#!/usr/bin/env bash
# Provision Ubuntu 22.04 with ROS 2 Humble + Gazebo Harmonic for this project.
#
#   sudo bash tools/provision_ubuntu2204.sh
#
# Runs inside Ubuntu, wherever that Ubuntu lives: WSL, a Docker container, a VM,
# or bare metal. It detects which and adjusts - the only differences are whether
# it creates a login account and whether it writes /etc/wsl.conf.
#
# Takes ~20 minutes and a few GB. Installs ROS 2 Humble desktop, ros2_control,
# Nav2, slam_toolbox, Gazebo Harmonic, ros_gz for Harmonic, gz_ros2_control
# built from source (there is no Humble+Harmonic binary of it), MuJoCo and
# Gymnasium.
#
# Knobs, all optional:
#   JETHEXA_USER=name          login to create        (default: jethexa)
#   JETHEXA_PASSWORD_B64=...   its password, base64   (default: a single space)
#   JETHEXA_FORCE_PASSWORD=1   reset an existing user's password
#   JETHEXA_CREATE_USER=0|1    override the per-environment default
#   JETHEXA_CLEAN_APT=0|1      remove apt lists afterwards (default: 1 in Docker)
#   JETHEXA_ENV=docker|wsl|native   skip detection and say where this is running.
#                              The Dockerfile sets docker: detection cannot tell a
#                              `docker build` step apart from WSL.
# If this file has Windows (CRLF) line endings - opened in a Windows editor,
# copied through a Windows tool - bash would die on the next line with
# "set: pipefail\r: invalid option name". So first, re-run a cleaned copy of
# ourselves. The line ends in '#' on purpose: a stray \r then lands inside a
# comment, so this one line still parses even when the file is CRLF.
# A temp file, not exec bash <(...): the process-substitution pipe is empty
# by the time the new bash reads it, which silently runs nothing and exits 0.
if grep -q $'\r' "$0" 2>/dev/null; then _c="$(mktemp)"; tr -d '\r' < "$0" > "$_c"; JETHEXA_CLEANED_COPY="$_c" exec bash "$_c" "$@"; fi #

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
[ -n "${JETHEXA_CLEANED_COPY:-}" ] && rm -f "$JETHEXA_CLEANED_COPY"

step() { echo; echo "=== $* ==="; }

step "where am I running?"
IS_WSL=0
IS_DOCKER=0
grep -qi microsoft /proc/version 2>/dev/null && IS_WSL=1
if [ -f /.dockerenv ] || [ -f /run/.containerenv ] \
   || grep -qaE '(docker|containerd|kubepods)' /proc/1/cgroup 2>/dev/null; then
  IS_DOCKER=1
fi

# Detection is a guess, and it guesses wrong inside `docker build`: BuildKit
# build containers have no /.dockerenv, cgroup v2 hides the runtime, and Docker
# Desktop's kernel says "microsoft" - so a build step looks exactly like WSL.
# Anything that knows where it is running should say so. The Dockerfile does.
case "${JETHEXA_ENV:-}" in
  docker) IS_DOCKER=1 ;;
  wsl)    IS_DOCKER=0; IS_WSL=1 ;;
  native) IS_DOCKER=0; IS_WSL=0 ;;
  "")     ;;
  *)      echo "ERROR: JETHEXA_ENV must be docker, wsl or native (got '$JETHEXA_ENV')" >&2; exit 1 ;;
esac

# Docker wins the tie deliberately: Docker Desktop on Windows runs containers
# on a WSL2 kernel, so /proc/version says "microsoft" inside a container too.
# Checking WSL first would mislabel every Windows container as WSL.
if   [ "$IS_DOCKER" = 1 ] && [ "$IS_WSL" = 1 ]; then ENVIRONMENT="Docker container (on a WSL2 kernel)"
elif [ "$IS_DOCKER" = 1 ];                      then ENVIRONMENT="Docker container"
elif [ "$IS_WSL" = 1 ];                         then ENVIRONMENT="WSL"
else                                                 ENVIRONMENT="native Linux or VM"
fi
echo "environment: $ENVIRONMENT"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run this as root (use sudo)." >&2
  exit 1
fi

# A container normally runs as root and gets its user from the Dockerfile, so
# creating a login account there is usually pointless. Everywhere else we want
# one. Override either way with JETHEXA_CREATE_USER.
if [ "$IS_DOCKER" = 1 ]; then
  CREATE_USER="${JETHEXA_CREATE_USER:-0}"
  CLEAN_APT="${JETHEXA_CLEAN_APT:-1}"
else
  CREATE_USER="${JETHEXA_CREATE_USER:-1}"
  CLEAN_APT="${JETHEXA_CLEAN_APT:-0}"
fi
echo "create a login account: $CREATE_USER    clean apt lists afterwards: $CLEAN_APT"

step "checking the distro"
# ROS 2 Humble only has packages for Ubuntu 22.04 (jammy). On 24.04 the ROS apt
# source installs fine but carries Jazzy, so the installs below fail with
# confusing "package not found" errors half an hour in. Stop now instead.
DISTRO_CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME:-unknown}")"
DISTRO_PRETTY="$(. /etc/os-release && echo "${PRETTY_NAME:-unknown}")"
echo "found: $DISTRO_PRETTY (codename $DISTRO_CODENAME)"
if [ "$DISTRO_CODENAME" != "jammy" ]; then
  echo >&2
  echo "ERROR: this needs Ubuntu 22.04 (jammy); found $DISTRO_PRETTY." >&2
  echo "ROS 2 Humble has no packages for $DISTRO_CODENAME." >&2
  echo >&2
  if [ "$IS_DOCKER" = 1 ]; then
    echo "Your base image is not 22.04. Use 'FROM ubuntu:22.04'." >&2
  elif [ "$IS_WSL" = 1 ]; then
    echo "A WSL instance made with plain 'wsl --install -d Ubuntu' is 24.04 or" >&2
    echo "newer. Create a 22.04 one alongside it:" >&2
    echo "  wsl --install --distribution Ubuntu-22.04 --name jethexa --no-launch" >&2
  fi
  exit 1
fi

step "checking the CPU architecture"
# ros-humble-ros-gzharmonic (the Gazebo<->ROS bridge) is only published for
# amd64. Everything else here exists for arm64, so without this check an
# Apple Silicon Mac or a Raspberry Pi gets 15 minutes in and then fails with
# "Unable to locate package ros-humble-ros-gzharmonic".
ARCH="$(dpkg --print-architecture)"
echo "architecture: $ARCH"
if [ "$ARCH" != "amd64" ]; then
  echo >&2
  echo "ERROR: this environment needs amd64 (x86_64); found $ARCH." >&2
  echo "The Gazebo Harmonic <-> ROS 2 Humble bridge has no $ARCH package." >&2
  echo >&2
  if [ "$IS_DOCKER" = 1 ]; then
    echo "On an Apple Silicon Mac, build and run the amd64 image instead - Docker" >&2
    echo "Desktop emulates it. tools/docker_run.sh does this automatically, or:" >&2
    echo "  docker build --platform linux/amd64 -f tools/Dockerfile -t jethexa:humble ." >&2
  fi
  exit 1
fi

step "base packages"
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  ca-certificates curl gnupg lsb-release locales software-properties-common \
  git build-essential cmake python3-pip python3-dev sudo nano less

locale-gen en_US en_US.UTF-8 >/dev/null
update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

# Pick up any extra root CAs dropped into /usr/local/share/ca-certificates
# (the Dockerfile copies tools/extra-ca/ there). Needed behind TLS inspection.
update-ca-certificates >/dev/null 2>&1 || true

step "checking HTTPS works"
# Everything from here on downloads over HTTPS. If something on the host is
# intercepting TLS - an antivirus "web shield", a corporate proxy - every
# download fails with "unable to get local issuer certificate", and under
# `set -e` inside a pipeline that death is SILENT. It cost an afternoon once.
# So check up front, and say what is wrong in words.
# Only hosts this script actually uses over HTTPS. NOT packages.ros.org: apt
# reaches that over plain HTTP (packages are GPG-signed), and its HTTPS
# certificate is for *.osuosl.org, so checking it would fail on every machine.
for url in https://github.com/ https://packages.osrfoundation.org/ https://pypi.org/simple/; do
  if ! err="$(curl -sS -o /dev/null --max-time 20 "$url" 2>&1)"; then
    echo >&2
    echo "ERROR: cannot reach $url" >&2
    echo "  $err" >&2
    if printf '%s' "$err" | grep -qiE 'local issuer certificate|self.signed|certificate verify'; then
      cat >&2 <<'MSG'

Something between this machine and the internet is intercepting HTTPS and
re-signing certificates. It is usually an antivirus "web shield" (Norton,
Avast, Kaspersky, ...) or a university/corporate proxy. The host trusts that
product's root certificate; this Linux environment does not.

Fix: export that root certificate as PEM, put it in tools/extra-ca/ with a
.crt extension, and rebuild. tools/extra-ca/README.md has the exact commands.
Alternatively, have the antivirus stop scanning this traffic.
MSG
    fi
    exit 1
  fi
done
echo "HTTPS ok"

# pip ships its own certificate bundle and ignores the system one, so without
# this it would fail behind TLS inspection even after the fix above works for
# curl and git. The system bundle contains all the normal roots as well.
export PIP_CERT=/etc/ssl/certs/ca-certificates.crt
# Running pip as root is deliberate here (system-wide install for all users).
# Without this, pip prints a warning that it "may render your system unusable",
# which alarms students for no reason.
export PIP_ROOT_USER_ACTION=ignore

step "ros 2 apt source"
add-apt-repository -y universe >/dev/null
# Ask GitHub for the latest release, but do not depend on the answer: the API is
# rate-limited to 60 requests an hour per IP, and eight students provisioning
# from one campus network can plausibly hit that. Fall back to a pinned version.
ROS_APT_SOURCE_PINNED="1.3.0"
ROS_APT_SOURCE_VERSION="$(curl -sL --max-time 20 https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
  | grep -F '"tag_name"' | awk -F'"' '{print $4}' || true)"
if [ -z "$ROS_APT_SOURCE_VERSION" ]; then
  echo "could not ask GitHub for the latest ros-apt-source; using pinned $ROS_APT_SOURCE_PINNED"
  ROS_APT_SOURCE_VERSION="$ROS_APT_SOURCE_PINNED"
fi
echo "ros-apt-source ${ROS_APT_SOURCE_VERSION}"
CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"
curl -fsSL --max-time 60 -o /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${CODENAME}_all.deb"
apt-get install -y -qq /tmp/ros2-apt-source.deb

step "gazebo apt source"
curl -fsSL --max-time 60 https://packages.osrfoundation.org/gazebo.gpg \
  -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable ${CODENAME} main" \
  > /etc/apt/sources.list.d/gazebo-stable.list

apt-get update -qq

step "ros 2 humble desktop"
apt-get install -y ros-humble-desktop ros-dev-tools

step "ros2_control + navigation + tooling"
apt-get install -y \
  ros-humble-ros2-control ros-humble-ros2-controllers \
  ros-humble-xacro ros-humble-joint-state-publisher-gui \
  ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-slam-toolbox \
  python3-colcon-common-extensions python3-rosdep python3-vcstool

step "gazebo harmonic + ros_gz for harmonic"
apt-get install -y gz-harmonic
apt-get install -y ros-humble-ros-gzharmonic

step "rosdep init"
rosdep init 2>/dev/null || true
rosdep update --rosdistro humble >/dev/null 2>&1 || rosdep update >/dev/null 2>&1 || true

step "gz_ros2_control from source (no humble+harmonic binary exists)"
# Pinned to an exact commit, not the branch tip. Eight students installing over
# several weeks would otherwise each get whatever the humble branch held on
# their install day, and one upstream push mid-semester would give the class
# two different builds. This is the commit the project was verified against.
GZ_ROS2_CONTROL_REF="c88a5fd9170af120c263c1201f0744a40f93d673"   # humble branch, 2026-09-02
mkdir -p /opt/gz_ws/src/gz_ros2_control
cd /opt/gz_ws/src/gz_ros2_control
if [ ! -d .git ]; then
  git init -q
  git remote add origin https://github.com/ros-controls/gz_ros2_control.git
fi
# fetch-by-commit also moves an existing checkout onto the pin
git fetch -q --depth 1 origin "$GZ_ROS2_CONTROL_REF"
git checkout -q --detach FETCH_HEAD
echo "gz_ros2_control at $(git rev-parse --short HEAD)"
cd /opt/gz_ws
set +u
source /opt/ros/humble/setup.bash
set -u
export GZ_VERSION=harmonic
colcon build --merge-install --cmake-args -DCMAKE_BUILD_TYPE=Release

step "python: mujoco + gymnasium"
# numpy and matplotlib come from apt, NEVER pip. ROS 2 Humble's compiled Python
# packages (cv_bridge, point cloud tools) are built against Ubuntu's numpy 1.21.
# A pip-installed numpy 2 lands in /usr/local, shadows it, and breaks them -
# exactly the depth-camera work the perception students are doing.
apt-get install -y -qq python3-numpy python3-matplotlib
pip3 install --no-cache-dir -q --upgrade pip
# Exact versions, verified together with Ubuntu's numpy 1.21.5. Unpinned, a
# future mujoco that wants numpy 2 would make pip upgrade it anyway.
pip3 install --no-cache-dir -q "mujoco==3.13.0" "gymnasium==1.3.0"
python3 -c 'import numpy, mujoco, gymnasium; print("numpy", numpy.__version__, "| mujoco", mujoco.__version__, "| gymnasium", gymnasium.__version__)'
case "$(python3 -c 'import numpy; print(numpy.__version__)')" in
  1.*) ;;
  *) echo "ERROR: numpy was upgraded past 1.x; ROS 2 Humble's cv_bridge will break" >&2; exit 1 ;;
esac

step "user account"
# Who is this environment for? NOT always 'jethexa' - students keep their own
# usernames. Pick, in order:
#   1. JETHEXA_USER, when the caller names someone explicitly
#   2. SUDO_USER - whoever ran `sudo bash tools/provision_ubuntu2204.sh`,
#      which is how most students run this inside their own WSL
#   3. the existing UID-1000 user - the first account on a machine, e.g. the
#      login someone already set up in their WSL instance
#   4. 'jethexa', only for a completely fresh instance with no users at all
if [ -n "${JETHEXA_USER:-}" ]; then
  PROJECT_USER="$JETHEXA_USER";  USER_SOURCE="named explicitly"
elif [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
  PROJECT_USER="$SUDO_USER";     USER_SOURCE="the user who ran sudo"
elif FIRST_USER="$(getent passwd 1000 | cut -d: -f1)" && [ -n "$FIRST_USER" ]; then
  PROJECT_USER="$FIRST_USER";    USER_SOURCE="the existing first user (UID 1000)"
else
  PROJECT_USER="jethexa";        USER_SOURCE="default, no users exist yet"
fi

# Password only matters for an account this script creates. Base64 takes
# precedence because whitespace does not survive PowerShell as a plain value.
# The default for a new account is a single space, the project convention.
if [ -n "${JETHEXA_PASSWORD_B64:-}" ]; then
  PROJECT_PASSWORD="$(printf '%s' "$JETHEXA_PASSWORD_B64" | base64 -d)"
else
  PROJECT_PASSWORD="${JETHEXA_PASSWORD- }"
fi

if [ "$CREATE_USER" != "1" ]; then
  echo "skipped: containers run as root and get their user from the Dockerfile"
  echo "(set JETHEXA_CREATE_USER=1 if you want one anyway)"

elif id -u "$PROJECT_USER" >/dev/null 2>&1; then
  # Rule: never change an account this script did not create. Its password,
  # groups, sudo settings and WSL default login all stay exactly as they are.
  echo "using existing user '$PROJECT_USER' ($USER_SOURCE)"
  if [ "${JETHEXA_FORCE_PASSWORD:-0}" != "1" ]; then
    echo "its password, sudo settings and login are left untouched"
  else
    # printf, not echo, so a password of exactly " " is preserved verbatim.
    printf '%s:%s\n' "$PROJECT_USER" "$PROJECT_PASSWORD" | chpasswd
    echo "password overwritten, because JETHEXA_FORCE_PASSWORD=1"
  fi

else
  useradd -m -s /bin/bash -G sudo "$PROJECT_USER"
  printf '%s:%s\n' "$PROJECT_USER" "$PROJECT_PASSWORD" | chpasswd
  # Passwordless sudo, but only for the account we just made: its password is
  # an invisible space nobody wants to type at every apt-get.
  mkdir -p /etc/sudoers.d
  echo "$PROJECT_USER ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/$PROJECT_USER"
  chmod 0440 "/etc/sudoers.d/$PROJECT_USER"
  echo "created user '$PROJECT_USER' ($USER_SOURCE), passwordless sudo"

  # Make it the WSL login - only for an account we created. An existing
  # instance's default login is its owner's choice (often stored in the
  # registry, not here), so it is never rewritten.
  if [ "$IS_WSL" = 1 ] && [ "$IS_DOCKER" = 0 ]; then
    cat > /etc/wsl.conf <<EOF
[user]
default=$PROJECT_USER
EOF
    echo "wrote /etc/wsl.conf (default user $PROJECT_USER)"
  fi
fi

# Environment goes in /etc/profile.d, NOT ~/.bashrc. Ubuntu's .bashrc returns
# early for non-interactive shells, so anything put there is invisible to
#   wsl -d jethexa -- bash -lc "..."
# which is how scripts and CI will invoke this environment.
cat > /etc/profile.d/jethexa.sh <<'EOF'
# --- JetHexa project environment (ROS 2 Humble + Gazebo Harmonic) ---
export GZ_VERSION=harmonic
export ROS_DOMAIN_ID=42

[ -f /opt/ros/humble/setup.bash ] && . /opt/ros/humble/setup.bash
[ -f /opt/gz_ws/install/setup.bash ] && . /opt/gz_ws/install/setup.bash
[ -f "$HOME/jethexa_ws/install/setup.bash" ] && . "$HOME/jethexa_ws/install/setup.bash"

# WSLg software-rendering fallback: uncomment if the Gazebo GUI misbehaves.
# export LIBGL_ALWAYS_SOFTWARE=1

# Always succeed, so a missing workspace never breaks the login shell.
true
EOF
chmod 0644 /etc/profile.d/jethexa.sh

if [ "$CLEAN_APT" = "1" ]; then
  step "cleaning up apt lists"
  rm -rf /var/lib/apt/lists/*
  apt-get clean
fi

step "versions"
set +u
source /opt/ros/humble/setup.bash
set -u
echo "environment = ${ENVIRONMENT}"
echo "ROS_DISTRO  = ${ROS_DISTRO}"
if [ "$CREATE_USER" = "1" ]; then
  echo "user        = ${PROJECT_USER}"
else
  echo "user        = (none created; running as root)"
fi
gz sim --versions 2>/dev/null | head -1 || true
echo "DONE"
