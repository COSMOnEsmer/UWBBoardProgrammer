# UWB Board Programmer 2.3.0 — battery Tag calibration

Run **START_HERE_2_3_0.cmd** after a complete pull. Use the explicitly versioned
**UWB Board Programmer 2.3.0** Desktop shortcut. Previous releases are preserved.

**Auto Survey → BLE Tag / CR2032** controls the Tag over GATT, so all four anchors
can remain powered while the Tag uses its coin cell. USB is required only to
prepare the new Tag firmware once. The already-tested Tag can skip reflashing.

- New Tag **1.5.0-pilot**: leased BLE control, TWR responder, restore to BLINK,
  finite 15-minute BLE window after Reset and a request for MCU power-down at expiry.
- **Check BLE Tag** verifies the identity/firmware/remaining window.
- BLE capture/save require no Tag COM port or battery-image reflash.
- At most three GATT links during a pair: Tag, master and selected slave.
- USB Tag / legacy and the previous normal battery image remain available.

Real BLE-controlled TWR on CR2032 was demonstrated with A1 and A2. Current
consumption, battery lifetime and full four-reference/3D accuracy still require
independent validation. A single Tag point does not determine all anchor XYZ.

- [คู่มือภาษาไทย](docs/INTEGRATED_STANDALONE_GUIDE.v6.th.md)
- [English guide](docs/INTEGRATED_STANDALONE_GUIDE.v6.en.md)
- [Validation scope](deployment/VALIDATION.v6.md)
