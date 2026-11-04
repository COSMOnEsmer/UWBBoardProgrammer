# Battery Tag finite-window observation

Actual CR2032 operation, Tag USB disconnected as confirmed by the user.
Tag firmware 1.5.0-pilot, boot `1b66ff5a`. All four anchors remained powered.

The observer first read the remaining BLE window, disconnected Tag GATT, then
recorded Tag advertisements and read-only RF notifications from all four anchors.
At window expiry, Tag advertising stopped and common BLINK reception continued.

- Tag advertisements observed: **430**.
- Tag BLINK records: A1 **457**, A2 **421**, A3 **423**, A4 **417**.
- Fresh common BLINK groups across all four: **246**.
- Advertising cessation followed by common BLINK reception: **observed**.
- Connection errors: **none recorded**.
- USB/COM opened by observer: **no**.
- Position fixes/RTLS messages: **none generated**.

This verifies finite BLE advertising behavior and continued autonomous RF on the
coin cell. It does **not** measure MCU sleep current, exact power-down state or
battery lifetime. Those flags remain false in the firmware/testing metadata.

Local evidence: `verification/battery-window-20261104T010356948415Z/report.json`
and its timestamped `events.jsonl`. Raw local recordings are not shipped in Git.
