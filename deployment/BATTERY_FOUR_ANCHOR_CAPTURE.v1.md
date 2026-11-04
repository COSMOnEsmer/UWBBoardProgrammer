# Exact 2.3.0 four-anchor BLE Tag backend test

4 November 2026. User confirmed Tag on CR2032 with USB unplugged, performed
Reset to reopen its BLE window, and kept all four anchors powered. The exact
`capture_reference_ble` function used by the GUI was exercised without COM access.

| Anchor | Records | LOS | NLOS | Failed | Result |
|---|---:|---:|---:|---:|---|
| A1 | 124 | 124 | 0 | 0 | Accepted median 0.86 m |
| A2 | 124 | 124 | 0 | 0 | Accepted median 1.48 m; 121 retained |
| A3 | 122 | 0 | 122 | 0 | Rejected for insufficient LOS |
| A4 | 127 | 0 | 0 | 127 | Rejected; status 0x21 / RX timeout |

The SDK defines 0x21 as `UCI_STATUS_RANGING_RX_TIMEOUT`. The reported distance
0xFFFF is invalid and was excluded; it is not a measured 655.35 m range.
The backend returned incomplete, retained only A1/A2 and did not calculate XYZ.

Additional A4 diagnosis explicitly connected and held master A1, so its SYNC
transmitter was silenced. A4 still returned 124 RX timeouts. Reversing TWR roles
(Tag initiator, A4 responder) then produced 127 successful measurements, all flagged
NLOS. This shows role-dependent behavior; it does not establish a single physical
cause or a valid A4 calibration range. Further RF/configuration diagnosis remains.

These are diagnostics at one Tag placement. They do not establish a complete
four-point survey, correct installation geometry or 3D accuracy. Quality gates
were not relaxed, measurements from different placements were not merged into
a position solution, and no RTLS data was published. Radio restoration was acknowledged.

Local evidence:

- `verification/battery-reference-20261104T011714032319Z/report.json`
- `verification/battery-tag-pair-20261104T012435775911Z/report.json`
- `verification/battery-role-reverse-20261104T012721116529Z/report.json`

The released BLE battery-control feature is functional on the tested Tag. Complete
survey acceptance still depends on collecting valid ranges from all four fixed
anchors at four measured reference points. Current/lifetime measurements remain separate.
