# Setting up the environment

Target: **Ubuntu 22.04 + ROS 2 Humble + Gazebo Harmonic**. The reasoning for
those versions is in the [README](../README.md#versions-and-why).

Everyone should use the same environment. Eight different ROS installs would
eat a large share of this project's total time budget.

## Already done on the project machine

A WSL instance named `jethexa` is provisioned and verified:

```bash
wsl -d jethexa
```

Nothing to install; the workspace is at `~/jethexa_ws` and the environment is
sourced automatically.

## On another Windows machine

One command, from the repo directory in PowerShell. It creates the instance,
provisions it, restarts it and verifies the result:

```bash
powershell -ExecutionPolicy Bypass -File tools\setup_wsl.ps1
```

It refuses to touch an existing instance called `jethexa` — pass `-Name
something_else`, or `-Force` to replace it (which deletes its contents). Takes
20–30 minutes, nearly all of it downloading packages.

There is no password. The `jethexa` user is created without one and has
passwordless sudo, so `wsl -d jethexa` logs straight in. Set one with
`sudo passwd jethexa` if you'd rather have it.

<details>
<summary>The same thing by hand, if the script fails</summary>

```bash
wsl --install --distribution Ubuntu-22.04 --name jethexa --no-launch
```

```bash
wsl -d jethexa -u root -- bash /mnt/c/path/to/repo/tools/provision_ubuntu2204.sh
```

The restart is not optional — `/etc/wsl.conf` only applies on restart, so
without it you log in as `root` instead of `jethexa`:

```bash
wsl --terminate jethexa
```

</details>

## On native Ubuntu 22.04

```bash
sudo bash tools/provision_ubuntu2204.sh
```

Then open a new shell so `/etc/profile.d/jethexa.sh` is picked up.

## Build the workspace

```bash
mkdir -p ~/jethexa_ws/src && cp -r jethexa_sim ~/jethexa_ws/src/ && cd ~/jethexa_ws && colcon build --symlink-install
```

## Check it worked

```bash
python3 ~/jethexa_ws/src/jethexa_sim/scripts/check_model.py
```

Expect `18 joints, sensor payload intact, 0 contact sensor(s), no dangling
collision refs`. Then launch it:

```bash
ros2 launch jethexa_sim jethexa_gazebo.launch.py
```

## Installing by hand

`tools/provision_ubuntu2204.sh` does all of this for you. The steps are here for
when you need to debug one of them, or install onto a machine you don't want a
script touching. Run as root, or prefix with `sudo`.

**1. Base packages and locale.** ROS is unhappy without a UTF-8 locale.

```bash
apt-get update && apt-get install -y ca-certificates curl gnupg lsb-release locales software-properties-common git build-essential cmake python3-pip python3-dev
```

```bash
locale-gen en_US en_US.UTF-8 && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
```

**2. The ROS 2 apt source.** Current practice is a `.deb` that installs the key
and list file, rather than piping a key into apt yourself.

```bash
add-apt-repository -y universe
```

```bash
ROS_APT_SOURCE_VERSION=$(curl -sL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F '"tag_name"' | awk -F'"' '{print $4}')
```

```bash
curl -sL -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo $VERSION_CODENAME)_all.deb"
```

```bash
apt-get install -y /tmp/ros2-apt-source.deb
```

**3. The Gazebo apt source.** Separate repository, run by OSRF.

```bash
curl -sL https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
```

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" > /etc/apt/sources.list.d/gazebo-stable.list
```

```bash
apt-get update
```

**4. ROS 2 Humble.**

```bash
apt-get install -y ros-humble-desktop ros-dev-tools
```

**5. Control, navigation and build tooling.**

```bash
apt-get install -y ros-humble-ros2-control ros-humble-ros2-controllers ros-humble-xacro ros-humble-joint-state-publisher-gui ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-slam-toolbox python3-colcon-common-extensions python3-rosdep python3-vcstool
```

**6. Gazebo Harmonic and its ROS bridge.** Note `ros-humble-ros-gzharmonic`, not
`ros-humble-ros-gz` — the latter pairs Humble with Fortress, which is
end-of-life.

```bash
apt-get install -y gz-harmonic ros-humble-ros-gzharmonic
```

```bash
rosdep init; rosdep update --rosdistro humble
```

**7. `gz_ros2_control`, from source.** There is no Humble + Harmonic binary, so
this one gets built. `GZ_VERSION=harmonic` is what makes it build against
gz-sim 8 instead of Fortress — without it you get a package that loads and then
fails to find the simulator.

```bash
mkdir -p /opt/gz_ws/src && git clone --branch humble --depth 1 https://github.com/ros-controls/gz_ros2_control.git /opt/gz_ws/src/gz_ros2_control
```

```bash
cd /opt/gz_ws && source /opt/ros/humble/setup.bash && GZ_VERSION=harmonic colcon build --merge-install --cmake-args -DCMAKE_BUILD_TYPE=Release
```

**8. Python packages** for the training sim, needed from Week 3.

```bash
pip3 install mujoco gymnasium numpy matplotlib
```

**9. Environment.** Put this in `/etc/profile.d/jethexa.sh` so it applies to
login shells. Do *not* put it only in `~/.bashrc` — that returns early for
non-interactive shells, so `wsl -d jethexa -- bash -lc "..."` would get none of it.

```bash
cat > /etc/profile.d/jethexa.sh <<'EOF'
export GZ_VERSION=harmonic
export ROS_DOMAIN_ID=42
[ -f /opt/ros/humble/setup.bash ] && . /opt/ros/humble/setup.bash
[ -f /opt/gz_ws/install/setup.bash ] && . /opt/gz_ws/install/setup.bash
[ -f "$HOME/jethexa_ws/install/setup.bash" ] && . "$HOME/jethexa_ws/install/setup.bash"
true
EOF
```

Open a new shell, then check:

```bash
echo "$ROS_DISTRO $GZ_VERSION" && gz sim --versions
```

Expect `humble harmonic` and `8.x.x`.

## What the provisioning script installs

| | |
|---|---|
| ROS 2 | `ros-humble-desktop`, `ros-dev-tools`, colcon |
| Control | `ros2_control`, `ros2_controllers` |
| Navigation | `navigation2`, `nav2_bringup`, `slam_toolbox` |
| Simulation | `gz-harmonic`, `ros-humble-ros-gzharmonic` |
| Control bridge | `gz_ros2_control`, **built from source** at `/opt/gz_ws` |
| Python | `mujoco`, `gymnasium`, numpy, matplotlib |

`gz_ros2_control` is built from source because no Humble + Harmonic binary
exists — the released binary pairs Humble with Fortress, which is end-of-life.
The build needs `GZ_VERSION=harmonic` set, which the script handles.

## Things that bit us, so they don't bite you

**The GUI under WSL.** WSLg renders the Gazebo GUI, but sensor update rates run
well below what they request under software rendering (we measured lidar at
~4.4 Hz against 10 Hz). If the GUI misbehaves, uncomment
`LIBGL_ALWAYS_SOFTWARE=1` in `/etc/profile.d/jethexa.sh`. For batch work, use
`gui:=false`.

**WSL shuts an instance down** when the last process exits, which kills anything
you backgrounded with `nohup`. Keep a shell open, or use `systemd-run`.

**`~/.bashrc` returns early for non-interactive shells**, so environment setup
placed there never runs under `wsl -d jethexa -- bash -lc "..."`. That is why
the environment lives in `/etc/profile.d/jethexa.sh` instead.

**The `ros2` CLI daemon** intermittently throws `!rclpy.ok()` on this setup. Run
`ros2 daemon stop` and retry; it is a CLI issue, not a problem with your nodes.

**PowerShell eats `$VAR` before WSL sees it.** `wsl -d jethexa -- bash -lc 'echo
"$ROS_DISTRO"'` comes back empty even though the variable is set, because
PowerShell expands it first. Use `printenv ROS_DISTRO` instead, or run the
command from inside the instance. This cost us a false alarm about the
environment being broken when it wasn't.
