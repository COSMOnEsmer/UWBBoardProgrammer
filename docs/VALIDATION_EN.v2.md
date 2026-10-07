# UWB Board Programmer 2.0.1 — Single-board preparation

The **Flash selected board** operation now reads only the chosen board's COM port and EVK revision. Anchor preparation reads its role; Tag preparation additionally validates the Tag MAC and BLINK interval before programming. Survey fields, workspace bounds, other ports and other board revisions do not block single-board preparation. The same COM port can be reused after each completed operation.

**47 software tests passed.** Added coverage prepares every Anchor and then the Tag with only one assigned COM port in both three-anchor and four-anchor modes, leaving all other revisions Unknown and survey fields deliberately incomplete. The checks also verify selected revision/COM errors, Tag MAC validation before programming and the continuing requirement for all Anchor ports during live acquisition. The existing 42 tests also passed.

The tests replace hardware access with a fake flasher. They do not claim an EVK was programmed. Firmware images are unchanged from the previously verified bundle. The new desktop package passed its explicit offline smoke test, found the firmware bundle, rendered all five pages and opened no serial or cloud connection.

New files preserve the previous release:

- Active updated source: `app/revisions/v4/`
- Executable package: `releases/desktop-v3/UWB_Board_Programmer/`
- Launcher: `Start_UWB_Board_Programmer_v3.cmd`
- Desktop shortcut: `UWB Board Programmer 2.0.1`
- Updated instructions: `README.v2.md`, `docs/USER_GUIDE_EN.v2.md` and `docs/USER_GUIDE_TH.v2.md`
- Default pytest configuration: `pytest.ini`; explicit revision configuration: `pytest.v4.ini`

Live positioning still needs all three or four configured Anchors connected simultaneously. Actual flash/HELLO, RF/AoA calibration, CR2032 and live RTLS validation remain pending real-board tests. Neither the old application files nor its old desktop shortcut were replaced.
