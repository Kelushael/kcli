# KCLI Windows Installer (PowerShell)
# Run with: irm <url> | iex

$ErrorActionPreference = 'Stop'

Write-Host @"

╔══════════════════════════════════════════════════╗
║         KCLI Desktop Commander             ║
║         Installer v1.0.0                   ║
╚══════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

$InstallDir = "$env:LOCALAPPDATA\KCLI"
$BinDir = "$InstallDir\bin"

# Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "      Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "      Python not found. Installing via winget..." -ForegroundColor Red
    winget install Python.Python.3.12 --silent
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Create directories
Write-Host "[2/5] Creating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\kcli" | Out-Null
Write-Host "      Created: $InstallDir" -ForegroundColor Green

# Download KCLI
Write-Host "[3/5] Downloading KCLI..." -ForegroundColor Yellow
$RepoUrl = "https://github.com/kelushael/kcli/archive/refs/heads/main.zip"
$ZipPath = "$env:TEMP\kcli.zip"
try {
    Invoke-WebRequest -Uri $RepoUrl -OutFile $ZipPath -UseBasicParsing
    Expand-Archive -Path $ZipPath -DestinationPath $env:TEMP -Force
    Copy-Item -Path "$env:TEMP\kcli-main\kcli\*" -Destination "$InstallDir\kcli" -Recurse -Force
    Copy-Item -Path "$env:TEMP\kcli-main\pyproject.toml" -Destination $InstallDir -Force
    Write-Host "      Downloaded successfully" -ForegroundColor Green
} catch {
    Write-Host "      Could not download from GitHub. Installing via pip..." -ForegroundColor Yellow
    pip install kcli --target $InstallDir 2>&1 | Out-Null
}

# Install dependencies
Write-Host "[4/5] Installing dependencies..." -ForegroundColor Yellow
pip install httpx colorama --quiet 2>&1 | Out-Null
Write-Host "      Dependencies installed" -ForegroundColor Green

# Create launcher script
Write-Host "[5/5] Creating launcher..." -ForegroundColor Yellow
$LauncherContent = @"
@echo off
python -m kcli %*
"@
$LauncherContent | Out-File -FilePath "$BinDir\kcli.cmd" -Encoding ASCII

# Add to PATH
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$CurrentPath;$BinDir", "User")
    $env:Path = "$env:Path;$BinDir"
    Write-Host "      Added to PATH" -ForegroundColor Green
}

# Create desktop shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\KCLI.lnk")
$Shortcut.TargetPath = "cmd.exe"
$Shortcut.Arguments = "/k kcli"
$Shortcut.WorkingDirectory = "$env:USERPROFILE"
$Shortcut.Description = "KCLI Desktop Commander"
$Shortcut.Save()
Write-Host "      Desktop shortcut created" -ForegroundColor Green

# Done!
Write-Host @"

╔══════════════════════════════════════════════════╗
║         Installation Complete!             ║
╚══════════════════════════════════════════════════╝

To get started:
  1. Open a NEW PowerShell window
  2. Type: kcli
  3. Set your API key with /config or:
     `$env:OPENROUTER_API_KEY = "your-key"`

Get a free API key at: https://openrouter.ai/keys

"@ -ForegroundColor Cyan

# Offer to start KCLI now
$start = Read-Host "Start KCLI now? [Y/n]"
if ($start -ne 'n') {
    & "$BinDir\kcli.cmd"
}
