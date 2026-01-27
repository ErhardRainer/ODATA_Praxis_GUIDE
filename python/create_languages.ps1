<#
PowerShell Wrapper für create_languages.py
- Keine CLI-Parameter; konfiguriere die Variablen unten.
- Default: Dry-Run (keine Änderungen). Setze $Apply = $true um Änderungen anzuwenden.
#>

# === Konfiguration (bearbeiten) ===
# Script-lokation ermitteln; wenn das PS-Skript in /python/ liegt, ist das Repo-Root eine Ebene höher.
$scriptDir = $PSScriptRoot

# Versuche mehrere Kandidaten zu finden, die das Repo-Root sein könnten (Script dir, parent, parent parent).
$candidate1 = Resolve-Path (Join-Path $scriptDir '..') -ErrorAction SilentlyContinue
$candidate2 = Resolve-Path (Join-Path $scriptDir '..\..') -ErrorAction SilentlyContinue

# Wähle das Verzeichnis, das eine Website/content Struktur enthält.
if (Test-Path (Join-Path $scriptDir 'Website\content')) {
    $RepoRoot = $scriptDir
} elseif ($candidate1 -and (Test-Path (Join-Path $candidate1 'Website\content'))) {
    $RepoRoot = $candidate1.Path
} elseif ($candidate2 -and (Test-Path (Join-Path $candidate2 'Website\content'))) {
    $RepoRoot = $candidate2.Path
} else {
    # Fallback: benutze Script-Ordner
    $RepoRoot = $scriptDir
}

$ContentRoot = Join-Path $RepoRoot 'Website\content'
$NavigationJson = Join-Path $RepoRoot 'Website\navigation.json'

# Setze $Apply auf $true, um Rename/Copy und navigation.json-Update anzuwenden
$Apply = $false
# Update navigation.json (file -> files mapping). Setze $false, um dies zu deaktivieren.
$UpdateNavigation = $true

# Dry-Run als Variable (kein CLI-Parameter mehr). Default: $true.
$Dry = $false

# Python-Executable (versuche 'py' dann 'python')
$PythonExe = 'py'
$PythonArgs = '-3'

# Pfad zum Python-Script
$ScriptPath = Join-Path $RepoRoot 'python\create_languages.py'

# === Umsetzung der Argumente ===
# Apply hat Vorrang: wenn Apply gesetzt ist, erzwinge Dry = $false
if ($Apply) { $Dry = $false }

$argsList = @()
if ($Dry) { $argsList += '-dry' } else { $argsList += '--apply' }
if ($UpdateNavigation) { $argsList += '--update-navigation' } else { $argsList += '--no-update-navigation' }
$argsList += '--root'; $argsList += $ContentRoot
$argsList += '--navigation'; $argsList += $NavigationJson

Write-Host "[create_languages.ps1] RepoRoot: $RepoRoot"
Write-Host "[create_languages.ps1] ContentRoot: $ContentRoot"
Write-Host "[create_languages.ps1] Navigation: $NavigationJson"
Write-Host "[create_languages.ps1] Apply: $Apply"
Write-Host "[create_languages.ps1] UpdateNavigation: $UpdateNavigation"
Write-Host "[create_languages.ps1] Running: $PythonExe $PythonArgs $ScriptPath $($argsList -join ' ')" -ForegroundColor Cyan

# Versuche exec
try {
    $cmd = @($PythonExe, $PythonArgs, $ScriptPath) + $argsList
    & $cmd[0] $cmd[1..($cmd.Count - 1)]
    $exit = $LASTEXITCODE
    if ($null -eq $exit) { $exit = 0 }
    Write-Host "[create_languages.ps1] Exit code: $exit"
    exit $exit
} catch {
    Write-Error "Fehler beim Aufruf: $_"
    exit 2
}
