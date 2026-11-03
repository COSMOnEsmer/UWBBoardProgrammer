# UWB Board Programmer 2.1.2 — Position diagnostics

Run **START_HERE_2_1_2.cmd** or the **UWB Board Programmer 2.1.2** Desktop shortcut.
Earlier versions remain intact. Board firmware remains **1.3.4-pilot**.

BLE 4/4 confirms board connections. RF frames and Tag age confirm incoming observations.
A position also needs matching BLINKs, validated RF clocks, an unambiguous solution and acceptable uncertainty.
Live positioning now retains the latest solver rejection, displays evaluated group counts and measured/allowed uncertainty,
and explains individual clock readiness failures. Later SYNC notifications cannot hide the diagnostic rejection.
Start is disabled while processing; duplicate Start requests retain the clock model.

The clock algorithm, position solver and acceptance thresholds are unchanged. This update improves diagnosis;
it does not establish successful real-RF 3D positioning.

In the user-confirmed 4 November 2026 reference test, anchors were configured at
A1=(-1,1,1), A2=(1,1,2), A3=(1,-1,1), A4=(-1,-1,1) metres and the Tag at (0,0,1.5).
All expected anchor distances are 1.5 m. Thirteen complete groups instead had median range differences
to A1 of 0.582 m, 1.253 m and 1.243 m for A2/A3/A4; A4 flagged NLOS in all 13.
All groups failed the uncertainty criterion. Constant delays, survey error, NLOS and clock errors remain unseparated.
No compensation is automatically applied from this single reference.

At that point, even ideal clocks and LOS produce a model-predicted Z95 of approximately 1.247 m
under the configured 0.30 m pairwise TDoA noise assumption, exceeding the 1 m acceptance limit.
This is a model calculation, not measured RF accuracy. Reference calibration must be independently checked
at different positions/heights before accuracy claims or live RTLS acceptance.

See the [2.1.1 guide](INTEGRATED_STANDALONE_GUIDE.v2.en.md) for connection and surveyed-profile steps.
