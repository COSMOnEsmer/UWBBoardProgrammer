param([string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
$integratedRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$integratedExe = Join-Path $integratedRoot 'releases/desktop-v5/UWB_Board_Programmer_2_1_0/UWB_Board_Programmer_2_1_0.exe'
if (-not (Test-Path -LiteralPath $integratedExe -PathType Leaf)) { throw 'Build the integrated 2.1.0 EXE first.' }
$integratedDesktop = [Environment]::GetFolderPath('Desktop')
$integratedShortcut = Join-Path $integratedDesktop 'UWB Board Programmer 2.1.0.lnk'
$integratedArguments = '--workspace "' + $integratedRoot + '"'
$integratedShell = New-Object -ComObject WScript.Shell
if (Test-Path -LiteralPath $integratedShortcut) {
    $integratedExisting = $integratedShell.CreateShortcut($integratedShortcut)
    if (($integratedExisting.TargetPath -ieq $integratedExe) -and ($integratedExisting.Arguments -ceq $integratedArguments)) {
        [PSCustomObject]@{Status='verified'; Shortcut=$integratedShortcut; Target=$integratedExe} | ConvertTo-Json
        return
    }
    $integratedStamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ',[Globalization.CultureInfo]::InvariantCulture)
    $integratedShortcut = Join-Path $integratedDesktop ("UWB Board Programmer 2.1.0 ($integratedStamp).lnk")
}
if (Test-Path -LiteralPath $integratedShortcut) { throw 'Preserving the existing shortcut.' }
$integratedLink = $integratedShell.CreateShortcut($integratedShortcut)
$integratedLink.TargetPath = $integratedExe
$integratedLink.Arguments = $integratedArguments
$integratedLink.WorkingDirectory = $integratedRoot
$integratedLink.IconLocation = $integratedExe + ',0'
$integratedLink.Description = 'Full UWB Board Programmer workspace with integrated Standalone firmware and BLE/GATT.'
$integratedLink.WindowStyle = 1
$integratedLink.Save()
[PSCustomObject]@{Status='created'; Shortcut=$integratedShortcut; Target=$integratedExe} | ConvertTo-Json
