# UWB Board Programmer 2.8.0 — explicit Survey / Floor coordinates

Run START_HERE_2_8_0.cmd on Windows 10/11 x64. Use the 2.8.0 Desktop shortcut. Earlier files are preserved. Firmware remains Anchor 1.4.1-pilot / Tag 1.5.1-pilot; no Flash is needed to change a map's origin. Tag calibration still supports CR2032/BLE.

## Coordinate workflow

1. Select the correct site/floor through RTLS Platform → Use gateway configuration. Map each UWB MAC to its server Anchor ID. BLE address is a different identifier. Imported floor dimensions are used when supplied; enter missing values explicitly.
2. Auto Survey measures anchors relative to the Tag antenna at Survey Origin. Complete the four physically measured reference points. Saving the survey now opens Align survey to floor. The survey is saved first, so cancelling alignment does not discard it.
3. In Survey & calibration click Align survey to floor at any later time. Select a reference Anchor, set its desired Floor XYZ and the yaw from Survey to Floor. Alternatively map the Survey Origin itself, or fit at least two paired Survey/Floor XYZ references with horizontal separation. +Z must already be vertical; scale remains exactly 1. Three or more references and an independent validation point are recommended.
4. Enter floor origin, length, width, height, elevation and level index. Level index is a label, not metres. Z in telemetry is above the floor; site elevation is stored separately and never added again.
5. Preview every Anchor. Out-of-floor coordinates are warned about, not visually clamped. Optionally enter an independent Survey/Floor point to check the registration. Confirm the physical axes/Z convention and apply. This saves a NEW floor-profile; the source survey remains in its metadata.
6. Check configuration, connect RTLS, connect BLE and start positioning. Only accepted fresh fixes are published. Diagnostic estimates and last-known markers remain local. Repeat alignment always derives from the retained source, so offsets do not accumulate.

## A4 as the XY origin

The default reference is the last configured Anchor, normally A4. The default target X/Y is zero. Keep existing Z means the existing Z values are already heights above the floor; it does not lower A4 to the floor. For the commissioning example, A4 moves from (-1.132,-0.426,0.518) to (0,0,0.518), giving translation (+1.132,+0.426,0), yaw 0, and floor bounds (0,0,0) to (4,4,2).

The four resulting anchors are (0.688,0.878,0.891), (2.013,0.895,1.891), (2.450,0.037,0.779), and (0,0,0.518). This matches the supplied configuration; it does not independently validate RF accuracy or the physical Z datum.

## Frame safety

Legacy profiles are Unmapped until reviewed; measured-survey confirmation alone does not assert a floor frame. Unmapped/Survey profiles can be used locally, but cloud configuration verification/publishing requires a confirmed Floor profile. Site/floor or aligned-coordinate edits invalidate the saved registration. Use retained survey restores source geometry into another NEW file when a new registration is needed. Imported confirmed server coordinates can also be explicitly marked floor-relative.

To keep geometry, AoA, covariance, bounds, map, path and payload consistent, 2.8.0 solves directly using the registered Floor anchor coordinates and rotated anchor orientations. It does not apply the transform again to solved Tag positions. This is equivalent to solving in Survey and transforming for a rigid registration, with Floor bounds acting as the explicit workspace prior. Recordings retain frame metadata; old replay stays local in its recorded frame. Frame registration does not calibrate antenna delay, clock quality or RF multipath.

The clean dock UI, English/Thai switch, panel floating/Attach, 30-second fading path and quality gates remain. See the 2.7.0 guide for the detailed dock interaction. Gateway credentials use user-scoped Windows DPAPI and are excluded from portable archives/Git. Save a token on a new laptop separately.
