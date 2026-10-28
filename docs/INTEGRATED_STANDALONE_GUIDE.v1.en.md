# UWB Board Programmer 2.1.0

The original complete workspace now includes standalone firmware and BLE/GATT.
Use the desktop shortcut **UWB Board Programmer 2.1.0**. Earlier releases and the
separate BLE Pilot remain preserved.

1. **Devices & firmware:** select Standalone BLE, a physical EVK COM port and
   Rev4.1, then flash the selected A1/A2/A3/A4/Tag. Only that board is required.
   Two matching host-Flash backups precede programming and verification. Images
   bind the slot MAC/role; Tag images bind MAC 0200000000000101 and 1000 ms.
2. **BLE/GATT:** choose passive/active scan and duration, discover anchors, select
   a row and assign its UWB MAC to the correct anchor. Save the mapping in a new
   surveyed profile. Capture can receive one anchor before coordinates exist.
3. **Survey & calibration:** enter measured X/Y/Z, bounds and RTLS identifiers.
   Four-anchor TDoA requires non-coplanar geometry. Hybrid AoA requires calibration.
4. **Live positioning:** connect and record, then start positioning. The PC fits
   clock offset/drift from RF SYNC, matches BLINK receptions using corrected RF
   timestamps, and solves TDoA. The original map, X/Y/Z, quality and clock tables
   remain available. Pause stops PC processing; disconnect closes BLE. Neither
   action sends radio STOP to autonomous anchors. Legacy USB keeps its workflow.
5. **RTLS:** use the original gateway/token, configuration validation and publish
   controls. Only fresh accepted positions with matching server scope are sent
   over Edge Socket.IO.
6. **Sessions & replay:** new JSONL sessions retain raw BLE, observations, resets,
   rejected inputs and fixes. Replay is local and never publishes to RTLS.

The hardware acceptance work for Master/Slave synchronization, four simultaneous
links, measured 3D accuracy, CR2032/Power Banks and production RTLS remains pending.
Model uncertainty is not measured accuracy. Host backups exclude protected Flash,
radio NVM and OTP/EFUSE.

The packaged onedir folder contains its runtime and required local assets; move
the entire folder to another Windows x64 PC, not just the EXE. Test that PC's BLE
adapter/driver and simultaneous connections. The local package includes firmware
and DK6; vendor binaries, recordings and credentials are not published to GitHub.
