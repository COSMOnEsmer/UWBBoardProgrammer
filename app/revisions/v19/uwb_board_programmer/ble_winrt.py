"""Release every WinRT event registration and background reconnect request we own.

Bleak 3.0.1's normal disconnect closes the session/requester but leaves their
MaxPduSizeChanged and GattServicesChanged event registrations attached. Native
delegates can retain the Python backend and its Windows device references.
Keep this adapter scoped to our client; never disconnect another app's session.
"""
import sys


def release_event(owner, backend, token_name, method):
    token = getattr(backend, token_name, None)
    if owner is not None and token is not None:
        try:
            getattr(owner, method)(token)
        except OSError:
            pass  # Windows may already have closed this native object.
        finally:
            setattr(backend, token_name, None)


def releasing_backend(base):
    class ReleasingWinRTClient(base):
        async def disconnect(self):
            session = getattr(self, '_session', None)
            requester = getattr(self, '_requester', None)
            if session is not None:
                try:
                    session.maintain_connection = False
                except OSError:
                    pass
            release_event(session, self, '_max_pdu_size_changed_token', 'remove_max_pdu_size_changed')
            release_event(requester, self, '_services_changed_token', 'remove_gatt_services_changed')
            try:
                await super().disconnect()
            finally:
                # Also cover a partial connect: Bleak returns early if services is None.
                session = getattr(self, '_session', None)
                requester = getattr(self, '_requester', None)
                release_event(session, self, '_session_status_changed_token', 'remove_session_status_changed')
                for name, owner in (('_session', session), ('_requester', requester)):
                    if owner is not None:
                        try:
                            owner.close()
                        except OSError:
                            pass
                        finally:
                            setattr(self, name, None)
    return ReleasingWinRTClient


if sys.platform == 'win32':
    from bleak.backends.winrt.client import BleakClientWinRT
    ReleasingWinRTClient = releasing_backend(BleakClientWinRT)


def make_client(*args, **kwargs):
    from bleak import BleakClient
    if sys.platform == 'win32':
        kwargs['backend'] = ReleasingWinRTClient
    return BleakClient(*args, **kwargs)
