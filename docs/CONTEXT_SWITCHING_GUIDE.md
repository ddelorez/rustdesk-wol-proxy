# Context Switching Guide: Phase 1 vs Phase 2 Development

**Quick Reference**: Determine which context you're working in and execute the correct commands.

**Last Updated**: 2026-02-10

---

## Quick Checklist: Am I Working on Phase 1 or Phase 2?

Ask yourself:

- **Phase 1**: "Am I working on the **Flask API** running on **Linux**?"
  - Answer YES → **Stay in WSL2** → Use Python/Flask tools
  
- **Phase 2**: "Am I working on the **RustDesk Rust client** running on **Windows**?"
  - Answer YES → **Switch to Windows native** → Use Rust/Cargo tools

---

## Context-Specific Instructions

### Phase 1: API Development (WSL2/Linux)

**When to Use Phase 1**:
- ✅ Developing `/wake` endpoint logic
- ✅ Adding API validation rules
- ✅ Improving logging/audit trails
- ✅ Writing unit tests for Flask app
- ✅ Modifying `app.py` or configuration
- ✅ Testing API locally via curl/Postman

**Development Environment Setup**:

```bash
# 1. Open WSL2 terminal (or use VS Code WSL remote)
wsl

# 2. Navigate to project
cd ~/rustdesk-wol-proxy
# or
cd /mnt/c/dev/rustdesk-wol-proxy

# 3. Activate Python virtual environment
source venv/bin/activate

# You should see: (venv) $ 

# 4. Set environment variables
export WOL_API_KEY="test_secure_key_1234567890"
export LOG_FILE="./dev.log"
```

**Core Commands**:

| Task | Command |
|------|---------|
| Start dev server | `python src/app.py` |
| Run all tests | `pytest tests/ -v` |
| Run specific test | `pytest tests/test_app.py::test_wake_success -v` |
| Test API endpoint | `curl "http://localhost:5001/wake?id=test&key=$WOL_API_KEY"` |
| View logs | `tail -f dev.log` |
| Git status | `git status` |
| Commit changes | `git add src/app.py && git commit -m "[phase1] message"` |
| Install dependencies | `pip install -r requirements.txt` |

**Port Configuration (Phase 1)**:

```
Local Development:  http://localhost:5001
Production Server:  http://10.10.10.145:5001
Health Endpoint:    /health
Wake Endpoint:      /wake?id=<ID>&key=<KEY>
```

**Example Working Session**:

```bash
# Start Phase 1 work
$ wsl
$ cd ~/rustdesk-wol-proxy
$ source venv/bin/activate
$ export WOL_API_KEY="test_1234567890_secure_key"

# Run tests
$ pytest tests/ -v
# ✓ All 33 tests pass

# Start dev server
$ python src/app.py
# * Running on http://127.0.0.1:5001

# In another WSL2 terminal, test the API
$ curl "http://localhost:5001/health"
# {"status": "healthy", "version": "1.0.0"}

# Make changes to src/app.py
$ vim src/app.py
# ... edit file ...

# Re-run tests
$ pytest tests/ -v

# Commit
$ git add src/app.py
$ git commit -m "[phase1] feat: improve error handling"

# Exit when done
$ exit  # exit Python venv (optional, but helps with context switch)
```

---

### Phase 2: Client Development (Windows/Rust)

**When to Use Phase 2**:
- ✅ Modifying RustDesk client code (Rust)
- ✅ Implementing offline detection logic
- ✅ Adding WOL API integration to client
- ✅ Building Windows `.exe` binary
- ✅ Writing Rust unit/integration tests
- ✅ Testing UI on Windows desktop

**Development Environment Setup**:

```powershell
# 1. Open PowerShell (native Windows)
# or open Windows Terminal

# 2. Navigate to RustDesk fork directory
cd C:\dev\rustdesk

# You should see files: Cargo.toml, Cargo.lock, src/, etc.

# 3. Verify Rust is available
rustc --version
# rustc 1.7x.x

cargo --version
# cargo 1.7x.x

# 4. Optional: Set environment (for faster builds)
$env:CARGO_BUILD_JOBS = "4"  # Adjust to your CPU cores
$env:RUST_BACKTRACE = "1"     # Better error messages
```

**Core Commands**:

| Task | Command |
|------|---------|
| Build (debug) | `cargo build --target x86_64-pc-windows-msvc` |
| Build (release) | `cargo build --release --target x86_64-pc-windows-msvc` |
| Run binary | `.\target\debug\rustdesk.exe` |
| Run tests | `cargo test --target x86_64-pc-windows-msvc` |
| Run specific test | `cargo test wol_api -- --nocapture` |
| Check compilation | `cargo check --target x86_64-pc-windows-msvc` |
| Format code | `cargo fmt` |
| Lint code | `cargo clippy` |
| Git status | `git status` |
| Commit changes | `git add src\client.rs && git commit -m "[phase2] message"` |

**Port/Endpoint Configuration (Phase 2)**:

```
Local Testing:      http://127.0.0.1:5001 (your PC running Phase 1 API)
RustDesk Signal:    Your configured hbbs server
WOL API Endpoint:   http://10.10.10.145:5001/wake
Retry Strategy:     30 seconds between attempts, up to 3 retries
```

**Example Working Session**:

```powershell
# Start Phase 2 work
PS> cd C:\dev\rustdesk

# Check that Phase 1 API is running (on your test machine)
PS> $response = Invoke-WebRequest "http://127.0.0.1:5001/health"
PS> $response.StatusCode
# 200 ✓

# Run tests
PS> cargo test --target x86_64-pc-windows-msvc
# test result: ok. XX passed; 0 failed

# Build debug binary
PS> cargo build --target x86_64-pc-windows-msvc
# Compiling rustdesk v1.x.x
# Finished debug ...

# Test binary
PS> .\target\debug\rustdesk.exe --version
# RustDesk 1.x.x

# Make changes to Rust code
PS> code src\client.rs
# ... edit file ...

# Check syntax
PS> cargo check --target x86_64-pc-windows-msvc

# Format code
PS> cargo fmt

# Commit
PS> git add src/client.rs
PS> git commit -m "[phase2] feat: improve offline detection"

# Build release version for distribution
PS> cargo build --release --target x86_64-pc-windows-msvc
# Compiling rustdesk v1.x.x
# Finished release ...

# Binary ready at: .\target\release\rustdesk.exe
```

---

## Port and Endpoint Configuration for Each Context

### Phase 1 API Endpoints

**Development (WSL2)**:
```
Base URL: http://localhost:5001

/health
  GET - Health check
  Response: {"status": "healthy", "version": "1.0.0"}

/wake
  GET /wake?id=<DEVICE_ID>&key=<API_KEY>
  Response: {"status": "success", "message": "...", "timestamp": "..."}
```

**Production (Linux Server)**:
```
Base URL: http://10.10.10.145:5001
# (or HTTPS via reverse proxy: https://rustdesk-wol.internal.net/)

Same endpoints as above, but served from production server
```

### Phase 2 Client Configuration

**WOL API URL** (stored in Phase 2 client config):
```
For development:   http://127.0.0.1:5001
For production:    http://10.10.10.145:5001
For HTTPS:         https://rustdesk-wol.internal.net/wake
```

**Retry Strategy**:
```
Initial attempt:   Immediate
Retry 1:          +30 seconds
Retry 2:          +30 seconds  (total 60 seconds)
Retry 3:          +30 seconds  (total 90 seconds)
Give up:          After 90 seconds total
```

---

## How to Test Phase 1→Phase 2 Communication Across Contexts

### Setup: Prerequisites

Ensure both contexts are available:

1. **Phase 1 API Running**:
   ```bash
   # In WSL2
   $ source venv/bin/activate
   $ export WOL_API_KEY="test_key_1234567890_secure"
   $ python src/app.py
   # API running at http://localhost:5001
   ```

2. **Windows can access WSL2**:
   ```powershell
   # In PowerShell (Windows)
   PS> Test-NetConnection -ComputerName localhost -Port 5001
   # TcpTestSucceeded : True ✓
   ```

### Test Scenario 1: Windows to WSL2 API (Local Network)

**Phase 2 Client Tests Phase 1 API**:

```powershell
# PowerShell on Windows
PS> $api_url = "http://localhost:5001/wake"
PS> $device_id = "test_device_001"
PS> $api_key = "test_key_1234567890_secure"

# Test health endpoint
PS> $health = Invoke-WebRequest -Uri "http://localhost:5001/health"
PS> $health.Content | ConvertFrom-Json | Format-Table
# status     version timestamp
# ------     ------- ---------
# healthy    1.0.0   2026-02-10T21:07:46.182Z

# Test wake endpoint
PS> $params = @{
>>   id = $device_id
>>   key = $api_key
>> }
PS> $response = Invoke-WebRequest -Uri $api_url -Body $params
PS> $response.Content | ConvertFrom-Json | Format-Table
# status  message                                 id              timestamp
# ------  -------                                 --              ---------
# success Wake-on-LAN packet sent to AA:BB:... test_device_001  2026-02-10T21:07:47.123Z
```

### Test Scenario 2: Remote Access (Phase 2 from different machine)

**If testing from actual Windows machine to Linux server**:

```powershell
# PowerShell on Windows machine
PS> $api_url = "http://10.10.10.145:5001/wake"
PS> $device_id = "desk_001"
PS> $api_key = $env:WOL_API_KEY  # from environment

# Verify network access
PS> Test-NetConnection -ComputerName 10.10.10.145 -Port 5001
# TcpTestSucceeded : True ✓

# Test API
PS> $response = Invoke-WebRequest -Uri "$api_url?id=$device_id&key=$api_key"
PS> $response.Content
```

### Test Scenario 3: Rust Code Calling Phase 1 API

**Phase 2 Rust code tests Phase 1 API**:

```rust
// In Phase 2 Rust code (src/client.rs or similar)

#[tokio::test]
async fn test_wol_api_integration() {
    let api_url = "http://127.0.0.1:5001/wake";
    let device_id = "test_device";
    let api_key = "test_key_1234567890_secure";
    
    let url = format!(
        "{}?id={}&key={}",
        api_url, device_id, api_key
    );
    
    let response = reqwest::Client::new()
        .get(&url)
        .send()
        .await
        .expect("Failed to call WOL API");
    
    assert_eq!(response.status(), 200);
    
    let body: serde_json::Value = response.json()
        .await
        .expect("Failed to parse response");
    
    assert_eq!(body["status"].as_str(), Some("success"));
    println!("✓ WOL API integration test passed");
}
```

Run test:
```powershell
PS> cargo test test_wol_api_integration -- --nocapture
```

---

## Repository Clone Locations for Each Context

### Phase 1 Repository (API)

**Location Options**:

```bash
# Option A: WSL2 home directory
~/rustdesk-wol-proxy/

# Option B: Windows mounted in WSL2
/mnt/c/dev/rustdesk-wol-proxy/

# How to clone (in WSL2):
cd ~
git clone https://github.com/your-fork/rustdesk-wol-proxy.git
cd rustdesk-wol-proxy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Phase 2 Repository (Client)

**Location** (Windows native):

```powershell
# Standard location
C:\dev\rustdesk\

# How to clone (in PowerShell):
cd C:\dev
git clone https://github.com/your-fork/rustdesk.git
cd rustdesk
git checkout phase2-wol-integration  # or your branch
cargo build --release
```

### Keep Clones Separate

**Goal**: Prevent accidentally mixing Phase 1 and Phase 2 code

**Do NOT**:
```
❌ C:\dev\rustdesk-wol-proxy\
    ├── src/app.py (Phase 1)
    ├── fork/rustdesk/  (Phase 2 inside Phase 1 — bad!)
    └── ...
```

**Do**:
```
✓ C:\dev\
   ├── rustdesk-wol-proxy\  (Phase 1 clone)
   │   └── src/app.py
   └── rustdesk\            (Phase 2 clone)
       └── src/client.rs
```

---

## Which Terminal/Environment to Use for Each Task

### Phase 1: Task → Terminal Mapping

| Task | Terminal | Command |
|------|----------|---------|
| Start API dev | WSL2 Bash | `python src/app.py` |
| Run tests | WSL2 Bash | `pytest tests/ -v` |
| Deploy to prod | WSL2 Bash (SSH) | `ssh 10.10.10.145 ...` |
| Edit code | VS Code (WSL2 remote) | `code src/app.py` |
| View logs | WSL2 Bash | `tail -f dev.log` |
| Git operations | WSL2 Bash | `git push origin main` |

### Phase 2: Task → Terminal Mapping

| Task | Terminal | Command |
|------|----------|---------|
| Build binary | PowerShell (Windows) | `cargo build --release` |
| Run tests | PowerShell (Windows) | `cargo test` |
| Run binary | PowerShell (Windows) | `.\target\release\rustdesk.exe` |
| Edit code | VS Code (native) | `code src\client.rs` |
| Format code | PowerShell (Windows) | `cargo fmt` |
| Git operations | PowerShell (Windows) | `git push origin phase2-*` |
| Sign binary | PowerShell (Admin) | `signtool sign ...` |

---

## Quick Decision Tree

```
┌─ What are you working on?
│
├─ Flask API, endpoint logic, tests
│  └─ → USE PHASE 1 (WSL2 Bash)
│     $ cd ~/rustdesk-wol-proxy
│     $ source venv/bin/activate
│     $ python src/app.py
│
├─ RustDesk client modifications, UI, Rust code
│  └─ → USE PHASE 2 (Windows PowerShell)
│     PS> cd C:\dev\rustdesk
│     PS> cargo build --release
│
├─ Documentation, shared files
│  └─ → USE EITHER (git from WSL2 OR PowerShell)
│     Both commit to docs/
│
└─ Cross-context testing (API + Client)
   └─ → START PHASE 1 API
       → THEN TEST FROM PHASE 2 CLIENT
       → Verify both work together
```

---

## Common Context Switches During a Workday

### Morning: Start Phase 1 Work

```bash
$ wsl                              # Enter WSL2
$ cd ~/rustdesk-wol-proxy
$ source venv/bin/activate
$ export WOL_API_KEY="..."
$ pytest tests/ -v                 # Run tests
# ✓ All tests pass

# Work on API code...
$ vim src/app.py
$ python src/app.py                # Test locally
$ curl "http://localhost:5001/..."

# Commit work
$ git add src/app.py
$ git commit -m "[phase1] feat: ..."
```

### Midday: Switch to Phase 2 Verification

```bash
# From WSL2 → Exit to PowerShell
$ exit                             # Leave WSL2 terminal

# PowerShell (Windows)
PS> cd C:\dev\rustdesk

# Verify Phase 1 API is accessible
PS> $response = Invoke-WebRequest http://localhost:5001/health
PS> $response.StatusCode            # Should be 200

# Test Phase 2 client calling Phase 1 API
PS> cargo test test_wol_api_integration -- --nocapture
# ✓ Tests pass

# Build Phase 2
PS> cargo build --release
```

### Afternoon: Return to Phase 1

```powershell
# From PowerShell → Enter WSL2
PS> wsl                             # Back to WSL2

# Continue Phase 1 work
$ source venv/bin/activate
$ cd ~/rustdesk-wol-proxy

# Resume development...
```

---

## Troubleshooting Context Switching Issues

### Problem: "Command not found" after switching context

**Cause**: Wrong terminal/environment

**Solution**:
- Phase 1 commands in PowerShell? → Run in WSL2 instead
- Phase 2 commands in WSL2? → Run in Windows PowerShell instead

```bash
# ❌ WRONG (Phase 1 command in WSL2 but venv not activated)
$ python src/app.py
# command not found: app.py

# ✓ RIGHT
$ source venv/bin/activate
$ python src/app.py
```

### Problem: Port 5001 already in use

**Cause**: Phase 1 API still running from previous session

**Solution**:
```bash
# Find process using port 5001
$ lsof -i :5001
# or
$ netstat -tlnp | grep 5001

# Kill it
$ kill <PID>

# Or restart API server
$ python src/app.py  # Starts on 5001
```

### Problem: Git conflicts between Phase 1 and Phase 2

**Cause**: Merging branches incorrectly

**Solution**:
```bash
# Keep branches separate
$ git branch -a
# * main                  (Phase 1 main branch)
#   develop
#   phase2-wol-integration (Phase 2 branch - separate!)

# Only merge Phase 1 → Phase 1
# Only merge Phase 2 → Phase 2

# For shared docs, merge from main → phase2-* only after review
$ git checkout main
$ git pull
$ git checkout phase2-*
$ git merge main --no-ff -m "Merge updated docs from Phase 1"
```

---

## Cheat Sheet: Context Commands

### Phase 1 (WSL2) One-Liners

```bash
# Start everything
$ wsl && cd ~/rustdesk-wol-proxy && source venv/bin/activate && export WOL_API_KEY="test_1234567890_secure" && python src/app.py

# Run all tests and exit
$ wsl && cd ~/rustdesk-wol-proxy && source venv/bin/activate && pytest tests/ -v && exit

# Push Phase 1 changes
$ wsl && cd ~/rustdesk-wol-proxy && git push origin main && exit

# SSH to production and restart service
$ wsl && ssh 10.10.10.145 "sudo systemctl restart rustdesk-wol && sudo systemctl status rustdesk-wol"
```

### Phase 2 (Windows) One-Liners

```powershell
# Start everything
PS> cd C:\dev\rustdesk; cargo build --release ; .\target\release\rustdesk.exe

# Run all tests and report
PS> cd C:\dev\rustdesk; cargo test -- --nocapture; Write-Host "Tests complete"

# Push Phase 2 changes
PS> cd C:\dev\rustdesk; git push origin phase2-wol-integration

# Build release binary signed and ready for distribution
PS> cd C:\dev\rustdesk; cargo build --release; signtool sign /f cert.pfx .\target\release\rustdesk.exe
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-10  
**Quick Reference For**: Switching between Phase 1 and Phase 2 development  
**Next Review**: During first multi-phase development sprint
