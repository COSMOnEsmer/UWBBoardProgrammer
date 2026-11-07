# 2.8.3 BLE recovery acceptance — 6 November 2026

The former receiver required a new advertisement less than three seconds old
before reconnecting a known anchor. Windows could retain its GATT connection
while the anchor stopped advertising, leaving the application unable to recover.
Normal Bleak 3.0.1 cleanup did not explicitly detach all native event registrations. The
2.8.3 adapter removes those registrations and releases MaintainConnection before
closing the session. Cleanup completes even when the receive task is cancelled.

The first physical cause of A3 stopping telemetry in the earlier 2.8.2 recording
is not established. Its last observation was at 11:46:46 Bangkok time, followed by
disconnect at 11:46:58, with firmware queue loss recorded beforehand. A separate
occasion required power cycling A3 before it advertised again. Do not attribute
that conclusively to the PowerBank without further evidence.

## Verified results

- 104 regression tests passed; 0 failures, errors or skips. This includes cached
  device retry without a fresh advertisement, identity mismatch rejection,
  cancellation-safe cleanup, telemetry timeout and independent anchor recovery.
- Offscreen fixtures skipped repeated Windows font registration only. Separate
  screenshots from the real EXE verified all six pages in English and Thai with
  the normal product fonts. Packaged startup reported no automatic BLE or cloud.
- USB endurance: 900 seconds, 6,179 real validated RF observations across A1–A4;
  A3 received 1,704. A deliberately cancelled A3 link resumed within 6.611 seconds.
  After a 25-second deliberate PC notification blackout, A3 resumed within 1.653
  seconds of the blackout ending. The other anchors continued receiving.
- Concurrent A3 UART capture: 1,050 seconds, one boot identifier, 3,102 RF records;
  free heap ranged from 14,808 to 14,864 bytes. No MCU reboot was observed during
  the USB test or the controlled PC faults.
- Original PowerBank endurance: 900 seconds without deliberate faults, 6,129 real
  validated observations; A3 received 1,818. All four anchors remained connected.
  No unplanned disconnect, BLE error or reconnect event was recorded. Final A3
  observation age was 0.133 seconds.
- After each acquisition closed, Windows reported no remaining UWB connection.
- The installed EXE received 1,808 real RF observations, including 513 from A3,
  while local positioning was exercised. No BLE error or retry was recorded.
  Pressing Disconnect released all UWB connections while that same EXE remained
  open (PID 13956); closing the application was not needed to release them.
  Existing position-geometry rejections were visible and are outside this BLE fix.
- The release ZIP has 606 hash-verified files, 97,127,825 bytes and SHA-256
  `b816778761e2461e86ae0d85b5d565c1af6e6db73fc77071a0f6ee3e26c9dbc0`.
  It contains no config/, data/, verification/ or vendor/ workspace data.
- The installed launcher/executable smoke test passed, using the existing data
  workspace in place. Profiles, recordings and DPAPI credentials need no copying
  into the distribution. Default entry points select 2.8.3; earlier versions remain.

The first packaging attempt exposed unrelated ICU/OpenSSL DLLs inherited from
the developer PATH. That attempt was retained separately and replaced before use.
The successful build uses a restricted dependency-search PATH and passes a native
DLL origin audit. Its real packaged EXE and installed launcher were both checked.

These finite tests demonstrate recovery and normal operation in the tested
conditions, not an indefinite guarantee against RF interference, power loss,
hardware failure or a non-responsive firmware task. Software cannot restore a
power supply that has switched off. No firmware was flashed for this fix.

See BUILD_AND_VERIFY_2_8_3.md for reproduction commands. Private raw recordings,
UART capture, JUnit and smoke reports remain under the local verification/ folder.
