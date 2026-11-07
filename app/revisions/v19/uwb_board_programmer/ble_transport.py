"""Isolated BLE pilot receiver. No radio-control writes and no cloud publishing.

Firmware must advertise service-data UUID SERVICE_UUID with bytes:
version(1), role(0 slave/1 master), UWB MAC(8 in display order).
INFO_UUID is a UTF-8 JSON read characteristic; DATA_UUID is notify-only.
"""
import asyncio
from dataclasses import dataclass
import json
import time
import struct
import zlib
from uwb_ble_wire import SERVICE_UUID, INFO_UUID, DATA_UUID, Reassembler


@dataclass(frozen=True)
class Binding:
    anchor_id: str
    mac: str
    role: str

    def __post_init__(self):
        if not self.anchor_id or len(bytes.fromhex(self.mac)) != 8:
            raise ValueError('Anchor ID and 8-byte UWB MAC required')
        if self.role not in ('master', 'slave'):
            raise ValueError('Anchor role')


def advertisement_identity(data):
    if len(data) != 10 or data[0] != 1 or data[1] not in (0, 1):
        raise ValueError('Advertisement contract')
    return data[2:].hex().upper(), 'master' if data[1] else 'slave'


def device_info(raw, binding):
    if len(raw) > 1024:
        raise ValueError('Device info too large')
    info = json.loads(bytes(raw).decode('utf-8'))
    if not isinstance(info, dict) or info.get('v') != 1:
        raise ValueError('Device info protocol')
    if info.get('model') != 'Type2BP' or info.get('role') != binding.role:
        raise ValueError('Device model/role mismatch')
    if info.get('mac', '').upper() != binding.mac.upper():
        raise ValueError('Device UWB identity mismatch')
    if info.get('autonomous') is not True or info.get('radio_state') != 'running':
        raise ValueError('Autonomous radio not running')
    boot = info.get('boot')
    if not isinstance(boot, str) or len(boot) != 8:
        raise ValueError('Boot identifier')
    int(boot, 16)
    sequence = info.get('sequence')
    if type(sequence) is not int or not 0 <= sequence <= 0xffffffff:
        raise ValueError('Exact sequence snapshot required')
    if not isinstance(info.get('firmware'), str) or not info['firmware']:
        raise ValueError('Firmware version missing')
    if info.get('provisioned') is not True:raise ValueError('Commissioned firmware required')
    interval=info.get('interval_ms')
    if type(interval) is not int or not 100<=interval<=10000:raise ValueError('Provisioned interval')
    expected=zlib.crc32(struct.pack('<I8sII',0xE2E11001,bytes.fromhex(binding.mac),interval,1 if binding.role=='master' else 0))&0xffffffff
    if info.get('config_crc','').lower()!=f'{expected:08x}':raise ValueError('Provisioned configuration CRC')
    return {**info, 'boot': boot.lower()}


class FreshGate:
    """Reject old/duplicate epochs; report transport loss separately from reset."""
    def __init__(self, info):
        self.boot = info['boot']
        self.sequence = info['sequence']
        self.dropped = None
        self.last_time = None

    def accept(self, record, now=None):
        now = time.monotonic() if now is None else now
        if record['boot'] != self.boot:
            raise ValueError('Radio boot changed; reconnect and reread info')
        delta = (record['transport_sequence'] - self.sequence) & 0xffffffff
        if delta == 0 or delta >= 0x80000000:
            return False, None
        reason = None
        if delta > 1:
            reason = 'sequence_gap'
        if self.dropped is not None and record['dropped'] != self.dropped:
            reason = 'firmware_queue_loss'
        if self.last_time is not None and now - self.last_time > 2:
            reason = 'rf_stream_gap'
        self.sequence = record['transport_sequence']
        self.dropped = record['dropped']
        self.last_time = now
        return True, reason


class Central:
    """One scanner and at most four explicit BLEDevice connections.

    emit receives (anchor_id, kind, dict) on this asyncio thread. A GUI adapter
    must forward through queued Qt signals. reset events MUST invalidate that
    anchor's clock fit and pending frame groups before the next observation.
    """
    def __init__(self, bindings, emit, *, queue_size=256, scan_mode="passive", silence_timeout=12):
        if scan_mode not in ("passive","active"):raise ValueError("BLE scan mode")
        self.scan_mode=scan_mode
        self.bindings = {b.mac.upper(): b for b in bindings}
        if not 1 <= len(self.bindings) <= 4 or len(self.bindings) != len(bindings):
            raise ValueError('Provide one to four unique UWB MACs')
        if len({b.anchor_id for b in bindings}) != len(bindings):
            raise ValueError('Anchor IDs must be unique')
        self.emit = emit
        self.queue_size = queue_size
        self.stop = asyncio.Event()
        self.devices = {}
        self.tasks = {}
        self.retry_at = {}
        self.failures = {}
        self.connect_lock = asyncio.Lock()
        if not 0 < silence_timeout < float('inf'):
            raise ValueError('BLE silence timeout must be positive and finite')
        self.silence_timeout = silence_timeout
        self.poll_seconds = .25

    def retry_delay(self, failures):
        return min(15, 2 ** min(max(0, failures - 1), 4))

    async def run(self):
        from bleak import BleakScanner
        from .ble_winrt import make_client
        if __import__('sys').platform == 'win32':
            from bleak.backends.winrt.util import assert_mta
            await assert_mta()

        def detected(device, advertisement):
            data = advertisement.service_data.get(SERVICE_UUID)
            if data is None:
                return
            try:
                mac, role = advertisement_identity(bytes(data))
            except ValueError:
                return
            binding = self.bindings.get(mac)
            if binding and binding.role == role:
                self.devices[mac] = (device, time.monotonic())

        try:
            async with BleakScanner(detected, scanning_mode=self.scan_mode):
                while not self.stop.is_set():
                    now = time.monotonic()
                    for mac, (device, seen) in list(self.devices.items()):
                        task = self.tasks.get(mac)
                        if task is not None and task.done():
                            self.tasks.pop(mac)
                            try:
                                outcome = task.result() or {}
                            except asyncio.CancelledError:
                                outcome = {'reason': 'connection_cancelled'}
                            except Exception as error:
                                outcome = {'reason': type(error).__name__ + ': ' + str(error)}
                                self.emit(self.bindings[mac].anchor_id, 'error', {'message': outcome['reason']})
                            self.failures[mac] = (1 if outcome.get('healthy') else self.failures.get(mac, 0) + 1)
                            delay = self.retry_delay(self.failures[mac])
                            self.retry_at[mac] = now + delay
                            if not self.stop.is_set():
                                self.emit(self.bindings[mac].anchor_id, 'retrying', {
                                    'reason': outcome.get('reason', 'disconnected'), 'delay_s': delay,
                                    'attempt': self.failures[mac], 'address': device.address})
                        # A connected Windows GATT session does not advertise. A previously
                        # admitted BLEDevice remains usable; verify its UWB identity on EVERY
                        # reconnect instead of waiting forever for another advertisement.
                        if mac not in self.tasks and now >= self.retry_at.get(mac, 0) and not self.stop.is_set():
                            self.tasks[mac] = asyncio.create_task(self._link(device, self.bindings[mac], make_client))
                    try:
                        await asyncio.wait_for(self.stop.wait(), self.poll_seconds)
                    except asyncio.TimeoutError:
                        pass
        finally:
            for task in self.tasks.values():
                task.cancel()
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
            self.tasks.clear()

    async def _link(self, device, binding, client_type):
        aid = binding.anchor_id
        queue = asyncio.Queue(self.queue_size)
        disconnected = asyncio.Event()
        overflow = False
        closing = False
        reader = Reassembler()
        client = client_type(device, disconnected_callback=lambda client: disconnected.set(),
                             timeout=15, winrt={'use_cached_services': False})
        characteristic = None
        subscribed = False
        reason = 'stop_requested'
        first_packet = None
        last_packet = None

        def notification(characteristic, data):
            nonlocal overflow
            if closing:
                return
            try:
                queue.put_nowait((time.monotonic(), bytes(data)))
            except asyncio.QueueFull:
                overflow = True

        self.emit(aid, 'reset', {'reason': 'connecting'})
        try:
            # Serialize handshakes on the shared adapter while existing links keep receiving.
            async with self.connect_lock:
                await asyncio.wait_for(client.connect(), 20)
                info = device_info(await asyncio.wait_for(client.read_gatt_char(INFO_UUID), 10), binding)
                characteristic = client.services.get_characteristic(DATA_UUID)
                if characteristic is None or 'notify' not in characteristic.properties:
                    raise ValueError('Measurement notify characteristic missing')
                gate = FreshGate(info)
                await asyncio.wait_for(client.start_notify(characteristic, notification), 10)
                subscribed = True
                self.emit(aid, 'connected', info)
            gap_reported = False
            last_packet = time.monotonic()
            while not self.stop.is_set() and not disconnected.is_set():
                if overflow:
                    raise ValueError('PC BLE queue overflow; discard this connection epoch')
                if time.monotonic() - last_packet > max(self.silence_timeout, info['interval_ms'] / 1000 * 3):
                    raise TimeoutError('No fresh BLE telemetry; reconnecting this anchor')
                try:
                    received, fragment = await asyncio.wait_for(queue.get(), self.poll_seconds)
                except asyncio.TimeoutError:
                    if not gap_reported and time.monotonic() - last_packet > 2:
                        self.emit(aid, 'transport_gap', {'reason': 'rf_stream_gap'})
                        gap_reported = True
                    continue
                if time.monotonic() - received > .5:
                    raise ValueError('Stale PC notification queue')
                record = reader.accept(fragment, now=received)
                self.emit(aid, 'raw_ble', {'received_monotonic': received, 'hex': fragment.hex()})
                if record is None:
                    continue
                accepted, reset_reason = gate.accept(record, now=received)
                if not accepted:
                    continue
                if record['anchor_role'] != binding.role:
                    raise ValueError('Measurement role disagrees with commissioned identity')
                if reset_reason:
                    self.emit(aid, 'transport_gap', {'reason': reset_reason})
                last_packet = received
                if first_packet is None:
                    first_packet = received
                gap_reported = False
                self.emit(aid, 'observation', record)
            if disconnected.is_set() and not self.stop.is_set():
                reason = 'remote_disconnect'
        except asyncio.CancelledError:
            reason = 'stop_requested' if self.stop.is_set() else 'connection_cancelled'
            raise
        except Exception as error:
            reason = type(error).__name__ + ': ' + str(error)
            self.emit(aid, 'error', {'message': reason})
        finally:
            closing = True

            async def release():
                try:
                    connected = client.is_connected
                except OSError:
                    connected = False
                if subscribed and connected:
                    try:
                        await asyncio.wait_for(client.stop_notify(characteristic), 2)
                    except Exception as error:
                        self.emit(aid, 'cleanup_warning', {'message': 'Stop notify: ' + str(error)})
                try:
                    await asyncio.wait_for(client.disconnect(), 5)
                except Exception as error:
                    self.emit(aid, 'cleanup_warning', {'message': 'Disconnect: ' + str(error)})

            # A cancellation from Stop/close must not cancel Windows GATT disposal.
            cleanup = asyncio.create_task(release())
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                await cleanup
                raise
            finally:
                reader.reset()
                self.emit(aid, 'reset', {'reason': 'disconnected'})
                self.emit(aid, 'disconnected', {'reason': reason})
        return {'reason': reason, 'healthy': first_packet is not None and last_packet - first_packet >= 30}
