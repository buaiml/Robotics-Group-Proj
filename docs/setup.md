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

Create a fresh WSL instance, separate from any Ubuntu you already have:

```bash
wsl --install --distribution Ubuntu-22.04 --name jethexa --no-launch
```

Then provision it. From the repo directory:

```bash
wsl -d jethexa -u root -- bash /mnt/c/path/to/repo/tools/provision_ubuntu2204.sh
```

Restart the instance so the default user takes effect:

```bash
wsl --terminate jethexa
```

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
