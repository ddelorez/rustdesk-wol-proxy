<#
.SYNOPSIS
Windows development environment automation script for Phase 2 Rust Windows client development

.DESCRIPTION
Automates installation of:
- CMake
- NASM (Netwide Assembler)
- Rust toolchain with x86_64-pc-windows-msvc target

Does NOT install (manual required):
- Git (use installer from git-scm.com)
- Visual C++ Build Tools 2022 (requires manual selection of workloads)
- Windows SDK (typically included with Build Tools)

.PARAMETER ToolsPath
Installation directory for CMake and NASM. Default: C:\tools

.PARAMETER RustDeskPath
Expected RustDesk repository path (for post-installation message). Default: C:\dev\rustdesk

.PARAMETER SkipVerification
Skip post-installation verification. Default: $false

.EXAMPLE
.\windows-setup.ps1
# Installs with defaults to C:\tools and expects RustDesk at C:\dev\rustdesk

.EXAMPLE
.\windows-setup.ps1 -ToolsPath "C:\development-tools" -RustDeskPath "C:\my-projects\rustdesk"
# Installs to custom directories

.NOTES
Requires: Administrator privileges
Platform: Windows 10 (Build 19041+) or Windows 11
PowerShell: 5.1 or higher
#>

param(
    [string]$ToolsPath = "C:\tools",
    [string]$RustDeskPath = "C:\dev\rustdesk",
    [switch]$SkipVerification = $false
)

# ============================================================================
# Configuration
# ============================================================================

$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

# Versions to install
$CMAKE_VERSION = "3.27.4"
$CMAKE_URL = "https://github.com/Kitware/CMake/releases/download/v$CMAKE_VERSION/cmake-$CMAKE_VERSION-windows-x86_64.zip"
$CMAKE_DEST = "$ToolsPath\cmake"

$NASM_VERSION = "2.16.01"
$NASM_URL = "https://www.nasm.us/pub/nasm/releasebuilds/$NASM_VERSION/win64/nasm-$NASM_VERSION-installer-x64.exe"
$NASM_DEST = "$ToolsPath\nasm"

# Rust
$RUST_TOOLCHAIN = "stable"
$RUST_TARGET = "x86_64-pc-windows-msvc"

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Header {
    param([string]$Title)
    Write-Host "`n" -NoNewline
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "=" * 70 -ForegroundColor Cyan
}

function Write-Status {
    param([string]$Message, [string]$Status = "INFO")
    $statusColor = @{
        "SUCCESS" = "Green"
        "ERROR" = "Red"
        "WARNING" = "Yellow"
        "INFO" = "Cyan"
    }
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] " -NoNewline -ForegroundColor Gray
    Write-Host "$Status" -NoNewline -ForegroundColor $statusColor[$Status]
    Write-Host " - $Message"
}

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-PathInEnvironment {
    param([string]$PathToAdd)
    $currentPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
    return $currentPath -like "*$PathToAdd*"
}

function Add-ToUserPath {
    param([string]$PathToAdd)
    
    if (Test-PathInEnvironment -PathToAdd $PathToAdd) {
        Write-Status "Already in PATH: $PathToAdd" "INFO"
        return $true
    }
    
    try {
        $currentPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
        $newPath = "$currentPath;$PathToAdd"
        [Environment]::SetEnvironmentVariable("Path", $newPath, [EnvironmentVariableTarget]::User)
        Write-Status "Added to PATH: $PathToAdd" "SUCCESS"
        return $true
    } catch {
        Write-Status "Failed to add to PATH: $_" "ERROR"
        return $false
    }
}

function Download-File {
    param([string]$URL, [string]$Destination)
    
    if (Test-Path $Destination) {
        Write-Status "Already downloaded: $(Split-Path $Destination -Leaf)" "INFO"
        return $true
    }
    
    try {
        Write-Status "Downloading from $URL" "INFO"
        $dir = Split-Path $Destination
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        
        # Use TLS 1.2 for modern HTTPS
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        
        Invoke-WebRequest -Uri $URL -OutFile $Destination -UseBasicParsing
        Write-Status "Downloaded successfully" "SUCCESS"
        return $true
    } catch {
        Write-Status "Download failed: $_" "ERROR"
        return $false
    }
}

function Test-Command {
    param([string]$Command)
    $null = & $Command 2>$null
    return $LASTEXITCODE -eq 0
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

Write-Header "Pre-flight Environment Checks"

# Check admin privileges
if (-not (Test-Administrator)) {
    Write-Status "Administrator privileges required" "ERROR"
    Write-Host "Please run this script as Administrator (Right-click > Run as administrator)" -ForegroundColor Red
    exit 1
}
Write-Status "Administrator privileges confirmed" "SUCCESS"

# Check Windows version
Write-Status "Checking Windows version..." "INFO"
$osVersion = [System.Environment]::OSVersion.Version
if ($osVersion.Build -lt 19041) {
    Write-Status "Windows build $($osVersion.Build) is too old (need 19041+)" "ERROR"
    exit 1
}
Write-Status "Windows build $($osVersion.Build) - OK" "SUCCESS"

# Check Disk space
Write-Status "Checking disk space..." "INFO"
$systemDrive = [System.IO.DriveInfo]::GetDrives() | Where-Object {$_.Name -eq "$($ToolsPath[0]):\"}
if ($systemDrive.AvailableFreeSpace -lt 2GB) {
    Write-Status "Less than 2GB free space available - may cause issues" "WARNING"
} else {
    $freeGB = [math]::Round($systemDrive.AvailableFreeSpace / 1GB, 2)
    Write-Status "$freeGB GB free disk space available" "SUCCESS"
}

# Check PowerShell version
$psVersion = $PSVersionTable.PSVersion
if ($psVersion.Major -lt 5) {
    Write-Status "PowerShell 5.0+ required (current: $psVersion)" "ERROR"
    exit 1
}
Write-Status "PowerShell $psVersion - OK" "SUCCESS"

# ============================================================================
# Install CMake
# ============================================================================

Write-Header "Installing CMake"

Write-Status "Target: $CMAKE_DEST" "INFO"

if (Test-Path "$CMAKE_DEST\bin\cmake.exe") {
    Write-Status "CMake already installed at $CMAKE_DEST" "SUCCESS"
} else {
    # Download CMake
    $tempDir = "$env:TEMP\cmake-install"
    $zipFile = "$tempDir\cmake.zip"
    
    Write-Status "Creating directory: $tempDir" "INFO"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    
    if (Download-File -URL $CMAKE_URL -Destination $zipFile) {
        # Extract
        Write-Status "Extracting CMake..." "INFO"
        Expand-Archive -Path $zipFile -DestinationPath $tempDir -Force
        
        # Find extracted folder
        $extractedFolder = Get-ChildItem -Path $tempDir -Directory | Where-Object {$_.Name -match "cmake-"} | Select-Object -First 1
        
        if ($extractedFolder) {
            # Create tools directory
            if (-not (Test-Path $ToolsPath)) {
                New-Item -ItemType Directory -Path $ToolsPath -Force | Out-Null
                Write-Status "Created: $ToolsPath" "SUCCESS"
            }
            
            # Move CMake
            if (Test-Path $CMAKE_DEST) {
                Remove-Item -Path $CMAKE_DEST -Recurse -Force
            }
            Move-Item -Path $extractedFolder.FullName -Destination $CMAKE_DEST -Force
            Write-Status "CMake installed successfully" "SUCCESS"
            
            # Add to PATH
            Add-ToUserPath -PathToAdd "$CMAKE_DEST\bin"
        } else {
            Write-Status "Could not find extracted CMake folder" "ERROR"
        }
        
        # Cleanup
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        Write-Status "CMake installation skipped due to download failure" "WARNING"
    }
}

# ============================================================================
# Install NASM
# ============================================================================

Write-Header "Installing NASM"

Write-Status "Target: $NASM_DEST" "INFO"

if (Test-Path "$NASM_DEST\nasm.exe" -or (Test-Command "nasm.exe")) {
    if (Test-Command "nasm.exe") {
        Write-Status "NASM already installed and in PATH" "SUCCESS"
    } else {
        Write-Status "NASM already installed at $NASM_DEST" "SUCCESS"
    }
} else {
    $tempDir = "$env:TEMP\nasm-install"
    $exeFile = "$tempDir\nasm-installer.exe"
    
    Write-Status "Creating directory: $tempDir" "INFO"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    
    if (Download-File -URL $NASM_URL -Destination $exeFile) {
        Write-Status "Running NASM installer..." "INFO"
        Write-Status "Installation directory: $NASM_DEST" "INFO"
        
        try {
            $process = Start-Process -FilePath $exeFile `
                -ArgumentList "/D=$NASM_DEST /S" `
                -NoNewWindow `
                -Wait `
                -PassThru
            
            if ($process.ExitCode -eq 0 -and (Test-Path "$NASM_DEST\nasm.exe")) {
                Write-Status "NASM installed successfully" "SUCCESS"
                Add-ToUserPath -PathToAdd $NASM_DEST
            } else {
                Write-Status "NASM installer exited with code $($process.ExitCode)" "WARNING"
                Write-Status "Trying Chocolatey as fallback: choco install nasm" "INFO"
            }
        } catch {
            Write-Status "NASM installation failed: $_" "ERROR"
            Write-Host "Manual installation: Download from https://www.nasm.us/" -ForegroundColor Yellow
        }
        
        # Cleanup
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        Write-Status "NASM installation skipped due to download failure" "WARNING"
    }
}

# ============================================================================
# Install Rust
# ============================================================================

Write-Header "Installing Rust Toolchain"

if (Test-Command "rustc.exe") {
    Write-Status "Rust already installed" "SUCCESS"
    rustc --version | ForEach-Object { Write-Status $_ "INFO" }
} else {
    Write-Status "Downloading rustup installer..." "INFO"
    $rustupExe = "$env:TEMP\rustup-init.exe"
    
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri "https://win.rustup.rs/x86_64" -OutFile $rustupExe -UseBasicParsing
        
        Write-Status "Running rustup installer..." "INFO"
        $process = Start-Process -FilePath $rustupExe `
            -ArgumentList "-y" `
            -NoNewWindow `
            -Wait `
            -PassThru
        
        if ($process.ExitCode -eq 0) {
            Write-Status "Rust installed successfully" "SUCCESS"
            
            # Reload PATH in current session
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
            
            # Show version
            Start-Sleep -Seconds 1
            rustc --version | ForEach-Object { Write-Status $_ "INFO" }
        } else {
            Write-Status "rustup installer exited with code $($process.ExitCode)" "ERROR"
        }
        
        Remove-Item -Path $rustupExe -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Status "Rust installation failed: $_" "ERROR"
        Write-Host "Manual installation: Visit https://rustup.rs/" -ForegroundColor Yellow
    }
}

# ============================================================================
# Install Rust MSVC Target
# ============================================================================

Write-Header "Installing Rust Windows MSVC Target"

Write-Status "Target: x86_64-pc-windows-msvc" "INFO"

# Reload PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

if (rustup target list | Select-String "x86_64-pc-windows-msvc.*installed") {
    Write-Status "Target already installed" "SUCCESS"
} else {
    Write-Status "Installing target with rustup..." "INFO"
    
    try {
        $output = rustup target add x86_64-pc-windows-msvc 2>&1
        $output | ForEach-Object { Write-Status $_ "INFO" }
        
        $targets = rustup target list
        if ($targets -match "x86_64-pc-windows-msvc.*installed") {
            Write-Status "Target installed successfully" "SUCCESS"
        } else {
            Write-Status "Target installation verification failed" "WARNING"
        }
    } catch {
        Write-Status "Failed to install target: $_" "ERROR"
    }
}

# ============================================================================
# Verify Installations
# ============================================================================

if (-not $SkipVerification) {
    Write-Header "Verification Tests"
    
    $allPassed = $true
    
    # Test Git
    Write-Status "Testing Git..." "INFO"
    if (Test-Command "git --version") {
        Write-Status "✓ Git verified" "SUCCESS"
    } else {
        Write-Status "✗ Git not found (must be installed manually)" "WARNING"
        $allPassed = $false
    }
    
    # Test CMake
    Write-Status "Testing CMake..." "INFO"
    if (Test-Command "cmake --version") {
        $version = cmake --version | Select-Object -First 1
        Write-Status "✓ $version" "SUCCESS"
    } else {
        Write-Status "✗ CMake not found" "WARNING"
        $allPassed = $false
    }
    
    # Test NASM
    Write-Status "Testing NASM..." "INFO"
    if (Test-Command "nasm -version") {
        $version = nasm -version | Select-Object -First 1
        Write-Status "✓ $version" "SUCCESS"
    } else {
        Write-Status "✗ NASM not found" "WARNING"
        $allPassed = $false
    }
    
    # Test Rust
    Write-Status "Testing Rust..." "INFO"
    if (Test-Command "rustc --version") {
        $version = rustc --version
        Write-Status "✓ $version" "SUCCESS"
    } else {
        Write-Status "✗ Rust not found" "WARNING"
        $allPassed = $false
    }
    
    # Test Cargo
    Write-Status "Testing Cargo..." "INFO"
    if (Test-Command "cargo --version") {
        $version = cargo --version
        Write-Status "✓ $version" "SUCCESS"
    } else {
        Write-Status "✗ Cargo not found" "WARNING"
        $allPassed = $false
    }
    
    # Test Rust target
    Write-Status "Testing Rust x86_64-pc-windows-msvc target..." "INFO"
    $targets = rustup target list
    if ($targets -match "x86_64-pc-windows-msvc.*installed") {
        Write-Status "✓ Target installed" "SUCCESS"
    } else {
        Write-Status "✗ Target not installed" "WARNING"
        $allPassed = $false
    }
    
    # Summary
    Write-Header "Verification Summary"
    if ($allPassed) {
        Write-Status "All automated tools verified successfully!" "SUCCESS"
    } else {
        Write-Status "Some tools missing or not fully verified - see above" "WARNING"
    }
}

# ============================================================================
# Installation Summary
# ============================================================================

Write-Header "Installation Complete"

Write-Host @"
Summary of what was installed:
  ✓ CMake          -> $CMAKE_DEST
  ✓ NASM           -> $NASM_DEST (or system PATH)
  ✓ Rust stable    -> ~/.rustup/
  ✓ MSVC target    -> x86_64-pc-windows-msvc

What you still need to do manually:
  1. Install Git from https://git-scm.com/download/win
  2. Install Visual C++ Build Tools 2022 from:
     https://visualstudio.microsoft.com/visual-cpp-build-tools/
     (Select "Desktop development with C++")

Next steps:
  1. Configure Git:
     git config --global user.name "Your Name"
     git config --global user.email "you@example.com"

  2. Clone RustDesk fork:
     git clone https://github.com/<your-fork>/rustdesk.git

  3. Run your first build:
     cd $RustDeskPath
     cargo build --release --target x86_64-pc-windows-msvc

  4. For detailed setup info, see:
     docs/PHASE2_WINDOWS_SETUP.md

Important Notes:
  - You may need to RESTART PowerShell for PATH changes to take effect
  - Visual C++ Build Tools are required for C/C++ compilation
  - Antivirus may slow down builds; add exclusions for:
    ~/.cargo/
    ~/.rustup/
    $(if ($RustDeskPath) { "$RustDeskPath" })

"@ -ForegroundColor Green

Write-Host "For troubleshooting, visit: docs/PHASE2_WINDOWS_SETUP.md`n" -ForegroundColor Cyan

# ============================================================================
# Completion
# ============================================================================

Write-Status "Setup script completed at $(Get-Date)" "SUCCESS"
Write-Host "`nReopen PowerShell to ensure PATH changes are loaded.`n" -ForegroundColor Yellow
