# Tag 1.5.1 finite BLE window and continued BLINK

4 November 2026. The operator confirmed Tag USB unplugged, CR2032 selected and
all four anchors powered. Tag boot remained `2af27490` during the completed
Anchor-first calibration tests and this subsequent read-only observation.

The observer briefly verified Tag GATT information, disconnected it, then used
passive Tag advertisement scanning plus four Anchor measurement links. It opened
no COM port and sent no RTLS data.

- Tag advertisements observed: 215.
- Fresh Tag BLINK reports: A1 171, A2 150, A3 153, A4 153.
- Common BLINK groups received by all four anchors: 120.
- BLE window closure followed by continued common BLINK: true.
- Transport errors: none.

Local receipt: `verification/battery-window-20261104T021711859867Z/report.json`.

This verifies advertising cessation and continued UWB reception across the end
of the control window. Actual MCU sleep state, current consumption, battery
voltage and lifetime were not measured. Firmware calls requesting sleep are not
substitutes for electrical measurements. Reset reopens Tag BLE calibration;
normal BLINK operation does not require an open BLE window.
