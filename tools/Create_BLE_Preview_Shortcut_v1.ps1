param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$previewRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$previewPython = Join-Path $previewRoot 'runtime/python-v1/Scripts/pythonw.exe'
$previewLauncher = Join-Path $previewRoot 'tools/launch_ble_bench_v7.py'
$previewIcon = (Join-Path $previewRoot 'resources/branding/logo-v1.ico') + ',0'
foreach ($previewRequired in @($previewPython, $previewLauncher)) {
    if (-not (Test-Path -LiteralPath $previewRequired -PathType Leaf)) {
        throw "Required local file missing: $previewRequired"
    }
}
$previewDesktop = [Environment]::GetFolderPath('Desktop')
$previewShortcut = Join-Path $previewDesktop 'UWB Board Programmer - BLE Preview.lnk'
$previewArguments = '"' + $previewLauncher + '"'
$previewShell = New-Object -ComObject WScript.Shell
if (Test-Path -LiteralPath $previewShortcut) {
    $previewExisting = $previewShell.CreateShortcut($previewShortcut)
    if (($previewExisting.TargetPath -ieq $previewPython) -and
        ($previewExisting.Arguments -ceq $previewArguments) -and
        ($previewExisting.WorkingDirectory -ieq $previewRoot) -and
        ($previewExisting.IconLocation -ieq $previewIcon)) {
        [PSCustomObject]@{Status='verified'; Shortcut=$previewShortcut; Target=$previewPython; Launcher=$previewLauncher} | ConvertTo-Json
        return
    }
    if ($VerifyOnly) { throw 'Existing shortcut points elsewhere; it was preserved.' }
    $previewSuffix = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ', [Globalization.CultureInfo]::InvariantCulture)
    $previewShortcut = Join-Path $previewDesktop ("UWB Board Programmer - BLE Preview ($previewSuffix).lnk")
}
if ($VerifyOnly) { throw 'Desktop preview shortcut is missing.' }
if (Test-Path -LiteralPath $previewShortcut) { throw 'Preserving existing shortcut.' }
$previewNew = $previewShell.CreateShortcut($previewShortcut)
$previewNew.TargetPath = $previewPython
$previewNew.Arguments = $previewArguments
$previewNew.WorkingDirectory = $previewRoot
$previewNew.IconLocation = $previewIcon
$previewNew.Description = 'Standalone BLE pilot for firmware 1.3.4. Separate from released UWB Board Programmer 2.0.1.'
$previewNew.WindowStyle = 1
$previewNew.Save()
[PSCustomObject]@{Status='created'; Shortcut=$previewShortcut; Target=$previewPython; Launcher=$previewLauncher} | ConvertTo-Json
