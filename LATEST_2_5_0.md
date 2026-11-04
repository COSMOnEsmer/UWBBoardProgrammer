# UWB Board Programmer 2.5.0

Run START_HERE_2_5_0.cmd or the new Desktop shortcut. No board Flash is required.
Previous application/firmware files and RTLSSimulator are preserved.

- Tag stays at its last received computed position during gaps, turns grey after
  three seconds and displays LAST KNOWN with actual sample age. It does not
  pretend to continue moving without new measurements.
- The path contains actual samples from the previous five seconds, fades by
  age and expires even without new samples. Repeated UI refreshes do not extend
  sample lifetime. Gaps over two seconds are not joined by an invented segment.
- Accepted path segments are teal; experimental Warning segments are amber.
  Last-known and Warning positions do not become new accepted RTLS fixes.
- Cards, including metrics and Activity log, have Collapse/Expand and
  Detach/Attach controls. Detached windows are resizable/maximizable. Closing
  one returns the same live controls to the main workspace. Floor view and
  clock panels also have a draggable splitter. The 2D/3D controls remain.
- RTLS Platform has a connection guide button. See
  [Thai RTLS guide](docs/RTLS_CONNECTION_2_5_0.th.md).

46 software tests passed, including sample-age/path expiry, retained last point,
widget identity and signal continuity across detach/reattach, and previous
clock/solver/calibration regressions. UI fixtures verify layout; they are not
new hardware position accuracy tests. No live RTLS publishing was initiated.
