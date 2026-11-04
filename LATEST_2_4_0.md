# UWB Board Programmer 2.4.0

Run START_HERE_2_4_0.cmd or the new Desktop shortcut. No firmware change required.

Live positioning now displays finite solver candidates rejected for geometry,
residual, ambiguity or uncertainty as amber Warning markers, with XYZ and the
rejection reason. Accepted fixes remain teal. Warning candidates are display-only:
they do not increment accepted fixes or enter the RTLS publishing callback.
Missing synchronized measurements or a failure before a numerical solution still
shows no point. Candidate displays expire after three seconds without an update.

The Floor view offers a 3D/2D button, drag rotation in 3D, wheel zoom and Reset view.
Anchors are green when BLE is connected and RF reports are fresh according to
the receiver health check (three seconds); otherwise grey. This is operational
receiver status, not an independent test of the board power supply.

The original six-page workspace and previous releases remain preserved. Geometry
and measured-survey prerequisites remain in place. Warning XYZ is experimental
and does not establish accurate Tag location, especially with poor height geometry.

Validation: 42 existing regressions passed, plus one candidate-rejection test.
2D/3D warning/status renders were inspected with UI fixtures. Hardware positioning
accuracy and interaction on another laptop are not newly certified by these checks.
