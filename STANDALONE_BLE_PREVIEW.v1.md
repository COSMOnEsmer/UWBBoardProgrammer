# UWB Board Programmer — Standalone BLE Preview

This preview is separate from the released desktop application 2.0.1. It uses
the experimental **1.3.4-pilot** firmware. Existing applications, SDK inputs,
firmware images, backups and simulator files are preserved.

On the development PC, double-click **UWB Board Programmer - BLE Preview** on
the desktop, or `Start_Standalone_BLE_Bench_Preview_v5.cmd` in this folder.
The active GUI is `app/ble_prototype/v1/standalone_bench_gui_v8.py`.

The preview can flash one selected USB EVK at a time, receive autonomous
Anchor telemetry over BLE, record real measurements, and run the four-anchor
3D pipeline with a surveyed profile. The RTLS connector uses Edge Socket.IO.

Verified on 28 October 2026: real Type2DK BLINK reception by one Type2BP,
57 complete BLE records matching simultaneous UART records exactly for timing
and protocol fields, native GUI reception, and continued BLINK reception after
the Tag firmware entered its MCU-sleep path. **84 software tests pass.**

Four simultaneous Anchors, inter-anchor clock synchronization, measured 3D
accuracy, Power Bank/CR2032 operation and production RTLS remain acceptance
tasks. Single-link measurements do not establish those results.

- [Thai operating guide](docs/STANDALONE_BLE_PREVIEW.v3.th.md)
- [Updated development and acceptance plan](plans/Standalone_TDoA_BLE_Plan.v4.th.md)
- [BLE wire protocol](docs/BLE_PILOT_PROTOCOL.v3.md)

Rebuild in fresh SDK copies with `tools/build_firmware_provisioned_pilot_v6.py`.
The six roles are `master`, `slave2`, `slave3`, `slave4`, `tag_setup` and
`tag_battery`. Licensed vendor SDKs, toolchains, generated binaries, runtimes,
device backups, recordings and credentials remain local and are not published.

Passive verification tools are `tools/capture_uart_pilot_v1.py` and
`tools/compare_ble_uart_pilot_v1.py`. Their reports are saved as new local files.
