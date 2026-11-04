# 2.6.0: continuous local display, independent gateways and movable windows

## Behaviour

- The local display has an independent approximate RF clock/TDoA estimator. Matching real BLINK frames from all four anchors are still required. Diagnostic estimates are amber and never become accepted fixes or enter the cloud publication callback. The strict solver's quality thresholds remain unchanged.
- The marker eases toward new estimates over about 0.25 seconds, remains visible during missing measurements, and turns grey with last-known age after three seconds. There is no invented motion during an outage. The fading path now retains 30 seconds; gaps over two seconds are not joined.
- Workspace panels, including the shared activity log, use movable/resizable native MDI subwindows. Detached windows contain their own Attach button. Internal scrolling preserves access to controls when panels are small. Tile/Cascade/Show all actions restore layouts. Layout geometry is currently session-local.
- New profiles use generic site/floor placeholders, A1–A4 and Tag-1. The dashboard URL follows the profile's site/floor. Existing user-defined IDs remain intact; no server identifiers are renamed automatically.
- Use gateway configuration retrieves the token-scoped site/floors/anchors, lets the user map physical MACs to server IDs, and saves a new local profile. Server coordinates are optional and require explicit confirmation before becoming a measured survey. It does not change server configuration.
- Authentication and publication readiness are separate. A gateway can authenticate and heartbeat while publishing is paused for an ID/coordinate mismatch. Queued messages are discarded if readiness is lost.
- The missing runtime TLS policy file is now packaged. The previous frozen executable failed in SSLContext initialization before authentication. Certificate verification remains enabled. The launcher selects the newest saved profile by modification time rather than its filename prefix.

## Verification

- 53 software tests passed, including RF estimate timing bounds, no accepted promotion, profile scope, movable/resizable panel geometry, floating-window Attach and 30-second path expiry.
- All six pages captured in English and Thai; native workspace layout inspected visually.
- A local recorded hardware session produced 37 continuous display estimates, zero accepted strict fixes and no replay exceptions. This is a recording replay, not a new live positioning accuracy test. The user recording is excluded from the repository.
- Final frozen executable completed HTTPS and received HTTP 401 without a token, confirming transport/TLS initialization.
- The user's already saved encrypted credential authenticated successfully through the real configuration API and /edge Socket.IO namespace. No positions were published and server configuration was not changed. The configuration returned one floor and zero anchors: provisioning/mapping is still required before coordinate publication.
- Portable launcher passed nine checks with Python removed from its launch PATH, including Unicode paths, hashes, first install, reuse, repair without overwrite, application startup and invalid archive rejection. Desktop installation verified all 584 files.

## Limits

Approximate display estimates are for debugging and may jump or choose an incorrect 3D branch with poor geometry. A continuous marker is not proof of continuous RF reception or accuracy. Correct anchor geometry, clock calibration and registered server mappings remain necessary for accepted RTLS positions. No new firmware or hardware accuracy claim accompanies this desktop update. Earlier files and RTLSSimulator are preserved.
