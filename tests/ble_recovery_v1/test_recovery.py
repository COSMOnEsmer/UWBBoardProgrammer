import asyncio
import json
import struct
import time
from types import SimpleNamespace
import zlib

import pytest

from uwb_board_programmer.ble_transport import Binding, Central
from uwb_board_programmer.ble_winrt import releasing_backend
from uwb_ble_wire import DATA_UUID, SERVICE_UUID


BINDING = Binding('A3', '0200000000000003', 'slave')


def info(**changes):
    interval = 100
    crc = zlib.crc32(struct.pack('<I8sII', 0xE2E11001, bytes.fromhex(BINDING.mac), interval, 0)) & 0xffffffff
    value = dict(v=1, model='Type2BP', role='slave', mac=BINDING.mac, boot='12345678',
                 sequence=10, firmware='1.4.1-pilot', autonomous=True, radio_state='running',
                 interval_ms=interval, config_crc=f'{crc:08x}', provisioned=True)
    value.update(changes)
    return json.dumps(value).encode()


class FakeClient:
    instances = []
    raw_info = info()
    fail_stop = False

    def __init__(self, device, **kwargs):
        self.is_connected = False
        self.released = False
        self.subscribed = False
        self.calls = []
        self.callback = kwargs['disconnected_callback']
        self.services = SimpleNamespace(get_characteristic=lambda uuid: SimpleNamespace(properties=['notify']))
        type(self).instances.append(self)

    async def connect(self):
        self.is_connected = True
        self.calls.append('connect')

    async def read_gatt_char(self, uuid):
        return self.raw_info

    async def start_notify(self, characteristic, callback):
        self.subscribed = True
        self.calls.append('subscribe')

    async def stop_notify(self, characteristic):
        self.calls.append('unsubscribe')
        if self.fail_stop:
            raise OSError('remote device went away')
        self.subscribed = False

    async def disconnect(self):
        await asyncio.sleep(.02)
        self.calls.append('disconnect')
        self.is_connected = False
        self.released = True


async def until(predicate, timeout=2):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(.005)


@pytest.fixture(autouse=True)
def fresh_client():
    FakeClient.instances = []
    FakeClient.raw_info = info()
    FakeClient.fail_stop = False


@pytest.mark.parametrize('fail_stop', [False, True])
def test_cancelled_link_finishes_native_cleanup_before_reporting_disconnected(fail_stop):
    async def scenario():
        FakeClient.fail_stop = fail_stop
        events = []
        central = Central([BINDING], lambda *row: events.append(row))
        task = asyncio.create_task(central._link(SimpleNamespace(address='known A3'), BINDING, FakeClient))
        await until(lambda: any(row[1] == 'connected' for row in events))
        central.stop.set()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        client = FakeClient.instances[0]
        assert client.released and not client.is_connected
        assert client.calls[-2:] == ['unsubscribe', 'disconnect']
        assert events[-1] == ('A3', 'disconnected', {'reason': 'stop_requested'})
    asyncio.run(scenario())


def test_silent_connected_device_is_released_instead_of_waiting_forever():
    async def scenario():
        events = []
        central = Central([BINDING], lambda *row: events.append(row), silence_timeout=.05)
        central.poll_seconds = .01
        outcome = await asyncio.wait_for(central._link(SimpleNamespace(address='known A3'), BINDING, FakeClient), 2)
        assert 'No fresh BLE telemetry' in outcome['reason']
        assert FakeClient.instances[0].released
        assert any(row[1] == 'error' for row in events)
    asyncio.run(scenario())


def test_reconnect_does_not_accept_changed_hardware_identity():
    async def scenario():
        FakeClient.raw_info = info(mac='0200000000000002')
        central = Central([BINDING], lambda *row: None)
        outcome = await central._link(SimpleNamespace(address='cached address'), BINDING, FakeClient)
        assert 'identity mismatch' in outcome['reason']
        client = FakeClient.instances[0]
        assert 'subscribe' not in client.calls and client.released
    asyncio.run(scenario())


def scanner_once(monkeypatch, bindings):
    import bleak
    import bleak.backends.winrt.util

    async def mta():
        pass

    class Scanner:
        def __init__(self, callback, **kwargs):
            self.callback = callback

        async def __aenter__(self):
            for binding in bindings:
                raw = bytes([1, int(binding.role == 'master')]) + bytes.fromhex(binding.mac)
                self.callback(SimpleNamespace(address='BLE-' + binding.anchor_id),
                              SimpleNamespace(service_data={SERVICE_UUID: raw}))
            return self

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(bleak, 'BleakScanner', Scanner)
    monkeypatch.setattr(bleak.backends.winrt.util, 'assert_mta', mta)


@pytest.mark.parametrize('failure', ['disconnect', 'exception', 'cancel'])
def test_retries_cached_device_without_new_advertisement_and_keeps_other_anchor_alive(monkeypatch, failure):
    master = Binding('A1', '0200000000000001', 'master')
    scanner_once(monkeypatch, [master, BINDING])

    async def scenario():
        events = []
        central = Central([master, BINDING], lambda *row: events.append(row))
        central.poll_seconds = .005
        central.retry_delay = lambda failures: .01
        attempts = []
        master_cancelled = []

        async def link(device, binding, client_type):
            if binding.anchor_id == 'A1':
                try:
                    await central.stop.wait()
                    return {'reason': 'stop_requested'}
                finally:
                    master_cancelled.append(central.stop.is_set())
            attempts.append(device)
            # Force advertisement age beyond the old three-second admission gate.
            central.devices[binding.mac] = (device, time.monotonic() - 100)
            if len(attempts) == 1:
                if failure == 'exception':
                    raise RuntimeError('unexpected per-device error')
                if failure == 'cancel':
                    raise asyncio.CancelledError()
                return {'reason': 'remote_disconnect'}
            central.stop.set()
            return {'reason': 'stop_requested'}

        central._link = link
        await asyncio.wait_for(central.run(), 2)
        assert len(attempts) == 2 and attempts[0] is attempts[1]
        assert master_cancelled == [True]
        assert any(row[0] == 'A3' and row[1] == 'retrying' for row in events)
        assert not central.tasks
    asyncio.run(scenario())


def test_retry_delay_is_bounded_for_long_outages():
    central = Central([BINDING], lambda *row: None)
    assert [central.retry_delay(n) for n in (1, 2, 3, 4, 5, 50)] == [1, 2, 4, 8, 15, 15]


@pytest.mark.parametrize('partial', [False, True])
def test_winrt_disconnect_releases_maintain_connection_and_native_event_references(partial):
    calls = []

    class Native:
        def __init__(self, name):
            self.name = name
            self.maintain_connection = True
            self.events = set()

        def remove_max_pdu_size_changed(self, token):
            self.events.remove(token)
            calls.append('remove_pdu')

        def remove_session_status_changed(self, token):
            self.events.remove(token)
            calls.append('remove_status')

        def remove_gatt_services_changed(self, token):
            self.events.remove(token)
            calls.append('remove_services')

        def close(self):
            assert not self.events, 'Native callbacks must not retain the backend after close'
            if self.name == 'session':
                assert self.maintain_connection is False
            calls.append('close_' + self.name)

    class Base:
        async def disconnect(self):
            if self.services is None:
                return
            self._session.remove_session_status_changed(self._session_status_changed_token)
            self._session_status_changed_token = None
            self._session.close()
            self._requester.close()
            self._session = self._requester = None

    backend = releasing_backend(Base)()
    backend._session = Native('session')
    backend._requester = Native('device')
    backend._session.events = {11, 12}
    backend._requester.events = {13}
    backend._max_pdu_size_changed_token = 11
    backend._session_status_changed_token = 12
    backend._services_changed_token = 13
    backend.services = None if partial else object()
    asyncio.run(backend.disconnect())
    assert backend._session is None and backend._requester is None
    assert set(calls) == {'remove_pdu', 'remove_status', 'remove_services', 'close_session', 'close_device'}
