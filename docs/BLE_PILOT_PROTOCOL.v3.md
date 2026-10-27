# BLE pilot protocol (experimental)

This draft is isolated from released desktop 2.0.1. Passing software fixtures does
not establish radio operation, GATT performance, simultaneous four-link reception,
3D accuracy, or CR2032 endurance. Experimental images stay under the ignored
`firmware/releases/_experimental/` folder and are not offered by the old app.

The PC receiver never writes a radio START/STOP command. Closing a capture only
disconnects BLE. Before connecting it accepts only the custom service-data identity
for an explicitly selected UWB MAC, then verifies model, role, MAC, autonomous
running state, boot epoch, and sequence snapshot through GATT. This identity check
is for correct board assignment; it is not cryptographic device authentication.

UUIDs are UUIDv5 of `https://github.com/COSMOnEsmer/UWBBoardProgrammer/ble/v1/`
followed by `service`, `info`, or `data`, using the URL namespace. SDK UUID arrays
use the reverse of UUID network byte order, as required by its BLE interface.

Legacy advertising is exactly 31 bytes: Flags AD (3), 128-bit service-data AD (28).
The latter contains the service UUID followed by version 1, role (0 slave/1 master),
and eight UWB MAC bytes in display order. The receiver does not match device names.

`info` is a UTF-8 JSON Read characteristic, maximum 256 bytes:

```json
{"v":1,"model":"Type2BP","role":"master","mac":"0200000000000001","boot":"aabbccdd","sequence":0,"firmware":"1.3.1-pilot","autonomous":true,"radio_state":"running"}
```

The read callback takes a current sequence snapshot. The PC rejects measurements
at or before that snapshot. Firmware flushes pending notifications on connection,
subscription changes, and disconnect. A boot change requires reconnect/info refresh.
The trial has no remote configuration/control characteristic.

The `data` notification carries fragments of one 64-byte little-endian record:

| Offset | Bytes | Meaning |
| --- | --- | --- |
| 0 | 2 | `UB` magic |
| 2 | 1+1 | version=1, measurement kind=1 |
| 4 | 4+4 | boot epoch, transport sequence (uint32) |
| 12 | 1+1+1+1 | role, RX bits (40/64), TX bits (0/40/64), frame (BLINK=0/SYNC=1) |
| 16 | 4 | SDK frame number; may repeat, not transport identity |
| 20 | 1+1+1+1 | radio status, message-control, MAC length (2/8), reserved=0 |
| 24 | 8 | peer MAC, right-padded with zero for short MAC |
| 32 | 8+8 | RX and TX original unsigned epochs; zero when TX absent |
| 48 | 2+2 | signed azimuth/elevation Q7; 32767/-32768 mean unavailable |
| 52 | 1+1+1+1 | azimuth FoM, elevation FoM, NLOS, reserved=0 |
| 56 | 4 | cumulative queue drops |
| 60 | 4 | IEEE CRC32 of bytes 0..59 |

Each notification starts with an 8-byte fragment header: version u8, kind u8,
sequence low uint16, index u8, count u8, complete-length uint16. Default ATT payload
20 uses six fragments (12 payload bytes each, final four). The receiver supports
different fragment sizes, out-of-order pieces, duplicates, and up to eight incomplete
messages for one second. It checks CRC and full sequence before accepting a record.

PC queue overflow, stale notifications, stream gaps, sequence/drop changes, boot
changes, and disconnects invalidate clock fits and pending frame associations.
Only RF epochs enter TDoA. BLE arrival times are diagnostics and freshness checks.

Pilot files: `app/ble_prototype/v1/uwb_ble_wire.py`, `uwb_ble_receiver.py`,
`tools/ble_capture_pilot_v1.py`, and `firmware/source/v16-provisioned-pilot/`.

Runtime: Python 3.12, Bleak 3.0.1. Use a dedicated asyncio/MTA worker when integrating
Qt. A single scanner supplies BLEDevice instances to clients; it avoids implicit
per-connection discovery. Four simultaneous links remain a hardware acceptance task.
See [Bleak Windows documentation](https://bleak.readthedocs.io/en/stable/backends/windows.html)
and [client connection documentation](https://bleak.readthedocs.io/en/stable/api/client.html).


The current GUI preview is opened through Start_Standalone_BLE_Bench_Preview_v4.cmd.
It uses a separate MTA receiver thread and processing thread, records private
sessions under data/sessions, and keeps USB/radio START/STOP separate from BLE
attach/detach. Load a surveyed four-anchor profile to enable positioning. The
legacy desktop remains 2.0.1. The selected-board flash workflow verifies two backups before programming and checks the board configuration acknowledgement. Other board ports and geometry are not required for flashing.

The live pilot solver whitens the TDoA vector with a full covariance matrix. With
pairwise LOS sigma s, each receiver contributes variance s^2/2; the master term
is shared by every difference. Independent slave clock RMS terms are added on
the diagonal. This still needs RF validation and a clock prediction-error model.

The RTLS button reuses the existing Edge Socket.IO connector and validates the
hardware gateway's site, floor, anchor IDs, roles and surveyed coordinates before
publishing accepted fresh fixes. Tokens are entered at runtime and not saved.
No production RTLS validation is implied by the local connector test.


The current receiver (uwb_ble_receiver_v4.py) requires provisioned=true,
interval_ms, and config_crc in Device Info. The CRC32 is computed over little-
endian <I8sII>: config magic 0xE2E11001, eight MAC bytes, interval_ms, and role
(0 slave/1 master; Tag role 2 is used by its USB provisioning). Firmware stores
these fields and the CRC as a 24-byte PDM record 0xE2E3, preserving the older
record 0xE2E2. Each selected fleet image binds its own slot identity.

Info is refreshed at connection and frozen for that connection, so long ATT
reads cannot mix changing sequence values. A radio boot change in measurements
forces reconnect and a new snapshot. The GUI uses a dedicated MTA receiver
thread and a separate bounded processing queue. The BLE service and payload
protocol stay v1 while firmware and PC preview have separate version identities.
