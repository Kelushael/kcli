# KCLI Installer Build Instructions

This folder contains files to build a proper Windows Setup Wizard for KCLI.

## Prerequisites

1. **Python 3.10+** with pip
2. **PyInstaller** for creating the .exe
3. **Inno Setup** (optional) for creating the Setup Wizard

## Quick Build (Just the .exe)

```powershell
# From the kcli_desktop folder
cd kcli_desktop

# Install dependencies
pip install pyinstaller httpx colorama

# Build
pyinstaller --onefile --name kcli --console kcli/__main__.py

# Your .exe is at: dist/kcli.exe
```

## Full Installer Build (Setup Wizard)

### Step 1: Build the .exe
```powershell
.\build.bat
```

### Step 2: Install Inno Setup
Download from: https://jrsoftware.org/isinfo.php

### Step 3: Compile the Installer
1. Open `installer/kcli.iss` in Inno Setup
2. Press F9 or Build > Compile
3. The installer will be at: `installer/output/KCLI-Setup-1.0.0.exe`

## Alternative: One-Line PowerShell Install

If you don't want to build an installer, users can install with:
```powershell
irm https://your-domain.com/install.ps1 | iex
```

## File Structure

```
kcli_desktop/
├── kcli/                  # Python package
│   ├── __init__.py
│   ├── __main__.py
│   ├── agent.py           # Main CLI agent
│   ├── config.py          # Configuration
│   ├── providers.py       # AI provider adapters
│   └── tools.py           # Desktop Commander tools
├── installer/
│   ├── kcli.iss           # Inno Setup script
│   └── README.md          # This file
├── assets/                # Icons and images
├── build.bat              # Build script
├── install.ps1            # PowerShell installer
├── kcli.spec              # PyInstaller spec
├── pyproject.toml         # Python package config
└── README.md              # Main readme
```

## Customization

### Change the Icon
1. Create a 256x256 .ico file
2. Save as `assets/kcli.ico`
3. Rebuild with PyInstaller

### Change Installer Wizard Images
1. Create `assets/wizard.bmp` (164x314 pixels)
2. Create `assets/wizard-small.bmp` (55x58 pixels)
3. Recompile with Inno Setup
