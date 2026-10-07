$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskExe = Join-Path $taskRoot 'releases\desktop-v3\UWB_Board_Programmer\UWB_Board_Programmer.exe'
$taskIcon = Join-Path $taskRoot 'resources\branding\logo-v1.ico'
if (-not (Test-Path -LiteralPath $taskExe)) { throw 'Build the desktop executable before creating shortcuts.' }
$taskDesktop = 'C:\Users\PC\OneDrive\Desktop'
$taskTargets = @((Join-Path $taskRoot 'UWB Board Programmer 2.0.1.lnk'), (Join-Path $taskDesktop 'UWB Board Programmer 2.0.1.lnk'))
$taskShell = New-Object -ComObject WScript.Shell
foreach ($taskTarget in $taskTargets) {
    if (Test-Path -LiteralPath $taskTarget) { throw "Shortcut already exists; choose a new name: $taskTarget" }
    $taskLink = $taskShell.CreateShortcut($taskTarget)
    $taskLink.TargetPath = $taskExe
    $taskLink.WorkingDirectory = $taskRoot
    $taskLink.IconLocation = "$taskIcon,0"
    $taskLink.Description = 'UWB Board Programmer - Murata Type2BP / Type2DK workspace'
    $taskLink.Save()
    Write-Output $taskTarget
}
