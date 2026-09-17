# JetHexa — Walking

Starter Gazebo environment for the Hiwonder JetHexa (Advanced Kit), plus the
hardware reference and the Weeks 1–2 plan.

- [`jethexa_sim/`](jethexa_sim) — ROS 2 + Gazebo Classic package: 18-DoF robot
  model, sensors, flat-ground world, one launch file, one stand-up smoke test.
- [`docs/jethexa_hardware.md`](docs/jethexa_hardware.md) — the robot, its
  sensors and components, and the constraints they put on the project.
- [`docs/semester_plan.md`](docs/semester_plan.md) — the 14-week plan: scope,
  teams, teaching calendar, standing decisions, risks.
- [`docs/tasks_weeks_1_2.md`](docs/tasks_weeks_1_2.md) — Weeks 1–2, one task per
  student per week, each sized to a single 1–2 hour sitting.

## Requirements

Ubuntu 22.04 · ROS 2 Humble · Gazebo Classic 11.

```bash
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control \
  ros-humble-ros2-control ros-humble-ros2-controllers ros-humble-xacro
```

## Build and run

```bash
mkdir -p ~/jethexa_ws/src && cp -r jethexa_sim ~/jethexa_ws/src/ && cd ~/jethexa_ws && colcon build --symlink-install && source install/setup.bash
```

```bash
ros2 launch jethexa_sim jethexa_gazebo.launch.py
```

Then, in a second sourced terminal, put the robot into a stance:

```bash
ros2 run jethexa_sim stand.py
```

Headless (for batch runs): `ros2 launch jethexa_sim jethexa_gazebo.launch.py gui:=false`

## What's in the sim

| | |
|---|---|
| Joints | 18, position-commanded via `/joint_group_position_controller/commands` (`Float64MultiArray`, 18 values, order in `config/controllers.yaml`) |
| Lidar | `/jethexa/scan` — 360°, 720 beams, 10 Hz |
| Depth camera | `/jethexa/depth_camera/*` — RGB + depth, 640×480, 15 Hz |
| IMU | `/jethexa/imu` — 100 Hz |
| Foot contacts | `/jethexa/contacts/<leg>_foot` — **simulation only**, no hardware equivalent |
| World | `worlds/flat_ground.world` — flat ground and a sun, nothing else |

The link lengths, masses and joint limits in `urdf/props.xacro` are placeholders
taken from the published footprint. Measure the real robot and replace them
(task **A3**) before drawing any conclusion from this sim.
