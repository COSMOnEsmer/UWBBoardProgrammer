# GitHub Windows distribution 1

The payload is a normal Git blob below 100 MiB, not an LFS pointer or a link
to a build on the original developer's PC. `main` must contain it as well as
the launcher and JSON manifest so ordinary clones work.

`START_HERE.cmd` runs the included .NET Framework launcher. It verifies the
ZIP SHA-256, validates every installed file, and extracts into a new ignored
`%LOCALAPPDATA%/UWBBoardProgrammer/Git/<repo-hash>` directory. The shorter
path allows deeply nested/Unicode clone folders. Each clone has its own workspace.
Settings and measurements are not committed.
Corrupt installs are retained and repaired into a new directory. A profile
or language preference in an older source workspace is copied only when a
new destination file does not already exist. Credentials are never imported
from the source workspace. There are no pip/network/bootstrap downloads.

The launcher is built from `deployment/Bootstrap.cs` using the Windows
.NET Framework C# compiler, with an asInvoker manifest and long-path support.
It does not request administrator privileges. Its `.exe.config` is required.
Dependencies are unmodified dynamically loaded files in the archive, with
third-party license notices. Raw vendor SDK archives are not published.

Developer build, on the original build workstation:

```powershell
& 'runtime/python-v1/Scripts/python.exe' 'tools/build_github_distribution_v1.py'
```

This build consumes the verified v5 desktop build, local package metadata
and vendor SDK license registers. It refuses to overwrite an earlier output.
Use a new distribution revision for future builds. It is not an installation
step for users or a reproducible source build of the vendor SDK.

Developer portability verification:

```powershell
& 'runtime/python-v1/Scripts/python.exe' 'tools/verify_github_distribution_v1.py'
```

This creates a separate checkout-like folder with Thai characters and spaces,
using only shipped deployment files. The child launcher/app PATH contains
only Windows. It verifies first-run extraction, cache reuse, six full UI pages,
four anchor rows, embedded firmware discovery, cache repair without replacing
the damaged copy, and rejection of missing/corrupt payloads, ZIP traversal and
unlisted files. No board flash or RTLS transmission is initiated.

Launcher diagnostics (paths must be new):

```powershell
& 'deployment/windows-x64/UWB_Board_Programmer_Launcher.exe' --root . --verify-only --report report-new.json
& 'deployment/windows-x64/UWB_Board_Programmer_Launcher.exe' --root . --prepare-only --no-shortcut --report preparation-new.json
```

The normal GUI shortcut points to this launcher and the clone's own root,
so pulling a new distribution selects the manifest shipped with that clone.
Existing unrelated Desktop shortcuts are preserved. Runtime caches are local;
when changing application/package versions, retain the previous installation
and import its saved profile with Load Profile. Session recordings remain in
their original installation.
