# UWB Board Programmer 2.8.3

Run `START_HERE_2_8_3.cmd` on Windows x64. Earlier releases are retained.

BLE recovery now retries previously discovered, identity-verified anchors even
when Windows still holds a connection and the anchor is no longer advertising.
The UWB MAC, role, provisioned CRC and running state are checked again on every
connection. Connect handshakes are serialized on the shared adapter; other
connected anchors keep receiving while one anchor reconnects.

A link with no fresh, valid telemetry for 12 seconds (or three configured
intervals, if longer) is released and retried. Backoff is bounded at 15 seconds.
The application records the disconnect/retry reason and displays reconnecting
instead of silently waiting for another advertisement forever.

Disconnect and application close stop notifications, release our Windows
background reconnect request, remove native event handlers, and finish GATT
cleanup even when the receive task is cancelled. A reconnect starts a fresh
receiver/clock epoch; stale or invalid packets are still rejected.

This is a PC software update. The packaged, hash-verified firmware is unchanged.
No flashing, radio START/STOP, automatic cloud publishing, credentials or personal
recordings are part of this update. Existing profiles and measurements are kept.

Software recovery cannot restore a board whose power supply has turned off or
whose firmware no longer responds. Check the power source if an anchor remains
absent. See [รายละเอียดและวิธีตรวจภาษาไทย](docs/BLE_RECOVERY_2_8_3.th.md).
