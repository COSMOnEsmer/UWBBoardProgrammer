# UWB Board Programmer 2.6.0

Run START_HERE_2_6_0.cmd on Windows 10/11 x64. The complete Python/Qt runtime, BLE receiver, firmware and USB programmer are included. Install the USB driver if Windows does not show the board's COM port. A working Windows Bluetooth LE adapter is required for BLE acquisition. No firmware update is required when upgrading from 2.5.0.

## Live display

Connect BLE, load a measured survey profile, then start positioning. Four-anchor TDoA uses matching RF BLINK frames and RF clock synchronization; PC/BLE arrival times are not used as propagation times. Hybrid three-anchor positioning additionally requires calibrated AoA.

Continuous display estimates (local only) is enabled initially. It uses a separate approximate clock fit and a bounded TDoA solution when the stricter validated solution is unavailable. Amber points are diagnostic estimates, not confirmed accuracy. The displayed point eases toward each measurement over approximately 0.25 seconds. It does not predict motion through an RF outage. Without a recent solvable observation, the marker remains at its last position, turns grey, and shows its age. A persistent marker does not mean a new measurement was received.

The fading path contains the last 30 seconds of measured/estimated points. Gaps over two seconds are not joined. Rotating and zooming work in 3D; double-click switches 2D/3D. Green anchors have recent reception/connection evidence; grey indicates unavailable/stale status.

Strict/RTLS diagnostics report why a quality-checked fix was rejected. Display updates and accepted fixes have separate counters. Approximate estimates, old held markers and replay results are never published as accepted live positions.

## Windows

Each workspace contains movable native subwindows. Drag the title bar to move and drag an edge or corner to resize. Scroll inside a small panel to reach its controls. Tile panels, Cascade panels and Show all panels arrange or restore windows. Detach opens the same live controls in a separate resizable window. Click Attach inside that window, click Attach on its original panel, or close the detached window to restore it. Activity log can also be detached and resized.

## Independent workspaces and RTLS

New profiles use generic A1–A4 and Tag-1 IDs. Existing profiles retain their identifiers and geometry to protect device/cloud mappings. Edit IDs or use gateway configuration to create a new profile for another installation. No site or floor is fixed in the program.

1. In the RTLS dashboard create/select the intended site, floor, gateway, anchors and Tag. Use a gateway bearer token, not a dashboard login password.
2. Disconnect BLE/RTLS before changing scope. Enter the gateway ID and token, then click **Use gateway configuration** in **Workspace actions**. Select the floor and map each physical anchor to its server anchor ID. Enter the registered Tag ID.
3. Keep your measured coordinates, or explicitly choose server coordinates only if they describe the real installation. Confirm measured installation only after checking it. The operation saves a new local profile and does not change server configuration.
4. Click **Check configuration**, then **Connect RTLS**. Site/floor/anchor IDs, roles and measured coordinates must match. A valid authenticated connection may stay online while publishing is paused for a configuration mismatch; the log gives the mismatch. Correct it before publishing.
5. Start BLE positioning and enable publishing. Only fresh accepted live fixes are queued. During an outage recording continues locally; old queued positions are discarded. Watch RTLS status/acknowledgements and the Tag on the selected floor.

Save encrypted token if desired. Windows DPAPI binds saved credentials to your Windows user; enter a token again on another laptop. Portable distributions contain no tokens, recordings or personal profiles.

2.6.0 includes the runtime TLS policy certificate omitted from the earlier package. HTTPS verification stays enabled. A successful unauthenticated diagnostic returns HTTP 401, proving TLS transport only; it does not prove your gateway token or server mapping is valid.
