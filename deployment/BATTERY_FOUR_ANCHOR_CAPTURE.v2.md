# Battery calibration: first-peer success and subsequent timeouts

4 November 2026. This is an additional diagnostic record, not a replacement for
the published 2.3.0 release or its previous acceptance records.

The operator reset the unplugged Type2DK on CR2032. A4 was tested first, with A1
connected and held to silence its SYNC transmitter. The Tag boot was `eda8ea66`.
A4 produced an accepted median of 0.89 m, 125 retained samples, one discarded
sample, and sample standard deviation 0.01733 m. This is repeatability at the
current placement, not independently verified distance accuracy.

Without another Tag reset, a subsequent A1/A2/A3/A4 sequence required the master
connection for every pair. All four returned only 0x21 RX timeouts:

| Anchor | Timeout records |
|---|---:|
| A1 | 126 |
| A2 | 124 |
| A3 | 127 |
| A4 | 126 |

An explicit one-second Tag hold before a new A4 session produced Tag API status
0xFC. The supplied SDK defines this as `UWBAPI_STATUS_HPD_WAKEUP`, separately
from RX timeout (0x21) and low-battery error (0xFE). The SDK's Nearby Interaction
example restores default core configuration and retries after HPD wakeup.
The released custom Tag application does not implement that recovery path.
This is a confirmed lifecycle handling omission; it is not yet proof that HPD
explains every observed RX timeout.

After restoration, a read-only 40-second receiver run observed fresh Tag BLINK
at all four anchors: A1 31, A2 28, A3 28, A4 28. There were no transport errors.
Two further A4 captures without another Reset each returned 64 RX timeouts.
BLE visibility and ongoing BLINK therefore do not establish that DS-TWR is ready.

## New candidate, not yet hardware accepted

`firmware/source/v25-battery-radio-recovery` and the independent builder
`tools/build_firmware_battery_recovery_v1.py` prepare Tag version 1.5.1-pilot.
The published 1.5.0 firmware, source, application and portable package are retained.

The candidate checks stop/deinitialization results, clears nonexistent session
handles, restores SDK core configuration and retries once on HPD wakeup, verifies
the new session is active, and propagates failures instead of acknowledging a
successful transition. A new CRC-checked 20-byte read characteristic reports
radio stage, last API/RF status, HPD recovery count and Tag TWR good/failed counts.
It does not alter ranging geometry, distance quality gates or current limiting.

Ten native C fault-injection scenarios execute the candidate's actual lifecycle
functions, including repeated HPD, failed recovery, stop/deinit timeouts, failed
configuration cleanup and a non-active session after start. These passed, as did
an independent Python CRC check of the diagnostic frame. This is host testing,
not validation of RF, CR2032 current, battery lifetime or position accuracy.

Next acceptance requires Flash on the identified Tag, USB and CR2032 sequential
peer tests, deliberate hold/wakeup, and observation of restored common BLINK.
No complete reference survey, XYZ or RTLS publishing is accepted by this record.

Local evidence (append-only):

- `verification/battery-tag-pair-20261104T013543740961Z/report.json`
- `verification/battery-peer-sequence-20261104T013800341393Z/report.json`
- `verification/battery-peer-sequence-20261104T014300521113Z/report.json`
- `verification/post-survey-blink-20261104T014454643968Z/report.json`
- `verification/battery-peer-sequence-20261104T014602300806Z/report.json`
- `verification/tag-radio-lifecycle-20261104T015219720826Z/report.json`
