# Auto Survey firmware for application 2.2.0

The distributed ZIP embeds the complete six-image bundle. End users do not build
firmware or install the SDK. The desktop image selector resolves the manifest,
checks the binary SHA-256, boot vectors/header CRC, provisioned MAC/interval/role
CRC, and backs up the selected physical board before programming.

| Label | Version | Source/build |
|---|---|---|
| master, slave2, slave3, slave4 | 1.4.1-pilot | `source/v22-auto-survey-mac`, `tools/build_firmware_auto_survey_v2.py` |
| tag_setup (USB calibration) | 1.4.2-pilot | `source/v23-auto-survey-tag`, `tools/build_firmware_auto_survey_v4.py` |
| tag_battery | 1.3.4-pilot | Preserved `source/v20-paced-telemetry-pilot`, existing battery image |

The complete manifest is frozen by `tools/assemble_auto_survey_bundle_v1.py` from
the actual tested images. It records per-image versions; the Tag battery image
intentionally remains unchanged. Experimental 1.4.0 images using unsupported
DS-TWR extended addressing are not selected or distributed in this bundle.

DS-TWR uses distinct 16-bit MAC suffixes for ranging. BLE identity and the normal
UL-TDoA network retain the commissioned 64-bit MACs. The PC verifies that all four
anchors and Tag have distinct suffixes before survey acquisition.

The custom BLE service adds leased HOLD/RESPONDER/INITIATOR/RESTORE commands, request
and session binding, CRC-protected range records, and radio status acknowledgement.
The firmware returns to normal standalone radio operation after each operation,
on BLE disconnection, or when the radio command lease expires (maximum 30 seconds).
No persistent radio-role changes or OTP writes are used by calibration.

The USB Tag image intentionally disables MCU power-down so UART calibration
commands remain available. **Do not use it as the normal CR2032 image.** The
wizard restores the separately preserved battery image on save by default.

Developer builds need the original licensed Murata/NXP SR150/SR040 SDK archives,
matching Murata EVK patches, QN9090 support and GNU Arm toolchain at the paths
specified by the scripts. Each build uses a fresh SDK copy; vendor originals and
earlier build output are never modified. Raw SDK source/archives and local board
backups are not published in this repository. Binary notices/EULAs accompany the
portable application. Rebuilding is separate from running the provided app.

Real Rev4.1 Flash/boot, selected TWR links and radio restoration were tested.
Completed four-reference physical survey and held-out 3D positioning accuracy
remain separate acceptance work; source compilation and synthetic tests do not
establish RF accuracy.
