# Command reference

Every command here has been run against this sim. Copy-paste should work.

Assumes the `jethexa` WSL environment from [setup.md](setup.md). ROS and Gazebo
are sourced automatically in a login shell, so there's no `source` step unless
you've just rebuilt.

## Get in and build

```bash
wsl -d jethexa
```

```bash
cd ~/jethexa_ws && colcon build --symlink-install
```

After a build, re-source in any shell that was already open:

```bash
source ~/jethexa_ws/install/setup.bash
```

## Run the sim

```bash
ros2 launch jethexa_sim jethexa_gazebo.launch.py
```

Headless, which is what you want for anything scripted or repeated:

```bash
ros2 launch jethexa_sim jethexa_gazebo.launch.py gui:=false
```

Launch arguments: `gui` (default true), `rviz` (default false), `spawn_z`
(default 0.15), `world` (default `worlds/flat_ground.sdf`).

Give it about 30 seconds before expecting controllers. The order is: Gazebo
starts, the robot spawns, then the controllers load.

## Make it move

Hold a standing stance (runs until you stop it):

```bash
ros2 run jethexa_sim stand.py
```

Command all 18 joints yourself, once:

```bash
ros2 topic pub --once /joint_group_position_controller/commands std_msgs/msg/Float64MultiArray "{data: [0.0,-0.6,1.3, 0.0,-0.6,1.3, 0.0,-0.6,1.3, 0.0,-0.6,1.3, 0.0,-0.6,1.3, 0.0,-0.6,1.3]}"
```

**Joint order** — 18 values, three per leg, in this order. It's defined in
`config/controllers.yaml` and it is the order the RL env has to use too:

```
lf_coxa lf_femur lf_tibia   lm_coxa lm_femur lm_tibia   lr_coxa lr_femur lr_tibia
rf_coxa rf_femur rf_tibia   rm_coxa rm_femur rm_tibia   rr_coxa rr_femur rr_tibia
```

`l`/`r` = left/right, `f`/`m`/`r` = front/middle/rear. Angles in radians, limits
±2.094 (±120°).

## Check the control stack

```bash
ros2 control list_controllers
```

Both should say `active`:

```
joint_state_broadcaster          joint_state_broadcaster/JointStateBroadcaster    active
joint_group_position_controller  forward_command_controller/ForwardCommandController  active
```

Which interfaces exist and whether a controller has claimed them:

```bash
ros2 control list_hardware_interfaces
```

## Read the robot's state

```bash
ros2 topic echo /joint_states --once
```

```bash
ros2 topic list
```

Check a sensor is actually publishing, and how fast:

```bash
ros2 topic hz /jethexa/scan
```

```bash
ros2 topic hz /jethexa/imu
```

Sensor topics: `/jethexa/scan`, `/jethexa/imu`,
`/jethexa/rgb_camera/image_raw`, `/jethexa/depth_camera/image_raw`,
`/jethexa/depth_camera/points`, plus `camera_info` for each camera.

Look at the frame tree (writes a PDF in the current directory):

```bash
ros2 run tf2_tools view_frames
```

## The Gazebo side

Gazebo has its own transport, separate from ROS. When a ROS topic is silent,
check here first to find out which side is broken.

```bash
gz topic -l
```

```bash
gz topic -e -t /scan -n 1
```

Where the robot actually is:

```bash
gz model -m jethexa -p
```

Simulation speed, which is the number that matters for training:

```bash
gz topic -e -t /stats -n 1
```

Measured headless on this machine: `real_time_factor: 0.997`. One hour of
simulation costs one hour of wall clock. PPO needs on the order of 10⁸ steps,
which is why training happens in MuJoCo and not here.

## Model checks

After any change to `urdf/`:

```bash
python3 ~/jethexa_ws/src/jethexa_sim/scripts/check_model.py
```

Expect `18 joints, sensor payload intact, 0 contact sensor(s), no dangling
collision refs`.

Expand the xacro by hand to see the generated URDF:

```bash
xacro ~/jethexa_ws/src/jethexa_sim/urdf/jethexa.urdf.xacro > /tmp/jethexa.urdf
```

```bash
check_urdf /tmp/jethexa.urdf
```

See what Gazebo will actually load, which is *not* the same as the URDF — this
is where collisions get renamed:

```bash
gz sdf -p /tmp/jethexa.urdf > /tmp/jethexa.sdf
```

## Recording data

```bash
ros2 bag record -o standtest /joint_states /jethexa/scan /jethexa/imu
```

```bash
ros2 bag info standtest
```

```bash
ros2 bag play standtest
```

## When it goes wrong

Gazebo left running after a crash, or a port already in use:

```bash
pkill -f 'gz sim'
```

`ros2` CLI throwing `!rclpy.ok()` or hanging — a CLI daemon problem, not your
nodes:

```bash
ros2 daemon stop
```

Restart the whole WSL instance (from Windows, not inside WSL):

```bash
wsl --terminate jethexa
```

Check the launch log after a failed start:

```bash
grep -iE '\[ERROR\]|exception|failed' /tmp/launch.log
```

If you redirected the launch elsewhere, look there instead. `[ERROR]` lines from
the spawner waiting for `/controller_manager` in the first ~30 seconds are
normal and resolve themselves.
