# Adds a Startup-folder shortcut so Jarvis starts when you log in.
# Remove it with: Remove-Item "$([Environment]::GetFolderPath('Startup'))\Jarvis.lnk"
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Shortcut = Join-Path ([Environment]::GetFolderPath("Startup")) "Jarvis.lnk"

$link = (New-Object -ComObject WScript.Shell).CreateShortcut($Shortcut)
$link.TargetPath = "wscript.exe"
$link.Arguments = "//B //Nologo `"$(Join-Path $Root 'start_jarvis.vbs')`""
$link.WorkingDirectory = $Root
$link.Description = "Jarvis local assistant"
$link.Save()
Write-Host "Created $Shortcut"
