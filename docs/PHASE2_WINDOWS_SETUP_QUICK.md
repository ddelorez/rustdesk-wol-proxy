# Phase 2: Windows Setup Quick Reference

**For experienced developers. Complete setup in 1 hour (excluding auto-installs).**

---

## Prerequisites Checklist

- [ ] Windows 10 Build 19041+ or Windows 11
- [ ] Administrator access
- [ ] 200GB free disk space
- [ ] Internet connection with GitHub/NuGet access
- [ ] PowerShell 5.1+ (run `$PSVersionTable.PSVersion`)

---

## Install Order (90 minutes)

| Step | Tool | Time | Manual? | Command |
|------|------|------|---------|---------|
| 1 | Git | 5m | Yes | Download from [git-scm.com](https://git-scm.com/download/win) |
| 2 | Visual C++ Build Tools | 20m | **Yes** | Download [VS 2022 Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) - Select "Desktop development with C++" |
| 3 | Windows SDK | 10m | Optional | Included with Build Tools (step 2) |
| 4 | CMake | 2m | No | `.\scripts\windows-setup.ps1` (or manual from [cmake.org](https://cmake.org/download/)) |
| 5 | NASM | 2m | No | `.\scripts\windows-setup.ps1` (or `choco install nasm`) |
| 6 | Rust | 10m | No | `.\scripts\windows-setup.ps1` (or [rustup.rs](https://rustup.rs/)) |
| 7 | RustDesk Clone | 5m | No | `git clone https://github.com/<your-fork>/rustdesk.git` |

**Automated script covers steps 4, 5, 6**: See [windows-setup.ps1](#automation-script)

---

## Quick Setup Path

### Prerequisites
```powershell
# Edit execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Verify Windows version
[System.Environment]::OSVersion.Version
```

### Manual Installs (Must do these first!)
1. **Git**: Download and run installer from [git-scm.com](https://git-scm.com/download/win)
2. **Visual C++ Build Tools**: Download from [visualstudio.microsoft.com](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - Select workload: **"Desktop development with C++"**
   - Allow 20-30 minutes

### Automated Setup
```powershell
# Run automation script (from this repository)
cd C:\dev\rustdesk-wol-proxy
.\scripts\windows-setup.ps1

# Script will install:
# - CMake
# - NASM
# - Rust (stable + x86_64-pc-windows-msvc target)
```

### Configuration
```powershell
# Configure Git
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global core.autocrlf true

# Clone RustDesk
cd C:\dev
git clone https://github.com/<your-fork>/rustdesk.git
cd rustdesk
```

---

## Verification (5 minutes)

```powershell
# Quick verification script
function Verify-Setup {
    $checks = @{
        "Git" = { git --version }
        "Rust" = { rustc --version }
        "Cargo" = { cargo --version }
        "CMake" = { cmake --version }
        "NASM" = { nasm -version }
    }
    
    $passed = 0
    foreach ($tool in $checks.Keys) {
        try {
            $null = & $checks[$tool] 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ $tool" -ForegroundColor Green
                $passed++
            }
        } catch {
            Write-Host "✗ $tool" -ForegroundColor Red
        }
    }
    
    # Check MSVC
    if (Test-Path "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\bin\Hostx64\x64\cl.exe") {
        Write-Host "✓ MSVC compiler" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "✗ MSVC compiler" -ForegroundColor Red
    }
    
    # Check Rust target
    if ((rustup target list) -match "x86_64-pc-windows-msvc.*installed") {
        Write-Host "✓ Rust MSVC target" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "✗ Rust MSVC target" -ForegroundColor Red
    }
    
    Write-Host "`nResults: $passed/7 passed" -ForegroundColor $(if ($passed -eq 7) { "Green" } else { "Yellow" })
}

Verify-Setup
```

---

## Troubleshooting Quick Fixes

| Issue | Solution |
|-------|----------|
| "Git not found" | Restart PowerShell or restart machine |
| "Rust not found" | Add `$env:USERPROFILE\.cargo\bin` to PATH, restart |
| "MSVC not found" | Reinstall Build Tools, ensure "Desktop development with C++" workload selected |
| "CMake not found" | Restart PowerShell or run `windows-setup.ps1` again |
| NASM errors | Run: `nasm -version`, if not found: `choco install nasm` |
| Antivirus blocking build | Add to exclusions: `C:\Users\<USERNAME>\.cargo\`, `C:\dev\rustdesk\` |
| Build fails with linker error | Run: `& 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'` |

---

## Automation Script

### Usage
```powershell
# Run from project root
.\scripts\windows-setup.ps1

# Or specify custom paths
.\scripts\windows-setup.ps1 -ToolsPath "C:\development-tools" -RustDeskPath "C:\my-dev\rustdesk"
```

### What It Does
- ✓ Downloads and installs CMake
- ✓ Downloads and installs NASM
- ✓ Installs Rust via rustup
- ✓ Adds x86_64-pc-windows-msvc target
- ✓ Updates PowerShell PATH
- ✓ Validates each installation
- ✓ Provides rollback instructions if needed

### What It Doesn't Do (manual required)
- ✗ Git (use installer from git-scm.com)
- ✗ Visual C++ Build Tools (too large, ~8GB)
- ✗ Windows SDK (typically included with Build Tools)

---

## Test Build

```powershell
# Create test project
cargo new C:\dev\test-build
cd C:\dev\test-build

# Build and run
cargo build
.\target\debug\test_build.exe

# If successful, ready for RustDesk!
cd C:\dev\rustdesk
cargo check --target x86_64-pc-windows-msvc
```

---

## Key Directories

```
C:\dev\rustdesk\                        # Your fork
C:\Users\<USERNAME>\.cargo\             # Cargo cache
C:\Users\<USERNAME>\.rustup\            # Rust installation
C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\  # MSVC
C:\tools\cmake\                         # CMake (if installed via script)
```

---

## Essential Commands Reference

```powershell
# Rust/Cargo
rustc --version
cargo new <project>
cargo build
cargo build --release
cargo check --target x86_64-pc-windows-msvc

# Git
git clone <url>
git status
git pull
git checkout <branch>

# Verification
rustup show
rustup target list

# Environment
$env:Path                    # Check PATH
[System.Environment]::GetEnvironmentVariable("Path", "User")
```

---

## Next Steps

1. **Complete automated script**: Run `.\scripts\windows-setup.ps1`
2. **Verify setup**: Run verification script above
3. **Clone RustDesk**: `git clone https://github.com/<your-fork>/rustdesk.git`
4. **Test build**: `cargo build --release --target x86_64-pc-windows-msvc`
5. **Begin Phase 2.1**: See `docs/PHASE2_DESIGN.md`

---

## Need Help?

- **Detailed Guide**: See `docs/PHASE2_WINDOWS_SETUP.md`
- **Rust Documentation**: https://doc.rust-lang.org/
- **Troubleshooting**: Section 5 of detailed guide
- **RustDesk Docs**: https://rustdesk.com/docs/en/

---

**Version**: 1.0 | **Updated**: 2026-02-10 | **Setup Time**: ~90 minutes
