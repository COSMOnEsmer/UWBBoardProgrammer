"""Isolated BLE pilot receiver. No radio-control writes and no cloud publishing.

Firmware must advertise service-data UUID SERVICE_UUID with bytes:
version(1), role(0 slave/1 master), UWB MAC(8 in display order).
INFO_UUID is a UTF-8 JSON read characteristic; DATA_UUID is notify-only.
"""
import asyncio
from dataclasses import dataclass
import json
import time
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
    return {**info, 'boot': boot.lower()}


class FreshGate:
    """Reject old/duplicate epochs; tell the pipeline to reset on loss."""
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
    def __init__(self, bindings, emit, *, queue_size=256):
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

    async def run(self):
        from bleak import BleakClient, BleakScanner
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
            async with BleakScanner(detected, scanning_mode='passive'):
                while not self.stop.is_set():
                    now = time.monotonic()
                    for mac, (device, seen) in list(self.devices.items()):
                        task = self.tasks.get(mac)
                        if task is not None and task.done():
                            await task
                            self.tasks.pop(mac)
                            self.retry_at[mac] = now + 2
                        if mac not in self.tasks and now - seen < 3 and now >= self.retry_at.get(mac, 0):
                            self.tasks[mac] = asyncio.create_task(self._link(device, self.bindings[mac], BleakClient))
                    try:
                        await asyncio.wait_for(self.stop.wait(), .25)
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
        reader = Reassembler()

        def notification(characteristic, data):
            nonlocal overflow
            try:
                queue.put_nowait((time.monotonic(), bytes(data)))
            except asyncio.QueueFull:
                overflow = True

        self.emit(aid, 'reset', {'reason': 'connecting'})
        try:
            async with client_type(device, disconnected_callback=lambda client: disconnected.set(),
                                   winrt={'use_cached_services': False}) as client:
                info = device_info(await asyncio.wait_for(client.read_gatt_char(INFO_UUID), 10), binding)
                characteristic = client.services.get_characteristic(DATA_UUID)
                if characteristic is None or 'notify' not in characteristic.properties:
                    raise ValueError('Measurement notify characteristic missing')
                gate = FreshGate(info)
                await asyncio.wait_for(client.start_notify(characteristic, notification), 10)
                self.emit(aid, 'connected', info)
                gap_reported = False
                last_packet = time.monotonic()
                while not self.stop.is_set() and not disconnected.is_set():
                    if overflow:
                        raise ValueError('PC BLE queue overflow; discard this connection epoch')
                    try:
                        received, fragment = await asyncio.wait_for(queue.get(), .25)
                    except asyncio.TimeoutError:
                        if not gap_reported and time.monotonic() - last_packet > 2:
                            self.emit(aid, 'reset', {'reason': 'rf_stream_gap'})
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
                        self.emit(aid, 'reset', {'reason': reset_reason})
                    last_packet = received
                    gap_reported = False
                    self.emit(aid, 'observation', record)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.emit(aid, 'error', {'message': str(error)})
        finally:
            reader.reset()
            self.emit(aid, 'reset', {'reason': 'disconnected'})
            self.emit(aid, 'disconnected', {})

