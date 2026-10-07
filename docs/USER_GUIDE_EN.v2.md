# UWB Board Programmer — User guide

Version 2.0.1. This workspace is separate from RTLSSimulator and preserves the earlier project. No UWB board was connected during software development.

## 1. Open and select the topology

Double-click the desktop shortcut or `Start_UWB_Board_Programmer_v3.cmd`. Use **Language** at the top right to switch English / ไทย. On **Devices & firmware**, select the positioning mode:

- **3 anchors · TDoA + AoA (3D):** A1 Master, A2/A3 Slave, one Type2DK Tag. At least one anchor needs verified usable azimuth AND elevation. The AoA orientation must be surveyed or calibrated in the floor frame.
- **4 anchors · TDoA (3D):** A1 Master, A2/A3/A4 Slave, one Type2DK Tag. No AoA participates in the solver. All four anchor coordinates must be measured and non-coplanar. A4 can use the same Slave firmware as A2/A3. Four anchors do not guarantee a unique or precise fix at every point.

Switching mode retains A1–A3 and Tag settings. A4 is retained in memory when toggling back and forth; save the four-anchor profile to preserve it across restarts. Close COM ports and disconnect RTLS before switching modes or profiles.

## 2. Flash and prepare the boards

Connect the EVKs through USB. Refresh ports and identify each physical board by unplugging one at a time. Enter the EVK revision printed on each board. Automatic USB flashing is enabled only for Rev.3 and later; older revisions require the vendor SWD procedure.

Select the complete firmware bundle. `Flash selected board` handles one board; `Flash all anchors` flashes every assigned Type2BP in the chosen mode. The generated bundle contains:

| Board / purpose | Image |
| --- | --- |
| Type2BP A1 Master | `murata_2bp_master_v1.bin` |
| Type2BP A2/A3/A4 Slave | `murata_2bp_slave_v1.bin` |
| Type2DK initial settings | `murata_2dk_tag_setup_v1.bin` |
| Type2DK standalone battery | `murata_2dk_tag_battery_v1.bin` |

The images are under `firmware/releases/<build timestamp>/`. The app selects them from a manifest, validates SHA-256, invokes DK6Programmer with verification, and checks firmware HELLO model/role/version over USB. A passing HELLO is not an RF acceptance test. Serial configuration uses 3,000,000 baud; the flash tool uses 1,000,000 baud.

For the Tag, set its unique 8-byte MAC and BLINK interval (100–10,000 ms; start at 1,000 ms). Choose **Tag · setup + battery** and Flash. The app installs the setup image, saves MAC/interval in PDM, installs the battery image without a full-chip erase, then verifies that the settings survived. Power-cycle the Tag and test it on CR2032 after removing USB. Keep the setup image for reconfiguration. Actual battery lifetime is not yet measured.

Do not disconnect USB during programming. Each flash creates a fresh log. No full-chip erase, OTP or lock/protection operation is part of this workflow.

### Flash with only one available USB port

Choose the physical board in the target selector, assign its COM port and EVK revision, then use **Flash selected board**. Leave the other port assignments blank and their revisions Unknown. Survey coordinates, orientation and workspace bounds are not required for single-board preparation. The selected board's revision and image integrity are still checked; Tag preparation also validates its MAC and BLINK interval.

Wait for programming, verification and the final HELLO check to finish. Disconnect that board, connect the next one, refresh ports, select the next target and repeat. You may reuse the same COM port for every board. If Windows assigns a different COM name to the next EVK, select that new name. Keep the Tag connected until both setup and battery images and retained settings have been verified.

**Flash all anchors** is the batch operation and requires distinct assigned ports. For live positioning, all three or four anchors must be connected and surveyed; sequential flashing does not remove the simultaneous acquisition requirement.

## 3. Survey the anchors

On **Survey & calibration**, enter actual floor-local X/Y/Z coordinates in metres; +Z points upward. Defaults have no surveyed coordinates. The board cannot discover its absolute floor coordinates or heading automatically. Match the RTLS map's origin, axes and scale.

The default IDs are KMUTNB-RF-A1 through A4 and KMUTNB-RF-T1. MACs are independent radio addresses and must be unique. Do not reuse simulator radio/device identities for actual hardware.

For four-anchor TDoA, arrange a useful volume instead of a flat ceiling rectangle. Different heights alone do not prove non-coplanarity; the app checks the rank of the coordinate differences. Example layout for planning only: A1=(0,0,0), A2=(10,0,0), A3=(0,8,0), A4=(0,0,4). These example coordinates are not your surveyed KMUTNB installation. Keep the useful tag region inside sensible workspace bounds and test across multiple heights.

**Hybrid mode:** enter measured yaw/pitch/roll in degrees or capture at least three known non-collinear tag directions, including different heights, in Diagnostic mode. The convention is local azimuth +X toward +Y, elevation toward +Z, and world rotation Rz(yaw) Ry(pitch) Rx(roll). Confirm the physical EVK antenna axes and angle signs experimentally. Fit orientation, then check independent reference points before checking **3D AoA**. A fit alone does not mark an anchor verified.

**Pure TDoA mode:** angle verification and orientation are optional diagnostics; the solver ignores AoA. Antenna RX bias still affects timing. Set noise estimates and uncertainty thresholds from measurements; the defaults are starting values, not demonstrated accuracy. Save a new profile rather than overwriting a previous file.

## 4. Acquire, record and solve

On **Live positioning**, open anchors and recording, then Start anchors. For angle-only commissioning, use Diagnostic mode; no position is computed or published in that mode.

The PC checks each HELLO, sends the chosen MAC/interval configuration and waits for configuration acknowledgements from **all** configured anchors before starting them. A1 transmits RF SYNC every 500 ms. Slave clocks need at least six fresh consistent SYNC samples. The app corrects clock offset/drift and associates the same Tag BLINK across all receivers. A missing A4 blocks four-anchor fixes.

The X/Y/Z cards show accepted results only. Rejections include missing measurements, stale clock synchronization, impossible TDoA, poor geometry, conflicting measurements, two plausible 3D roots or excessive horizontal/vertical uncertainty. Inspect the activity log and local JSONL recordings. Do not increase uncertainty thresholds merely to hide unsuitable geometry.

## 5. Connect the RTLS Platform

Register a real hardware gateway in RTLS, assign it to the supplied KMUTNB site/floor and obtain its Gateway ID and bearer token. The dashboard password is not a gateway token. Register the surveyed Anchor IDs/coordinates on the same floor, including A4 in four-anchor mode. **Export RTLS anchor setup** produces a worksheet; it does not silently modify the server.

On **RTLS Platform**, enter Gateway ID/token, check configuration, optionally save the encrypted token, then connect. The app validates site/floor/anchor IDs and coordinates within 1 cm. Only fresh accepted positions are sent when live publishing is enabled. `num_anchors_used` is 3 or 4 according to the actual solver result. Heartbeats/status and optional raw RF observations use the existing Edge Socket.IO contract; acknowledgements and dropped events are visible.

The default dashboard is [KMUTNB RTLS](https://uwb.mangosgo.com/?siteId=ca29a1a6-76c5-48ed-9c9a-e4615fcb4d09&floorId=58afbe99-a0a9-4fd2-ba69-4bf9acc96f6a). This release does not create gateway credentials or modify the map during startup. Live RF-to-cloud validation remains to be performed with the boards and your gateway token.

## 6. Review and acceptance

Stop anchors, close ports and disconnect RTLS. **Sessions & replay** can recalculate recorded data locally; it never sends replay positions to RTLS. Every session contains its topology and geometry.

Before relying on results, test flash/HELLO on each EVK, SYNC on every Slave, simultaneous BLINK reception, known static tag points at different heights, ambiguous/poor geometry rejection, lost-anchor behavior, clock resets, CR2032 operation and live cloud rendering. Record ground truth, median/95th percentile errors, update rate and fix/rejection counts. Software fixtures are not measured RF accuracy.
