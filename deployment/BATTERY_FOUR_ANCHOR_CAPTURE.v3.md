# 2.3.1: battery Tag radio recovery and complete four-anchor range batch

4 November 2026. All changes are new revision/release paths. Previous firmware,
desktop releases, source inputs and RTLSSimulator are preserved.

## Firmware actually programmed

The connected board was identified as Type2DK, Tag MAC `0200000000000101`, on
COM9 / USB serial `5` before programming. Two matching same-board backups were
verified before each Flash. The final 1.5.1-pilot image was programmed and byte
verified, with matching version/MAC/provisioning acknowledgement. No OTP or
protected tail was written.

- Image size: 447,160 bytes.
- SHA-256: `78b038e539d9e9f3bcc9d20af0ddc6def8a4b2b310cf921b8ed15c22c4de3d51`.
- Source: `firmware/source/v25-battery-radio-recovery`.
- Flash: `verification/flash-jobs/20261104T015935512291Z/report.json`.
- Preserved backup: `verification/host-backups/20261104T015935516832Z/backup-manifest.json`.

An earlier unpublished candidate had the diagnostic characteristic UUID encoded
in the wrong Bluetooth octet order. This was found through real GATT discovery,
corrected, checked with a regression test and rebuilt into new output. The final
image above is the corrected image; earlier build outputs remain retained.

## What the experiments establish

The supplied SDK defines 0xFC as HPD wakeup. The previous Tag code did not restore
default core configuration and retry on that status. The new firmware performs
one bounded recovery attempt, checks stop/deinit/start results, verifies session
state and exposes CRC-checked radio diagnostics over GATT.

A real deliberate one-second RF hold triggered 0xFC. The new code restored core
configuration and started the next session successfully. USB tests then completed
A4/A1/A4 exchanges. Many USB records were NLOS, so those tests were not accepted
as calibration ranges.

On CR2032, the original Tag-first startup order passed A4/A1/A2 but later returned
127 timeouts on A3 and another 127 on repeated A4. Tag diagnostics showed no new
successful TWR reports during those late pairs and additional HPD recoveries.

The PC was then changed to start the Anchor initiator before enabling the Tag
responder. This avoids leaving the coin-cell responder receiving while waiting
for a slow Anchor ATT start. Without another Tag Reset, A4/A3/A4 all produced
accepted LOS ranges; the Tag failed-report counter did not increase. This fixes
the observed startup behavior in this test. Battery voltage/current was not
measured, so a brownout or precise electrical cause is not claimed.

## Exact GUI backend on CR2032

The exact `capture_reference_ble` used by the 2.3.1 wizard then measured all four
anchors sequentially, without Tag USB/COM, Reset or a deliberate HPD hold.
Master A1 was explicitly connected and held for every slave pair. At most three
GATT links were used: Tag, master and target slave.

| Anchor | Records | LOS | NLOS | Failed | Retained LOS | Median range (m) |
|---|---:|---:|---:|---:|---:|---:|
| A1 | 117 | 32 | 85 | 0 | 31 | 0.46 |
| A2 | 123 | 114 | 9 | 0 | 112 | 1.63 |
| A3 | 116 | 23 | 93 | 0 | 21 | 1.77 |
| A4 | 123 | 123 | 0 | 0 | 123 | 0.95 |

The range batch returned `complete=true`, `missing=[]`, `errors={}` and
acknowledged restoration. Tag RF good reports increased from 1,335 to 2,244;
failed reports stayed at 58 and HPD recoveries stayed at 3 throughout this batch.
Distance and positioning quality gates were unchanged.

Local evidence:

- USB: `verification/battery-recovery-sequence-20261104T020134731838Z/report.json`.
- Tag-first battery comparison: `verification/battery-recovery-sequence-20261104T020605307817Z/report.json`.
- Anchor-first recovery: `verification/battery-recovery-sequence-20261104T021100537709Z/report.json`.
- Exact GUI backend: `verification/battery-reference-20261104T021341686696Z/report.json`.

These ranges describe the current test placement. No independent tape/laser
distances to Tag were supplied. The zero reference label used by the diagnostic
script is not a surveyed physical origin. The report explicitly marks its purpose
as link diagnostics and geometry unverified. It was not imported as a production
survey, used to calculate XYZ or sent to RTLS.

## Application and checks

Application 2.3.1 keeps the original six-page workspace and English/Thai UI. BLE
Tag support is in `app/battery_calibration/v2`, desktop source in `app/revisions/v11`.
The wizard shows wake recovery and RF counters, records diagnostics, requires
the powered master and uses Anchor-first startup. Timeouts before both startup
acknowledgements are discarded before acquisition begins.

42 software regression tests passed, including startup ordering, stale startup
timeouts, restoration after Tag-start failure, CRC/identity checks, geometry,
clock and positioning diagnostics. Ten native C fault-injection scenarios passed
against the actual firmware lifecycle functions. English/Thai wizard renders
were inspected. None of these host tests substitutes for RF acceptance.

Full calibration still requires four physically measured non-coplanar Tag points
and fixed antenna positions. Independent holdout positions/heights, RTLS frame
alignment, current consumption and battery lifetime remain unverified. A separate
read-only receipt covers finite BLE window closure and continued common BLINK.
