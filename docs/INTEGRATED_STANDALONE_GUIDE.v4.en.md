# UWB Board Programmer 2.2.0

Run `START_HERE_2_2_0.cmd` after cloning/pulling the complete repository. The
launcher verifies the embedded Windows x64 distribution, extracts a new local
installation and creates the **UWB Board Programmer 2.2.0** Desktop shortcut.
No Python or Murata SDK installation is needed to run the application. Windows
must expose a compatible Bluetooth LE adapter/driver for Bleak/WinRT; a Wi-Fi
antenna alone does not provide BLE. FTDI drivers are needed for USB flashing.

## Firmware and normal operation

| Selection | Board | Firmware | Use |
|---|---|---|---|
| A1 / master | Type2BP Rev4.1 | 1.4.1-pilot | Autonomous RF SYNC, UWB reception, BLE telemetry, leased TWR survey |
| A2 / A3 / A4 | Type2BP Rev4.1 | 1.4.1-pilot | Autonomous UWB reception, BLE telemetry, leased TWR survey |
| Tag / Auto Survey / USB calibration | Type2DK Rev4.1 | 1.4.2-pilot | Awake USB-powered Tag; UART-controlled leased TWR |
| Tag / battery | Type2DK Rev4.1 | 1.3.4-pilot | Existing low-power autonomous BLINK operation |

These are project firmware builds based on the Murata/NXP SDK and matching
Murata board patches, not a claim that stock SDK binaries implement this BLE
survey protocol. Each image has a provisioned identity. Use the correct slot;
do not flash the A1 image to every anchor. Flash one board at a time if needed.
The application makes two matching backups before programming and verifies the
image, board acknowledgement and configuration CRC. It does not write OTP.

Normal positioning: power all four anchors from USB supplies/Power Banks; they
start themselves. The PC receives their UWB measurements through BLE/GATT. The
Tag uses its battery image and CR2032, without a PC connection. A1 remains the
RF clock reference; standalone operation does not remove clock synchronization.

## Auto Survey: four measured Tag points

Open **Survey & calibration → Auto Survey / Calibration**. Disconnect normal
BLE acquisition and RTLS first. Auto Survey measures distances using DS-TWR,
temporarily pauses TDoA, then restores standalone radio operation. Control leases
expire within 30 seconds if the connection is lost. Radio ranging is sequential.

A single Tag at (0,0,0) cannot determine all anchor XYZ and their axes. Instead,
physically mark these four non-coplanar **Tag antenna** locations:

| Point | Known coordinate |
|---|---|
| Origin | (0, 0, 0) |
| X | (Lx, 0, 0) |
| Y | (0, Ly, 0) |
| Z | (0, 0, Lz) |

Measure Lx, Ly and Lz with a tape or laser. X/Y are perpendicular and level;
Z is vertically above origin. Each baseline must be 0.4–20 m; about 1 m or more
usually offers a more useful baseline than a short movement. Keep anchors fixed
throughout all four references. Establish clear LOS and avoid metal obstructions.
Mount at least one anchor at a different height for 3D TDoA.

1. Connect Type2DK by USB, select its actual COM port, and set its power switch
   to USB. Use **Prepare USB calibration Tag** if it is not already on 1.4.2.
2. Enter measured Lx/Ly/Lz and confirm the physically measured axes. Do not infer
   them from unverified AoA. These lengths define the fit, not an independent
   accuracy test.
3. Place the Tag at origin; press **Capture origin**. Keep it still.
4. With limited power outputs, leave only three anchors powered alongside the
   USB Tag. The program retains successful ranges. When it reports missing
   anchors, switch power from a completed anchor to a missing one without moving
   any board. Press the **same** capture button again. Reach 4/4 before moving Tag.
5. Repeat for X, Y and Z. A completed reference cannot accidentally be recaptured;
   reset references if a board moved or the axes/lengths were wrong. Length fields
   lock once a capture is retained. Raw ranges and reports are new files under
   `data/surveys`; keep the wizard open while accumulating a survey.
6. Press **Calculate anchor coordinates**. Review XYZ, fit RMS and model standard
   deviations. NLOS samples, insufficient counts, inconsistent ranges and poorly
   constrained geometry are rejected with a reason. Reported model uncertainty
   includes a 0.05 m range floor; it is not a measured absolute error guarantee.
7. **Save new profile and finish** creates a new profile and loads it into Survey.
   Existing profiles remain intact. The default checked option restores the
   normal battery Tag image; keep Tag USB connected until Flash/verify finishes.
   Only then switch the Tag to its CR2032 supply for normal operation.

If saving rejects insufficient anchor height diversity, the calculated coordinates
remain in a new preview report. Move an anchor vertically and repeat all references.
Do not change acceptance thresholds merely to obtain an XYZ display.

**Optional: anchor links** measures the six inter-anchor pairs while all anchors
are powered and Tag is off. It records link failures and NLOS separately. This
diagnostic is not required by the four-reference coordinate solver.

## TDoA positioning and RTLS

Power all four anchors and the battery Tag. Connect BLE, then Start positioning.
The PC groups the same Tag BLINK frame across anchors; fits slave-to-master clock
models from UWB RF SYNC timestamps; compensates surveyed SYNC propagation; converts
corrected arrival-time differences to distance differences; and solves nonlinear
3D range-difference equations. USB/BLE packet arrival times are not RF timestamps.
Four-anchor TDoA does not require AoA calibration. Hybrid three-anchor mode still
requires verified anchor angle axes/orientation and adequate geometry.

Accepted output is Tag ID, XYZ in metres in the survey frame, time, anchors used,
residual and estimated horizontal/Z uncertainty. Rejected solutions show the
reason, clock state and diagnostics. Calibration cannot guarantee every later
TDoA group passes; NLOS, timestamp noise and poor geometry still matter.

Check separate known Tag positions and heights before making an accuracy claim.
Auto Survey finds antenna coordinates; it does not jointly estimate unknown
antenna delays or anchor yaw/pitch/roll. Those orientation fields are not enabled
as calibrated AoA by the wizard.

The measured origin/axes must be transformed/aligned to the RTLS floor's coordinate
frame before publishing to the existing KMUTNB map. The app does not silently
replace that map's frame with the new Tag-origin frame. Review bounds, site/floor,
Tag ID and exported anchor setup. Use the existing RTLS Platform page to sign in,
verify configuration and explicitly start publishing accepted fixes. No cloud
traffic or BLE acquisition starts automatically when launching the app. No account
passwords, recordings, local settings or board backups are shipped in the Git payload.

## Validation scope

Real Rev4.1 tests verified four-anchor Flash/boot/BLE, selected anchor TWR links,
A1-to-Type2DK USB TWR, and acknowledged radio restoration. Software tests cover
four-reference geometry, quality rejection, sequential power subsets and save-new
profiles. Complete physical four-reference calibration and held-out 3D TDoA accuracy
must still be measured by the user; software fixtures are not RF accuracy evidence.

Older 2.1.x releases and RTLSSimulator are preserved. Use the explicitly versioned
2.2.0 launcher/shortcut to avoid opening an older application.
