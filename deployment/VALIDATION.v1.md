# Windows distribution validation — 2026-10-28

Application 2.1.0; payload SHA-256:
`0e8b1137ea4ce50726cab38d2cad097d772bdcf865c705b8feb3110710129ff9`.
The normal Git ZIP contains 554 verified files, 95,394,284 bytes compressed.

Completed checks:

- Nine launcher/portability checks passed: archive integrity, first installation,
  installation reuse, full packaged UI launch without Python on PATH, repair
  without overwriting the damaged copy, repaired-install reuse, and rejection
  of ZIP traversal, unlisted archive files and incomplete payloads.
- Twelve existing integrated UI/controller regression tests passed.
- A fresh shallow clone of GitHub **main**, commit
  `8bb64fd95442e953914657fd4173e0e98b3b226a`, launched the shipped package
  successfully from a new folder with Thai characters and spaces. Its child
  PATH contained only Windows directories. The clone had no local Python
  environment, vendor SDK, credentials or unpacked firmware directory.
- The packaged UI reported six pages, four anchor rows, five device rows,
  embedded firmware discovery and Standalone BLE transport. Acquisition and
  cloud transmission remained off until explicitly started.
- The new Desktop shortcut was created successfully while older shortcuts
  and source files were preserved. First-run extraction and all file hashes
  were checked again using the payload actually downloaded from GitHub.

Tests ran on the existing Windows workstation with isolated checkout and
application folders; a physically different laptop was not available. These
checks establish software packaging/launch portability, not four-anchor RF
or RTLS end-to-end acceptance. No board was flashed during these tests.
