"""Real-board BLE endurance and recovery check. No flashing, UWB controls, or cloud.

Injects a PC-side A3 link cancellation and a short PC notification blackout.
Every recorded observation still comes from a CRC-checked real RF packet.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

sys.coinit_flags = 0
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'app/revisions/v19'), str(ROOT / 'app/ble_prototype/v1'),
                str(ROOT / 'app/battery_calibration/v2')]
from uwb_board_programmer import ble_winrt
from uwb_board_programmer.ble_controller import BleController
from uwb_board_programmer.models import Profile


def main(args):
    profile = Profile.from_dict(json.loads(args.profile.read_text(encoding='utf-8-sig')))
    target = next(a for a in profile.anchors if a.mac.upper() == args.target_mac.upper())
    folder = ROOT / 'verification' / ('ble-recovery-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir()
    fault = dict(address=None, blackout=False, packets_discarded=0)
    actual_factory = ble_winrt.make_client

    class ClientProbe:
        def __init__(self, device, **kwargs):
            self.client = actual_factory(device, **kwargs)
            self.address = device.address

        def __getattr__(self, key):
            return getattr(self.client, key)

        async def start_notify(self, characteristic, callback):
            def receive(char, data):
                if fault['blackout'] and self.address == fault['address']:
                    fault['packets_discarded'] += 1
                else:
                    callback(char, data)
            await self.client.start_notify(characteristic, receive)

    ble_winrt.make_client = ClientProbe
    messages = []

    def log(message):
        messages.append(dict(utc=datetime.now(timezone.utc).isoformat(), message=message))
        print(message, flush=True)

    controller = BleController(folder, profile, log, lambda value: None, diagnostic=True)
    started = time.monotonic()
    injected_cancel = False
    blackout_started = False
    blackout_ended = False
    cancel_baseline = blackout_baseline = None
    cancel_recovered_s = blackout_recovered_s = None
    next_status = 0
    report = dict(duration_s=args.seconds, target=target.id, radio_control_writes=0,
                  fault_injection_enabled=not args.no_injection,
                  cloud_messages_sent=0, flashing_attempted=False, status=[])
    error = None
    try:
        while time.monotonic() - started < args.seconds:
            elapsed = time.monotonic() - started
            if controller.receiver_ended.is_set():
                raise RuntimeError('BLE receiver ended before the test deadline')
            central = controller.central
            if central and target.mac.upper() in central.devices:
                fault['address'] = central.devices[target.mac.upper()][0].address
            count = controller.rx_counts.get(target.id, 0)
            if not args.no_injection and elapsed >= args.cancel_at and not injected_cancel:
                if not count:
                    raise RuntimeError('Target has no genuine RF observations before fault injection')
                cancel_baseline = count

                def cancel_target():
                    task = central.tasks.get(target.mac.upper())
                    if task:
                        task.cancel()

                controller.loop.call_soon_threadsafe(cancel_target)
                injected_cancel = True
                log('TEST: cancelled only ' + target.id + ' PC link')
            if injected_cancel and cancel_recovered_s is None and count > cancel_baseline:
                cancel_recovered_s = round(elapsed - args.cancel_at, 3)
                log('TEST: target resumed real RF after cancellation')
            if not args.no_injection and elapsed >= args.blackout_at and not blackout_started:
                fault['blackout'] = True
                blackout_started = True
                log('TEST: discarding target PC notifications to exercise telemetry watchdog')
            if not args.no_injection and elapsed >= args.blackout_at + args.blackout_seconds and not blackout_ended:
                fault['blackout'] = False
                blackout_baseline = count
                blackout_ended = True
                log('TEST: target notification blackout ended')
            if blackout_ended and blackout_recovered_s is None and count > blackout_baseline:
                blackout_recovered_s = round(elapsed - args.blackout_at - args.blackout_seconds, 3)
                log('TEST: target resumed real RF after watchdog recovery')
            if elapsed >= next_status:
                state = dict(elapsed_s=round(elapsed, 1), connected=sorted(controller.connected),
                             frames=dict(controller.rx_counts), states=dict(controller.states))
                report['status'].append(state)
                print(json.dumps(state), flush=True)
                next_status += 30
            time.sleep(.2)
        report['frames'] = dict(controller.rx_counts)
        report['final_connected'] = sorted(controller.connected)
        now = time.monotonic()
        report['final_frame_age_s'] = {a.id: round(now - controller.pipe.last_rx.get(a.id, started), 3) for a in profile.anchors}
    except Exception as exc:
        error = repr(exc)
    finally:
        fault['blackout'] = False
        try:
            controller.close()
            report['cleanup_completed'] = True
        except Exception as exc:
            report['cleanup_completed'] = False
            error = error or repr(exc)
        ble_winrt.make_client = actual_factory
    report.update(error=error, cancel_recovered_s=cancel_recovered_s,
                  blackout_recovered_s=blackout_recovered_s,
                  pc_notifications_deliberately_discarded=fault['packets_discarded'],
                  recording=str(controller.record.path), messages=messages)
    report['passed'] = bool(not error and report['cleanup_completed'] and
        (args.no_injection or (cancel_recovered_s is not None and cancel_recovered_s < 45 and
                              blackout_recovered_s is not None and blackout_recovered_s < 45)) and
        all(report.get('frames', {}).get(a.id, 0) > 0 and
            report.get('final_frame_age_s', {}).get(a.id, 1e9) < 5 for a in profile.anchors))
    path = folder / 'summary.json'
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(report=str(path), passed=report['passed'], error=error)), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=900)
    parser.add_argument('--target-mac', default='0200000000000003')
    parser.add_argument('--cancel-at', type=float, default=90)
    parser.add_argument('--blackout-at', type=float, default=180)
    parser.add_argument('--blackout-seconds', type=float, default=25)
    parser.add_argument('--no-injection', action='store_true', help='Observe real use without deliberate PC faults')
    args = parser.parse_args()
    if args.seconds <= 0 or (not args.no_injection and not
            (0 < args.cancel_at < args.blackout_at and args.blackout_seconds >= 15 and
             args.blackout_at + args.blackout_seconds + 45 < args.seconds)):
        parser.error('Allow separate cancellation/blackout recovery windows before the deadline')
    raise SystemExit(main(args))
