# Coordinate registration in 2.8.0

The approved plan separates the Tag-reference Survey frame from the RTLS Floor frame. Implementation preserves the source survey and rigid transform, but solves directly in the registered Floor frame rather than transforming every fix afterward. For a rigid registration, distances and TDoA remain unchanged. Anchor orientations rotate with the frame, so AoA and the solver's derived uncertainty remain in the same frame. There is no output offset that could be applied twice. Floor bounds are an explicit workspace prior.

## Commissioning result

The supplied TechnoPark / Ground Floor gateway configuration was retrieved with the user's credential. Its four Anchor positions match the requested A4-XY-origin registration of the latest local survey:

| Anchor | Floor X | Floor Y | Floor Z |
| --- | --- | --- | --- |
| TP-A1 | 0.688 | 0.878 | 0.891 |
| TP-A2 | 2.013 | 0.895 | 1.891 |
| TP-A3 | 2.450 | 0.037 | 0.779 |
| TP-A4 | 0 | 0 | 0.518 |

Yaw=0°, translation=(1.132,0.426,0) m, rectangular bounds=(0,0,0) to (4,4,2), level index=0, elevation=0. Existing Z was preserved as requested. This confirms numerical/server agreement, not independently measured physical height or RF accuracy.

A new user-specific active floor profile was installed separately from the portable package. Site/Floor IDs came from authenticated configuration. The Windows-encrypted credential was stored only locally. Neither credentials nor the personal profile are committed or distributed.

## Verification

- 78 regression tests passed; 20 directly cover registration, the A4 dataset, rigid/inverse transformations, distance/AoA invariance, scale/reflection/height rejection, eight-corner bounds, schema migration, GUI formatting, no repeated offset, changed-frame guards and display/payload consistency.
- Native UI captures cover six workflows, two languages and three display sizes, plus the registration wizard with static example geometry. No live RF values are fabricated for UI evidence.
- The actual server accepted authentication, floor/Anchor configuration validation and one heartbeat acknowledgement. No positions or raw measurements were sent; server configuration was not changed.
- Nine portable checks passed, including first install, reuse, non-destructive repair, startup without external Python, Unicode paths and bad archive rejection.
- The frozen executable contains the coordinate/alignment modules and loads the prepared real floor profile with no automatic acquisition/cloud connection.

## Operational limits

The registration is yaw+translation at scale 1 and requires physically vertical +Z. Floor bounds/rendering use the rectangular dimensions for this installation; an imported footprint is retained as metadata, not enforced as a polygonal solver constraint. Independent checkpoint input checks frame agreement, not a new live RF accuracy claim. Clock synchronization, antenna delay, multipath and 3D observability remain separate concerns. Legacy profiles require explicit frame review before cloud publication. Source and prior application files remain intact.
