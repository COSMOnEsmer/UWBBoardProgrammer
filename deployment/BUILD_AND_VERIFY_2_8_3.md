# BLE recovery 2.8.3 build

Use Windows x64 and CPython 3.13.5. Keep the earlier 2.8.2 distribution ZIP and
manifest in place: the build copies only its hash-verified firmware/programmer
assets and vendor notices, without requiring a firmware rebuild.

1. Create a new virtual environment and install `deployment/requirements-2.8.3.lock.txt`.
2. Run `tools/verify_ble_recovery_suite_v1.py --skip-font-registration` using that interpreter.
3. Run `tools/package_desktop_v19_release.py`. Native dependency discovery uses
   a PATH containing only Python and Windows. The build rejects native DLLs
   originating outside that environment, preventing unrelated ICU/OpenSSL DLLs
   from host tools entering the package.
4. Run the executable with `--workspace <packaged directory> --smoke-output <new JSON path>`
   and optionally `--screenshots <new directory>`. This checks packaged GUI
   startup, Windows fonts, both languages and all six pages. It opens neither BLE
   nor RTLS automatically. Use QT_QPA_PLATFORM=offscreen for unattended capture.
5. Run `tools/build_github_distribution_v16.py`, then the launcher with
   `--root <repository> --verify-only --report <new JSON path>`. Preparing an
   installation uses `--prepare-only --no-shortcut`.
6. With the old application disconnected/closed and real boards powered, run
   `tools/verify_ble_recovery_v1.py --profile <local profile> --seconds 900`.
   It exercises A3 cancellation and missing-notification recovery while other
   anchors continue. A separate `--no-injection` run checks normal operation on
   the intended power supply. There is no flashing, UWB control or cloud output.
7. After closing acquisition, enumerate Windows' connected BLE devices and
   confirm no UWB connection remains when no other app is using these boards.

Packaging tools refuse to replace an existing build. Preserve failed attempts
separately before rebuilding. Personal profiles, credentials, recordings and
verification captures are excluded from the ZIP. Earlier releases remain intact.

The launcher accepts `--workspace <existing workspace>` and also reads the optional,
ignored `config/local-runtime-workspace.v1.txt`. This keeps existing profiles,
recordings and DPAPI credentials in place across software upgrades. The desktop
shortcut preserves an explicit workspace selection; normal launches choose the
latest saved profile in that workspace.

`--skip-font-registration` affects only offscreen regression fixtures. The product
keeps its normal Windows fonts; the separate packaged screenshot test verifies them.
