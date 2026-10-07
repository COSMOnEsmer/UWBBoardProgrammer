# UWB Board Programmer 2.0.0 — Validation

Software validation performed on 7 October 2026, with no UWB boards connected.

- **42 automated tests passed:** existing timestamp precision/wrap, RF clock fit, hybrid 3D solver, calibration, recording/replay, offline cloud-contract and flashing guards; new four-anchor TDoA height fixtures, angle exclusion, geometry/count/uncertainty gates, missing/stale fourth receiver, two-root ambiguity, four-board configuration acknowledgements, flash/tag dispatch and bilingual mode/profile behavior.
- **All four firmware images compiled:** Master, Slave, Tag setup and Tag battery, using fresh copied SDK work directories. SHA-256 manifests, vector checksums and image header CRC32 were verified. Every firmware manifest explicitly records `hardware_validated: false`.
- **Desktop EXE built and launched:** five pages, complete firmware bundle discovered, no automatic serial open or cloud connect. An explicit packaged numerical fixture passed and was not published. Offscreen UI checks covered all five pages in English/three-anchor and Thai/four-anchor configurations; the native Windows app was also inspected.
- **Original source preserved:** the 13 files from the previous application source baseline retained the same SHA-256. Existing original SDKs, RTLSSimulator and the previous workspace were not edited.
- **Windows shortcuts created:** the desktop and project shortcuts point to the new release and use the new logo.

The fixtures are constructed software measurements, not RF accuracy measurements. Firmware compilation and USB HELLO code do not demonstrate that a real EVK has been flashed or that its UWB session works. Actual flash/HELLO, per-Slave RF SYNC, measured TDoA/AoA signs and biases, CR2032 operation, update rate, empirical 3D errors and live RTLS rendering remain pending the user's real-board tests.

Local test reports, screenshots, build logs, binaries and the original-source baseline are in the ignored `verification/` and `firmware/releases/` folders of the prepared PC workspace. The Git repository excludes those local artifacts, vendor inputs, generated releases, profiles, tokens and recordings.
