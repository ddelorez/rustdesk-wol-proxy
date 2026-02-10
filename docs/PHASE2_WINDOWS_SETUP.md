# Phase 2: Windows Development Environment Setup Guide

**⚠️ Important Context Note**: This guide is for **Phase 2 only** (Windows native development). **Phase 1 (the Flask API) stays in WSL2** and does NOT move to Windows. See the sections below for clarity.

**Target**: Rust Windows client development for RustDesk
**Scope**: Complete Windows environment configuration
**Estimated Time**: 2-3 hours
**Hardware Requirements**: 200GB disk space, 8GB RAM minimum, 16GB recommended

---

## Phase 1 vs Phase 2: Context Clarity

**Your Current WSL2 Environment (Phase 1) - NO CHANGES NEEDED**:

- ✅ Python Flask API runs in **WSL2 Ubuntu 22.04**
- ✅ Deployed to production Linux server at **10.10.10.145**
- ✅ Continue all Phase 1 development in WSL2
- ✅ Your WSL2 environment is **ideal for Phase 1** — keep it as is
- ✅ No cross-compilation to Windows needed for Phase 1

**Phase 2 (This Guide) - Separate Native Windows Setup**:

- 🔧 Rust client development runs on **native Windows 10/11**
- 🔧 Phase 2 is on a **separate Windows machine** or in a separate development context
- 🔧 Phase 2 client calls the Phase 1 API via HTTP (over network or LAN)
- 🔧 No builds cross-compiled from WSL2 to Windows for Phase 2
- 🔧 Rust builds happen **natively on Windows** using MSVC toolchain

**Key Message**: Phase 1 and Phase 2 are completely separate. You develop Phase 1 in WSL2, Phase 2 on native Windows, and they communicate via the WOL API over HTTP.

### Network Communication Between Contexts

```
Phase 1 (WSL2/Linux)              Phase 2 (Windows Native)
┌──────────────────────────────┐  ┌──────────────────────────┐
│ Flask API @ 10.10.10.145:5001│  │ RustDesk Client on       │
│                              │  │ your Windows machine     │
│ Listens for WOL requests     │◄─┤ Calls WOL API when      │
│                              │  │ machine goes offline    │
│ Sends magic packets on LAN   │  │                         │
└──────────────────────────────┘  └──────────────────────────┘
     (Production server)              (Your Windows dev)
          network ←─────────HTTP/HTTPS communication────→
```

### File Sharing / Network Communication Between Contexts

**No file sharing is needed between Phase 1 and Phase 2.**

Instead, they communicate via **HTTP API**:

- **Phase 1 (API) listens** on: `http://10.10.10.145:5001/wake`
- **Phase 2 (Client) calls** the API when it detects an offline connection
- **Data transmission**: JSON over HTTP/HTTPS
- **Authentication**: API key passed as query parameter

**Development/Testing Across Contexts**:

1. **Phase 1 API must be running** (on Linux server or WSL2 during local testing)
2. **Phase 2 client is built** natively on Windows
3. **Phase 2 client connects** to Phase 1 API via HTTP
4. **Test cycle**: Build Phase 2 → Run it → Trigger WOL → Verify Phase 1 API sends packets

---

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Prerequisites and Pre-flight Checks](#prerequisites-and-pre-flight-checks)
3. [Installation Steps](#installation-steps)
4. [Post-Installation Verification](#post-installation-verification)
5. [Troubleshooting](#troubleshooting)
6. [Directory Structure](#directory-structure)
7. [Network Connectivity](#network-connectivity-verification)
8. [Quick Test Build](#quick-test-build)

---

## System Requirements

### Minimum Hardware
- **OS**: Windows 10 Build 19041+ or Windows 11
- **Processor**: x86_64 (Intel/AMD)
- **RAM**: 8GB minimum, 16GB recommended
- **Disk Space**: 200GB total (breakdown below)
- **Internet**: Stable connection (2+ Mbps recommended)

### Disk Space Breakdown
| Component | Size | Notes |
|-----------|------|-------|
| Windows SDK | 15-20GB | Multi-version support |
| Visual C++ Build Tools | 8-12GB | Includes MSVC compiler |
| Rust toolchain | 2-5GB | Multiple targets |
| CMake | 0.5GB | Build system |
| NASM | 0.1GB | Assembler |
| RustDesk fork source | 1-2GB | Git repository |
| Build artifacts | 50-100GB | Debug/Release builds |
| **Total** | **~200GB** | With build artifacts |

### Network Connectivity
- Static IP recommended for build machine
- No corporate proxy issues (or proxy configured)
- GitHub access required
- NuGet package access required

### Windows Edition
- Windows 10 Professional / Enterprise (LTSC)
- Windows 11 Professional / Enterprise
- Home edition can work but may have limitations with development tools

---

## Prerequisites and Pre-flight Checks

### Pre-flight Checklist
Before starting installation:

- [ ] Windows is fully updated (Check Settings > Update & Security > Windows Update)
- [ ] Administrator access confirmed
- [ ] UAC (User Account Control) enabled
- [ ] Antivirus exclusions added for dev directories (see Troubleshooting)
- [ ] 200GB free disk space verified
- [ ] RAM usage is below 75% (check Task Manager)
- [ ] Network connectivity working (`ping 8.8.8.8`)
- [ ] PowerShell execution policy allows scripts

### Check PowerShell Execution Policy

```powershell
# In PowerShell (Administrator), check current policy
Get-ExecutionPolicy

# If restricted, set to RemoteSigned
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Verify Windows Version

```powershell
# Check Windows version (must be build 19041+)
[System.Environment]::OSVersion.Version
wmic os get buildnumber
```

Expected output: Build number 19041 or higher

### Network Connectivity Verification

```powershell
# Test GitHub access
Test-NetConnection -ComputerName github.com -Port 443

# Test NuGet access
Test-NetConnection -ComputerName api.nuget.org -Port 443

# Test DNS
nslookup github.com
```

---

## Installation Steps

### ✓ Step 1: Git Installation

Git is required for cloning the RustDesk fork and version control.

**Manual Installation:**
1. Download from [git-scm.com](https://git-scm.com/download/win)
2. Run installer, accept defaults
3. Choose "Windows Explorer integration" (useful)
4. Select "Use Git from Windows Command Prompt" or "Use Git from Git Bash"

**Verification:**
```powershell
git --version
# Expected: git version 2.40.0 (or newer)
```

**Configuration:**
```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global core.autocrlf true  # Important for Windows!
git config --list
```

### ✓ Step 2: Visual C++ Build Tools Installation

**CRITICAL**: Must be done manually due to large download (8-12GB).

**Required Components:**
- MSVC v143 compiler
- Windows SDK
- CMake tools

**Manual Installation:**

1. Download [Visual Studio Build Tools 2022](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Run installer as Administrator
3. Select **"Desktop development with C++"** workload
4. Under **Optional**, also select:
   - Windows 10/11 SDK (latest)
   - CMake tools for Windows
5. Start installation (15-20 minutes)
6. Restart machine when prompted

**Verification:**
```powershell
# Check for MSVC compiler
& 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
# Should not produce errors

# Check MSVC version
cl.exe /v
# Expected: Microsoft (R) C/C++ Optimizing Compiler Version 19.3x.xxxxx
```

**Environment Variables to Verify:**
- `VCINSTALLDIR` should be set to Visual Studio installation path
- Path should include `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\...`

### ✓ Step 3: Windows SDK Installation

**If not installed with Build Tools:**

1. Download [Windows SDK Installer](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/)
2. Latest recommended: Windows 11 SDK
3. Run installer, select desired SDKs
4. Installation location: `C:\Program Files (x86)\Windows Kits\10` or `11`

**Verification:**
```powershell
# Check SDK presence
dir "C:\Program Files (x86)\Windows Kits\10\bin"
ls "C:\Program Files (x86)\Windows Kits\10\Include"

# Should show version folders like 10.0.22621.0
```

### ✓ Step 4: CMake Installation

**Manual Installation:**

1. Download [CMake 3.27+ for Windows](https://cmake.org/download/)
2. Choose "Windows x64 ZIP"
3. Extract to `C:\tools\cmake` (create directory first)
4. Skip installer if you prefer the ZIP method

**Alternative (Chocolatey, if installed):**
```powershell
choco install cmake
```

**Add to PATH:**

1. Press `Win + X` and select "System"
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "User variables" or "System variables", click "Path"
5. Click "New"
6. Add: `C:\tools\cmake\bin`
7. Click "OK" multiple times

**Or via PowerShell (Administrator):**
```powershell
# Add CMake to user PATH
$cmakePath = "C:\tools\cmake\bin"
$currentPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if ($currentPath -notlike "*$cmakePath*") {
    $newPath = "$currentPath;$cmakePath"
    [Environment]::SetEnvironmentVariable("Path", $newPath, [EnvironmentVariableTarget]::User)
    Write-Host "CMake added to PATH"
} else {
    Write-Host "CMake already in PATH"
}
```

**Verification:**
```powershell
# Reload environment (restart PowerShell or close/reopen terminal)
cmake --version
# Expected: cmake version 3.27.x or newer
```

### ✓ Step 5: NASM Installation

NASM (Netwide Assembler) required by some Rust dependencies.

1. Download [NASM installer](https://www.nasm.us/) (wininet installer)
2. Run installer, select `C:\tools\nasm` as installation directory
3. Keep all defaults

**Or via Chocolatey:**
```powershell
choco install nasm
```

**Verify Installation:**
```powershell
# NASM should be in PATH
nasm -version
# Expected: NASM version 2.16 or newer
```

**If Not in PATH Automatically:**

Add to PATH (same process as CMake):
- Add: `C:\tools\nasm` or installation directory

### ✓ Step 6: Rust Installation

Rust toolchain and x86_64-pc-windows-msvc target.

**Install rustup (official installer):**

1. Download from [rustup.rs](https://rustup.rs/)
2. Run `rustup-init.exe`
3. Press Enter to use default settings (installs stable)
4. Restart PowerShell or Command Prompt

**Verification:**
```powershell
rustup --version
# Expected: rustup 1.2x.x

rustc --version
# Expected: rustc 1.7x.x (stable)

cargo --version
# Expected: cargo 1.7x.x
```

**Install MSVC Target:**
```powershell
# Install x86_64-pc-windows-msvc target
rustup target add x86_64-pc-windows-msvc

# Verify
rustup target list | findstr msvc
# Should show: x86_64-pc-windows-msvc (installed)
```

**Rust Toolchain Structure:**
```
C:\Users\<USERNAME>\.rustup\toolchains\stable-x86_64-pc-windows-msvc\
├── bin\
│   ├── rustc.exe
│   ├── cargo.exe
│   └── ...
├── lib\
└── src\
```

### ✓ Step 7: RustDesk Fork Setup

Clone and configure the RustDesk fork for Windows development.

**Clone Repository:**
```powershell
# Navigate to development directory
cd C:\dev  # or preferred location, create if needed

# Clone the RustDesk fork
git clone https://github.com/<your-fork>/rustdesk.git
cd rustdesk

# Add upstream remote (to track original)
git remote add upstream https://github.com/rustdesk/rustdesk.git
```

**Verify Clone:**
```powershell
# Check remotes
git remote -v
# Should show origin and upstream

# Check branch
git branch -a
# Should show local and remote branches
```

**Windows-Specific Branch Setup:**
```powershell
# Ensure you're on appropriate branch
git checkout master  # or specific Windows development branch

# Fetch latest updates
git fetch upstream
git fetch origin

# Update local branch
git pull origin master
```

**Directory Structure After Clone:**
```
C:\dev\rustdesk\
├── .github\
├── .gitignore
├── Cargo.toml          (Main workspace manifest)
├── Cargo.lock
├── src\                (Main source)
│   ├── bin\            (Binaries: rustdesk, rustdesk-rc.exe, etc.)
│   ├── client.rs
│   ├── server.rs
│   └── ...
├── flutter\            (Flutter UI)
├── contrib\            (Contributions, scripts)
│   └── build\          (Build scripts for Windows)
├── README.md
└── Cargo.toml
```

---

## Post-Installation Verification

### ✓ Verification Checklist

Run through each verification in order to ensure all components work together:

#### 1. Rust Toolchain
```powershell
Write-Host "=== Rust Toolchain Verification ===" -ForegroundColor Green
rustup show
rustup toolchain list
rustup target list | findstr msvc
```

Expected output:
- Active toolchain: `stable-x86_64-pc-windows-msvc`
- Installed target: `x86_64-pc-windows-msvc (installed)`

#### 2. C++ Build Environment
```powershell
Write-Host "=== C++ Build Environment ===" -ForegroundColor Green

# Check MSVC compiler
cl.exe /v

# Check linker
link.exe /?

# Check include paths
echo %INCLUDE%
```

#### 3. Windows SDK
```powershell
Write-Host "=== Windows SDK Verification ===" -ForegroundColor Green
ls "C:\Program Files (x86)\Windows Kits\10\Include"
```

#### 4. Build Tools PATH
```powershell
Write-Host "=== Build Tools PATH Verification ===" -ForegroundColor Green
$env:Path -split ';' | findstr /i "visual|cmake|nasm"
```

Should output paths containing:
- "Visual Studio"
- "cmake" or "CMake"
- "nasm"

#### 5. Git Configuration
```powershell
Write-Host "=== Git Configuration ===" -ForegroundColor Green
git config --global --list | findstr user
git config --global --list | findstr core
```

#### 6. Clone and Inspect RustDesk
```powershell
Write-Host "=== RustDesk Fork Verification ===" -ForegroundColor Green
cd C:\dev\rustdesk
git remote -v
git status
ls -l
```

#### 7. Cargo Clean Test
```powershell
Write-Host "=== Cargo Configuration ===" -ForegroundColor Green
cargo --version
cargo config get directories

# Test cargo build directory
cargo metadata --format-version 1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Cargo build system ready" -ForegroundColor Green
}
```

### Full Verification Script

Save as `verify-setup.ps1`:

```powershell
# Full environment verification script
param(
    [string]$RustDeskPath = "C:\dev\rustdesk"
)

function Test-Command {
    param([string]$Command)
    $null = & $Command 2>$null
    return $LASTEXITCODE -eq 0
}

Write-Host "`n=== Full Environment Verification ===" -ForegroundColor Cyan
Write-Host "Timestamp: $(Get-Date)" -ForegroundColor Gray

# Test each component
$checks = @{
    "Git" = "git --version"
    "Rust" = "rustc --version"
    "Cargo" = "cargo --version"
    "CMake" = "cmake --version"
    "NASM" = "nasm -version"
}

$passed = 0
$failed = 0

foreach ($tool in $checks.Keys) {
    $command = $checks[$tool]
    $result = &$command 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ $tool" -ForegroundColor Green
        Write-Host "  $result" -ForegroundColor Gray
        $passed++
    } else {
        Write-Host "✗ $tool" -ForegroundColor Red
        $failed++
    }
}

# Test MSVC
Write-Host "`nChecking MSVC compiler..." -ForegroundColor Yellow
$msvcPath = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\bin\Hostx64\x64\cl.exe"
if (Test-Path $msvcPath) {
    Write-Host "✓ MSVC compiler found" -ForegroundColor Green
    $passed++
} else {
    Write-Host "✗ MSVC not found at $msvcPath" -ForegroundColor Red
    $failed++
}

# Test Rust target
Write-Host "`nChecking Rust targets..." -ForegroundColor Yellow
$targets = rustup target list
if ($targets -match "x86_64-pc-windows-msvc \(installed\)") {
    Write-Host "✓ Windows MSVC target installed" -ForegroundColor Green
    $passed++
} else {
    Write-Host "✗ Windows MSVC target not installed" -ForegroundColor Red
    $failed++
}

# Test RustDesk repository
Write-Host "`nChecking RustDesk repository..." -ForegroundColor Yellow
if (Test-Path "$RustDeskPath\.git") {
    Write-Host "✓ RustDesk repository found at $RustDeskPath" -ForegroundColor Green
    $passed++
} else {
    Write-Host "✗ RustDesk repository not found" -ForegroundColor Red
    $failed++
}

# Summary
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })

if ($failed -eq 0) {
    Write-Host "`n✓ All checks passed! Environment ready for development." -ForegroundColor Green
} else {
    Write-Host "`n✗ Some checks failed. See troubleshooting guide." -ForegroundColor Red
}
```

Run verification:
```powershell
.\verify-setup.ps1 -RustDeskPath "C:\dev\rustdesk"
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. "rustup: command not found"
**Cause**: Rust not installed or PATH not updated

**Solution**:
```powershell
# Restart PowerShell to reload PATH
exit
# Open new PowerShell window

# If still fails, manually add to PATH
$rustPath = "$env:USERPROFILE\.cargo\bin"
$currentPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if ($currentPath -notlike "*$rustPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$rustPath", [EnvironmentVariableTarget]::User)
}
```

#### 2. "cl.exe: command not found"
**Cause**: MSVC not installed or environment not set

**Solution**:
```powershell
# Run Visual Studio environment setup
& 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'

# Add to PowerShell profile to auto-load
$profile_path = $PROFILE.CurrentUserAllHosts
if (-not (Test-Path $profile_path)) {
    New-Item -Path $profile_path -Type File -Force | Out-Null
}
Add-Content -Path $profile_path -Value @'
# Load Visual Studio environment
& 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat' | Out-Null
'@
```

#### 3. "cmake: command not found"
**Cause**: CMake not in PATH

**Solution**:
```powershell
# Check if CMake installed
Get-ChildItem -Path "C:\Program Files\CMake\bin" -ErrorAction SilentlyContinue

# If not found, reinstall or add manual PATH
$cmakePath = "C:\Program Files\CMake\bin"  # Adjust path as needed
$currentPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
[Environment]::SetEnvironmentVariable("Path", "$currentPath;$cmakePath", [EnvironmentVariableTarget]::User)

# Restart PowerShell
exit
```

#### 4. "NASM not found"
**Cause**: NASM installation error or PATH issue

**Solution**:
```powershell
# Verify NASM installed
Get-ChildItem -Path "C:\Program Files\NASM\" -ErrorAction SilentlyContinue

# If exists, add to PATH
$nasmPath = "C:\Program Files\NASM"
$currentPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if ($currentPath -notlike "*NASM*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$nasmPath", [EnvironmentVariableTarget]::User)
}

# Restart PowerShell
```

#### 5. Cargo Build Fails with "Linker `link.exe` not found"
**Cause**: Visual Studio C++ tools not properly configured

**Solution**:
```powershell
# Reinstall/reconfigure toolchain
rustup self uninstall
# Re-download and install from rustup.rs

# Or, manually set linker
$env:CC = "cl.exe"
$env:LINK = "link.exe"

# Add to PowerShell profile permanently
Add-Content -Path $PROFILE.CurrentUserAllHosts -Value @'
$env:CC = "cl.exe"
$env:LINK = "link.exe"
'@
```

#### 6. "PowerShell execution policy prevents script running"
**Cause**: Execution policy too restrictive

**Solution**:
```powershell
# Check current policy
Get-ExecutionPolicy

# Change to RemoteSigned (recommended for development)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# If that fails, try Bypass (less secure)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser
```

#### 7. Antivirus Blocking Build Tools
**Cause**: Real-time scanning slowing down or blocking compilation

**Solution**: Add development directories to antivirus exclusions:
- `C:\Users\<USERNAME>\.cargo\` (Cargo cache)
- `C:\Users\<USERNAME>\.rustup\` (Rust toolchain)
- `C:\dev\rustdesk\` (or your project directory)
- `C:\Program Files (x86)\Microsoft Visual Studio\` (Build tools)

**For Windows Defender:**
```powershell
# Administrator PowerShell
Add-MpPreference -ExclusionPath "C:\Users\$env:USERNAME\.cargo\"
Add-MpPreference -ExclusionPath "C:\Users\$env:USERNAME\.rustup\"
Add-MpPreference -ExclusionPath "C:\dev\rustdesk\"
```

#### 8. Git Line Endings Causing Issues
**Cause**: LF/CRLF mismatch on Windows

**Solution** (already configured, but verify):
```powershell
# Should already be set from Step 1
git config --global core.autocrlf

# Should return: true

# If not set:
git config --global core.autocrlf true
```

#### 9. Disk Space Running Out During Installation
**Cause**: Insufficient free space

**Solution**:
```powershell
# Check disk space
Get-Volume | Format-Table -AutoSize

# Clear temp files
Remove-Item -Path $env:TEMP\* -Force -Recurse -ErrorAction SilentlyContinue

# Clear NuGet cache
Remove-Item -Path "$env:APPDATA\.nuget\v3-cache\*" -Force -Recurse -ErrorAction SilentlyContinue

# Check Rust cache
Remove-Item -Path "$env:USERPROFILE\.cargo\registry\cache\*" -Force -Recurse -ErrorAction SilentlyContinue
```

#### 10. Build Machine Behind Corporate Proxy
**Cause**: Network access blocked by proxy

**Solution**:
```powershell
# Configure Git for proxy
git config --global http.proxy http://proxy.company.com:8080
git config --global https.proxy http://proxy.company.com:8080

# Configure Cargo for proxy
Write-Output @"
[net]
proxy = "http://proxy.company.com:8080"
"@ | Out-File -Append "$env:USERPROFILE\.cargo\config.toml"

# Configure npm/NuGet if needed
npm config set proxy http://proxy.company.com:8080
npm config set https-proxy http://proxy.company.com:8080
```

---

## Directory Structure

### Recommended Development Layout

```
C:\dev\
├── rustdesk\                          # Main RustDesk fork
│   ├── src\
│   │   ├── client.rs                 # Windows client code
│   │   ├── ui\                       # UI components
│   │   └── platform\windows\         # Windows-specific code
│   ├── Cargo.toml
│   ├── target\                       # Build output (ignored in git)
│   │   ├── debug\
│   │   ├── release\
│   │   └── x86_64-pc-windows-msvc\
│   └── build\
│       └── windows\                  # Windows build scripts
├── scratch\                           # Temporary experimental code
└── builds\                            # Archived builds for testing

C:\Users\<USERNAME>\.cargo\
├── bin\                               # Cargo-installed binaries
├── registry\                          # Downloaded crates
└── git\                               # Cloned git dependencies

C:\Users\<USERNAME>\.rustup\
├── toolchains\
│   └── stable-x86_64-pc-windows-msvc\
│       ├── bin\                       # rustc, cargo, etc.
│       ├── lib\
│       └── src\
└── settings.toml

C:\tools\
├── cmake\                             # CMake installation
│   └── bin\
├── nasm\                              # NASM installation
└── git\                               # Git installation (or Program Files)

C:\Program Files (x86)\
├── Microsoft Visual Studio\2022\
│   └── BuildTools\
│       ├── VC\                        # MSVC compiler
│       ├── MSBuild\                   # Build system
│       └── Common7\                   # Shared components
└── Windows Kits\                      # Windows SDK
    └── 10\
        ├── bin\
        ├── Include\
        └── Lib\
```

### Key Environment Variables

After installation, verify these are set:

```powershell
# Display important environment variables
Write-Host "PATH:" $env:Path
Write-Host "RUST_HOME:" $env:RUST_HOME
Write-Host "CARGO_HOME:" $env:CARGO_HOME
Write-Host "RUSTUP_HOME:" $env:RUSTUP_HOME
Write-Host "MSVC_HOME:" $env:VCINSTALLDIR
```

Expected values:
- `RUST_HOME`: `C:\Users\<USERNAME>\.rustup\toolchains\stable-x86_64-pc-windows-msvc`
- `CARGO_HOME`: `C:\Users\<USERNAME>\.cargo`
- `RUSTUP_HOME`: `C:\Users\<USERNAME>\.rustup`
- `VCINSTALLDIR`: `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\`

---

## Network Connectivity Verification

### Pre-Build Network Tests

Run these before attempting your first build:

#### 1. DNS Resolution
```powershell
Write-Host "DNS Resolution Test" -ForegroundColor Green

$sites = @(
    "github.com",
    "crates.io",
    "api.nuget.org",
    "registry.npmjs.org"
)

foreach ($site in $sites) {
    try {
        $ip = [System.Net.Dns]::GetHostAddresses($site)[0].IPAddressToString
        Write-Host "✓ $site -> $ip" -ForegroundColor Green
    } catch {
        Write-Host "✗ $site - DNS resolution failed" -ForegroundColor Red
    }
}
```

#### 2. HTTPS Connectivity
```powershell
Write-Host "HTTPS Connectivity Test" -ForegroundColor Green

$endpoints = @(
    "https://github.com",
    "https://crates.io",
    "https://api.nuget.org"
)

foreach ($endpoint in $endpoints) {
    try {
        $response = Invoke-WebRequest -Uri $endpoint -Method Head -TimeoutSec 5 -ErrorAction Stop
        Write-Host "✓ $endpoint - $(($response).StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "✗ $endpoint - Connection failed" -ForegroundColor Red
    }
}
```

#### 3. Git Clone Test
```powershell
Write-Host "Git Connectivity Test" -ForegroundColor Green

# Test with a small public repo
$testPath = "$env:TEMP\git-test"
git clone --depth 1 https://github.com/rust-lang/rust.git $testPath 2>&1 | ForEach-Object {
    Write-Host $_ -ForegroundColor Gray
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Git clone successful" -ForegroundColor Green
    Remove-Item -Path $testPath -Recurse -Force
} else {
    Write-Host "✗ Git clone failed" -ForegroundColor Red
}
```

#### 4. Cargo Registry Test
```powershell
Write-Host "Cargo Registry Access Test" -ForegroundColor Green

# Create temporary test project
$testDir = "$env:TEMP\cargo-test"
cargo new --path $testDir cargo-test-project 2>&1 | Out-Null

# Try to resolve dependencies (won't build, just checks registry)
cd $testDir
cargo check --offline 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Cargo registry accessible" -ForegroundColor Green
} else {
    Write-Host "⚠ Offline mode only - may need online check" -ForegroundColor Yellow
}

# Cleanup
cd $env:TEMP
Remove-Item -Path $testDir -Recurse -Force
```

---

## Quick Test Build

### Minimal Verification Build

This quick build verifies all tools work together without building the full RustDesk application.

#### 1. Create Test Project
```powershell
# Create test directory
$testDir = "C:\dev\rust-verify-build"
cargo new --path $testDir verify-build

# Navigate to project
cd $testDir
```

#### 2. Create Simple Test Program

Edit `src/main.rs`:
```rust
use std::env;
use std::path::Path;

fn main() {
    println!("=== Rust Build Verification ===");
    println!("Rust version: {}", env::var("CARGO").unwrap_or_default());
    println!("Target triple: {}", env::consts::ARCH);
    println!("OS: {}", env::consts::OS);
    
    let project_root = Path::new(env!("CARGO_MANIFEST_DIR"));
    println!("Project root: {}", project_root.display());
    
    println!("\n✓ All systems operational!");
    println!("Ready for Phase 2.1 development");
}
```

#### 3. Build and Run
```powershell
# Build debug version
cargo build

# Run
.\target\debug\verify-build.exe
# Expected: Should print OS info and success message

# Build release version
cargo build --release

# Run release
.\target\release\verify-build.exe
```

#### 4. Verify Build Artifacts
```powershell
# Check build output
ls -l .\target\debug\            # Debug build
ls -l .\target\release\          # Release build

# List all binaries
Get-ChildItem -Path .\target\debug\ -Filter "*.exe" -Recurse
Get-ChildItem -Path .\target\release\ -Filter "*.exe" -Recurse
```

### First RustDesk Build (Pre-compilation check)

Before attempting full RustDesk build:

```powershell
# Navigate to RustDesk directory
cd C:\dev\rustdesk

# Check dependencies only (no build)
cargo check --target x86_64-pc-windows-msvc

# This downloads and indexes all dependencies
# Takes 5-10 minutes first time

# If successful, you're ready for full build:
cargo build --release --target x86_64-pc-windows-msvc
```

---

## Next Steps

Once environment verification passes:

1. **Phase 2.1**: Proceed to Windows RustDesk client compilation and testing
2. **Debug Setup**: Configure IDE (VS Code, Visual Studio) with Rust debugging
3. **Build Optimization**: Configure release build settings for distribution
4. **CI/CD Pipeline**: Set up GitHub Actions for Windows builds (Phase 2.2)

For detailed next steps, see `docs/PHASE2_DESIGN.md` and `docs/PHASE2_WINDOWS_SETUP_QUICK.md`.

---

## Support Resources

| Resource | Link | Purpose |
|----------|------|---------|
| Rust Book | https://doc.rust-lang.org/ | Rust language reference |
| Cargo Guide | https://doc.rust-lang.org/cargo/ | Build system documentation |
| MSVC Documentation | https://docs.microsoft.com/en-us/cpp/ | C++ compiler reference |
| Windows SDK | https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/ | SDK documentation |
| RustDesk Repository | https://github.com/rustdesk/rustdesk | Main project repository |
| RustDesk Wiki | https://rustdesk.com/docs/en/ | Official documentation |

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-10  
**Status**: Phase 2 Preparation  
**Next Review**: Phase 2.1 Completion
