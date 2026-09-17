#!/usr/bin/env bash
# Provision Ubuntu 22.04 with ROS 2 Humble + Gazebo Harmonic for this project.
#
#   sudo bash tools/provision_ubuntu2204.sh
#
# Tested on a fresh WSL2 Ubuntu 22.04 instance. Takes ~20 minutes and a few GB.
# Installs ROS 2 Humble desktop, ros2_control, Nav2, slam_toolbox, Gazebo
# Harmonic, ros_gz for Harmonic, gz_ros2_control built from source (there is no
# Humble+Harmonic binary of it), MuJoCo and Gymnasium.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

step() { echo; echo "=== $* ==="; }

step "base packages"
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  ca-certificates curl gnupg lsb-release locales software-properties-common \
  git build-essential cmake python3-pip python3-dev sudo nano less

locale-gen en_US en_US.UTF-8 >/dev/null
update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

step "ros 2 apt source"
add-apt-repository -y universe >/dev/null
ROS_APT_SOURCE_VERSION="$(curl -sL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
  | grep -F '"tag_name"' | awk -F'"' '{print $4}')"
echo "ros-apt-source ${ROS_APT_SOURCE_VERSION}"
CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"
curl -sL -o /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${CODENAME}_all.deb"
apt-get install -y -qq /tmp/ros2-apt-source.deb

step "gazebo apt source"
curl -sL https://packages.osrfoundation.org/gazebo.gpg \
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
mkdir -p /opt/gz_ws/src
cd /opt/gz_ws/src
[ -d gz_ros2_control ] || git clone -q --branch humble --depth 1 \
  https://github.com/ros-controls/gz_ros2_control.git
cd /opt/gz_ws
set +u
source /opt/ros/humble/setup.bash
set -u
export GZ_VERSION=harmonic
colcon build --merge-install --cmake-args -DCMAKE_BUILD_TYPE=Release

step "python: mujoco + gymnasium"
pip3 install --no-cache-dir -q --upgrade pip
pip3 install --no-cache-dir -q mujoco gymnasium numpy matplotlib

step "user account"
if ! id -u jethexa >/dev/null 2>&1; then
  useradd -m -s /bin/bash -G sudo jethexa
  echo "jethexa ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/jethexa
  chmod 0440 /etc/sudoers.d/jethexa
fi

cat > /etc/wsl.conf <<'EOF'
[user]
default=jethexa
EOF

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

step "versions"
set +u
source /opt/ros/humble/setup.bash
set -u
echo "ROS_DISTRO = ${ROS_DISTRO}"
gz sim --versions 2>/dev/null | head -1 || true
echo "DONE"
