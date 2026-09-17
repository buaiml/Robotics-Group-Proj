# JetHexa — Walking

Starter Gazebo environment for the Hiwonder JetHexa (Advanced Kit), plus the
hardware reference and the semester plan.

- [`jethexa_sim/`](jethexa_sim) — ROS 2 Humble + Gazebo Harmonic package: 18-DoF
  robot model, sensors, flat-ground world, one launch file, one stand-up test.
- [`docs/jethexa_hardware.md`](docs/jethexa_hardware.md) — the robot, its
  sensors and components, and the constraints they put on the project.
- [`docs/semester_plan.md`](docs/semester_plan.md) — the 14-week plan: scope,
  teams, teaching calendar, standing decisions, risks.
- [`docs/tasks_weeks_1_2.md`](docs/tasks_weeks_1_2.md) — Weeks 1–2 task list.
- [`docs/commands.md`](docs/commands.md) — command reference for everyday sim work.

## Versions, and why

| | |
|---|---|
| Ubuntu | 22.04 |
| ROS 2 | **Humble** |
| Gazebo | **Harmonic** (gz-sim 8) |

**Humble**, not Jazzy, because the robot is a Jetson Nano on JetPack 4.6 /
Ubuntu 18.04. ROS 2 on that means a Humble container (`dustynv/ros:humble-*-l4t-r32.7.1`)
or no ROS on the control path. Matching the robot matters more than being current.

**Harmonic**, not Gazebo Classic, because Classic went end-of-life in January
2025. Humble's own default pairing (Fortress) hit end-of-life in September 2026,
so Harmonic is the only live option. The catch: there is no Humble + Harmonic
binary of `gz_ros2_control`, so it is built from source — already done in the
environment below.

## Environment

A ready WSL instance is set up on this machine:

```bash
wsl -d jethexa
```

Ubuntu 22.04, user `jethexa`, with ROS 2 Humble, Gazebo Harmonic, Nav2,
slam_toolbox, MuJoCo and Gymnasium installed. `gz_ros2_control` is built at
`/opt/gz_ws`. The environment is sourced automatically from
`/etc/profile.d/jethexa.sh`, so every login shell has ROS and `GZ_VERSION` set.
The workspace lives at `~/jethexa_ws`.

To set this up elsewhere, see [`docs/setup.md`](docs/setup.md).

## Build and run

```bash
cd ~/jethexa_ws && colcon build --symlink-install && source install/setup.bash
```

```bash
ros2 launch jethexa_sim jethexa_gazebo.launch.py
```

Then, in a second shell, put the robot into a stance:

```bash
ros2 run jethexa_sim stand.py
```

Headless, for batch runs: `ros2 launch jethexa_sim jethexa_gazebo.launch.py gui:=false`

After changing anything in `urdf/`, run the model check:

```bash
python3 ~/jethexa_ws/src/jethexa_sim/scripts/check_model.py
```

It asserts the 18 joints and the sensors survive URDF→SDF conversion, and that
no sensor references a collision that does not exist. That last one matters: a
sensor with a wrong collision reference loads fine and silently publishes
nothing.

## What's in the sim

| | |
|---|---|
| Joints | 18, position-commanded on `/joint_group_position_controller/commands` (`Float64MultiArray`, 18 values, order in `config/controllers.yaml`) |
| Joint state | `/joint_states` (via `gz_ros2_control`) |
| Lidar | `/jethexa/scan` — 360°, 720 beams, 10 Hz requested |
| RGB camera | `/jethexa/rgb_camera/image_raw` + `camera_info` |
| Depth camera | `/jethexa/depth_camera/image_raw`, `/points`, `camera_info` |
| IMU | `/jethexa/imu` — 100 Hz requested |
| World | `worlds/flat_ground.sdf` — flat ground and a light, nothing else |

Verified working: both controllers come up active, all 18 joints track commanded
positions, lidar and IMU publish through the bridge.

## Known limitations

Read these before trusting a result from this sim.

**The geometry is still placeholder.** Link lengths, masses and mount offsets in
`urdf/props.xacro` come from the published footprint, not from the robot. The
servo limits *are* real (HX-35H datasheet). Hiwonder ships an accurate URDF with
meshes in the robot's own ROS packages, so the fix is to copy that off the robot
and fold its numbers in — a Week 2 task, and the one that makes this sim mean
anything.

**The stance height does not match the model.** `stand.py` settles the body about
5.3 cm off the ground, while `stand_height` in `props.xacro` claims 12 cm. The
placeholder link lengths and the arbitrary stance angles simply disagree. Both
get fixed once the robot is measured.

**No foot contact sensors.** Two reasons: the real robot has no foot switches, so
a policy using contact could not be deployed; and Gazebo's contact sensors do not
publish for URDF-spawned models in this Humble + Harmonic combination — verified
against both the as-written and the sdformat-emitted collision names. If contact
is wanted for reward shaping, do it in the MuJoCo training sim, which is where
training happens anyway.

**Friction comes from the ground, not the robot.** The `<mu1>`/`<mu2>` URDF
extension attaches by collision name, and sdformat renames collisions during
conversion, so per-link friction silently does nothing. The ground surface in
the world file sets it instead. Per-link friction would need the model authored
in SDF rather than converted from URDF.

**Sensor rates run below what they request** under WSL software rendering — lidar
measured ~4.4 Hz against 10 Hz requested, IMU ~41 Hz against 100 Hz. Fine for
integration testing, not for anything timing-sensitive. This is also a reminder
that Gazebo is the validation sim, not the training sim.
