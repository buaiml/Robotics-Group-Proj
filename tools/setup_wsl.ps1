<#
.SYNOPSIS
  Create and provision the 'jethexa' WSL instance from scratch, on Windows.

.DESCRIPTION
  Does the whole job in one go:
    1. creates a new Ubuntu 22.04 WSL instance (leaving any existing distro alone)
    2. runs tools/provision_ubuntu2204.sh inside it
    3. restarts it so the default user takes effect
    4. verifies ROS 2 and Gazebo are actually there

  Takes 20-30 minutes and a few GB, most of it downloading packages.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\setup_wsl.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\setup_wsl.ps1 -Name jethexa2
#>
[CmdletBinding()]
param(
    # Name for the new WSL instance. Must not already exist.
    [string]$Name = "jethexa",

    # Delete and recreate the instance if it already exists. Destroys its contents.
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Info($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "  ! $msg" -ForegroundColor Yellow }
function Die($msg)  { Write-Host "FAILED: $msg" -ForegroundColor Red; exit 1 }

# --- locate the provisioning script next to this one ---
$repoRoot = Split-Path -Parent $PSScriptRoot
$provision = Join-Path $PSScriptRoot "provision_ubuntu2204.sh"
if (-not (Test-Path $provision)) { Die "cannot find $provision" }

# Translate Windows paths into the /mnt/... form WSL sees.
$provisionWsl = "/mnt/" + $provision.Substring(0,1).ToLower() + ($provision.Substring(2) -replace '\\','/')
$repoWsl      = "/mnt/" + $repoRoot.Substring(0,1).ToLower() + ($repoRoot.Substring(2) -replace '\\','/')

# --- check WSL itself ---
Info "checking WSL"
try { wsl.exe --status | Out-Null } catch { Die "WSL is not installed. Run 'wsl --install' first, reboot, then re-run this." }

# --distribution and --name need a reasonably recent WSL.
# wsl.exe writes UTF-16 here, which arrives with NULs between characters, so
# strip them before matching or every check silently fails.
$wslVersion = ((wsl.exe --version 2>$null) -join " ") -replace "`0",""
if ($wslVersion -notmatch "WSL version") {
    Warn "could not read the WSL version; if the install step fails, run 'wsl --update'"
}

# --- does it already exist? ---
# --list output is UTF-16 with NULs when piped, so strip them before matching.
$existing = (wsl.exe --list --quiet) -replace "`0","" -split "`r?`n" | Where-Object { $_.Trim() }
if ($existing -contains $Name) {
    if ($Force) {
        Warn "'$Name' exists; -Force given, unregistering it (this deletes its contents)"
        wsl.exe --unregister $Name
    } else {
        Die "a WSL instance named '$Name' already exists. Use -Name for a different one, or -Force to replace it."
    }
}

# --- 1. create ---
Info "creating Ubuntu 22.04 instance '$Name' (downloads ~600 MB)"
wsl.exe --install --distribution Ubuntu-22.04 --name $Name --no-launch
if ($LASTEXITCODE -ne 0) { Die "wsl --install failed. If it does not recognise --name, run 'wsl --update' and retry." }

# --- 2. provision ---
Info "provisioning: ROS 2 Humble, Gazebo Harmonic, Nav2, MuJoCo"
Info "this is the slow part - 20-30 minutes. Leave it running."
# Strip CRLF in case the script was checked out with Windows line endings, which
# would otherwise fail with 'bad interpreter'.
wsl.exe -d $Name -u root -- bash -c "tr -d '\r' < '$provisionWsl' > /tmp/provision.sh && bash /tmp/provision.sh"
if ($LASTEXITCODE -ne 0) { Die "provisioning failed. Re-run with the same -Name to retry; the script is safe to run twice." }

# --- 3. restart so /etc/wsl.conf default user applies ---
Info "restarting '$Name' so the default user takes effect"
wsl.exe --terminate $Name

# --- 4. verify ---
Info "verifying"
# Use printenv, not `echo "$VAR"`. PowerShell expands $VAR itself before
# wsl.exe sees the argument, so the echo form always comes back empty and this
# check reports a false failure on a perfectly good install.
$who  = (wsl.exe -d $Name -- bash -lc "whoami") -replace "`0","" -replace "`r|`n",""
$vers = ((wsl.exe -d $Name -- bash -lc "printenv ROS_DISTRO GZ_VERSION") -replace "`0","") -join " "
$gz   = (wsl.exe -d $Name -- bash -lc "gz sim --versions 2>/dev/null | head -1") -replace "`0","" -replace "`r|`n",""

Write-Host ""
Write-Host "  default user : $who"
Write-Host "  environment  : $vers"
Write-Host "  gazebo       : $gz"
Write-Host ""

$ok = $true
if ($who -notmatch "jethexa") { Warn "default user is '$who', expected jethexa - the restart may not have applied"; $ok = $false }
if ($vers -notmatch "humble")  { Warn "ROS_DISTRO is not set; check /etc/profile.d/jethexa.sh"; $ok = $false }
if ($vers -notmatch "harmonic"){ Warn "GZ_VERSION is not set; check /etc/profile.d/jethexa.sh"; $ok = $false }
if (-not $gz)                  { Warn "gz sim did not report a version"; $ok = $false }

if (-not $ok) { Die "the instance exists but is not fully set up. See the warnings above." }

Info "done"
Write-Host ""
Write-Host "Next, inside the instance:" -ForegroundColor Green
Write-Host "  wsl -d $Name"
Write-Host "  mkdir -p ~/jethexa_ws/src"
Write-Host "  cp -r '$repoWsl/jethexa_sim' ~/jethexa_ws/src/"
Write-Host "  cd ~/jethexa_ws && colcon build --symlink-install"
Write-Host ""
Write-Host "Then see docs/commands.md." -ForegroundColor Green
