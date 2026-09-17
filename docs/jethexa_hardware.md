# Hiwonder JetHexa — Advanced Kit

Reference sheet for the platform we are simulating and, eventually, deploying to.
Everything marked **[verify]** could not be confirmed from published vendor
documentation — measure or read it off the physical robot before any number here
is used in the simulation model or in a sim-to-real transfer.

---

## 1. Platform summary

JetHexa is an 18-DoF hexapod (six legs × three joints) built around an NVIDIA
Jetson Nano, running ROS. The Advanced Kit is the middle tier of three:

| Kit | Vision | Lidar |
|---|---|---|
| Standard | monocular HD camera | EAI G4 |
| **Advanced (ours)** | **3D depth camera (RGB + depth)** | **EAI G4** |
| Ultimate | depth camera + 6-mic array | EAI G4 |

Stock firmware ships tripod and ripple gaits driven by an analytic inverse
kinematics solver, with adjustable body pitch, roll, height, stride and speed.
**Our project replaces that gait layer with a learned policy** — the stock gaits
are our baseline to beat, not our starting code.

---

## 2. Compute

| Item | Spec |
|---|---|
| SoC module | NVIDIA Jetson Nano **B01**, 4 GB |
| GPU | 128-core Maxwell |
| CPU | quad-core ARM Cortex-A57 |
| OS / middleware | Hiwonder image: Ubuntu 18.04 + **ROS 1 Melodic** **[verify — see §7]** |
| Accel stack | TensorRT, OpenCV, PyTorch/TF (vendor-supplied) |
| Storage | microSD **[verify size]** |

The Nano is the inference target. A policy that needs more than ~10 ms per step
at 50 Hz on this hardware is not deployable — keep the actor network small
(2×128 or 2×256 MLP is the usual size for this class of robot).

## 3. Actuation

| Item | Spec |
|---|---|
| Joints | 18 (6 legs × coxa / femur / tibia) |
| Servos | 18 × **Hiwonder HX-35H** serial bus servos (confirmed) |
| Range | 0–240°, i.e. ±120° about centre; 0–1000 command counts map to that range |
| Torque | 25 kg·cm running, 35 kg·cm stall @ 11.1 V → **2.45 N·m / 3.43 N·m** |
| Speed | 0.18 s per 60° @ 11.1 V → **5.82 rad/s** no-load |
| Accuracy | 0.3° |
| Current | 100 mA no load, 3 A stall (× 18 servos — size the battery budget accordingly) |
| Bus | UART serial daisy chain, **115200 baud** |
| Feedback | position, voltage and temperature, read back over the same bus |
| Control mode | **position only** — no torque command, no direct current control |

Working voltage is **9–12.6 V**, so the pack is 3S (11.1 V nominal), not the
7.4 V quoted for some other Hiwonder kits. Confirm against the actual battery.

**This is the single most important constraint on the RL design.** The action
space must be joint *positions* (or position deltas), not torques. The servo's
internal PD loop sits between the policy and the world, and its gains are not
directly observable — identifying its effective stiffness/damping is a Week 2+
task and the main sim-to-real gap.

### The bus is a bandwidth constraint, and it may cap our control rate

115200 baud is roughly 11.5 kB/s. A Hiwonder position command is about 10 bytes,
so writing all 18 joints costs ~180 bytes ≈ **16 ms**, i.e. a ceiling near 60 Hz
for commands alone. Reading position back adds a request and a reply per servo
(~14 bytes plus turnaround), which roughly doubles it — call it **25–30 Hz** for
a full command-and-read cycle on a single bus.

Our working assumption has been a 50 Hz control loop. That may not be reachable
with full joint feedback. Three ways out, in rough order of preference:

1. Feed the policy the *commanded* joint positions instead of measured ones, plus
   the IMU, and skip the per-cycle readback. Costs almost nothing and is what
   many deployed locomotion policies do anyway.
2. Read feedback at a lower rate than the control loop.
3. Check whether the expansion board splits the 18 servos across more than one
   bus, which would change the arithmetic. **[verify on the robot]**

This is worth measuring early — the answer constrains both the control rate and
the observation space, and both are decisions we make in the first month.

## 4. Sensing

| Sensor | Spec | Sim topic (in `jethexa_sim`) |
|---|---|---|
| 2D lidar | EAI G4, 360°, ≈0.12–16 m, 5–12 Hz **[verify range/rate]** | `/jethexa/scan` |
| Depth camera | 3D depth camera, RGB + depth, 640×480 **[verify model — Astra-class]** | `/jethexa/depth_camera/*` |
| IMU | 6-axis on the expansion board **[verify part]** | `/jethexa/imu` |
| Servo feedback | per-joint position from the bus | `/joint_states` |
| Foot contact | **not present on hardware** | not available in sim either |

Two notes that shape the whole project:

- **There is no foot contact signal, in sim or on the robot.** The real JetHexa
  has no foot switches, and Gazebo's contact sensors turned out not to publish
  for our URDF-spawned model either (see the README's known limitations). So the
  observation space excludes contact, full stop. If contact is wanted for reward
  shaping it belongs in the MuJoCo training sim, where it is directly available,
  and where training happens anyway. Training on a signal we cannot reproduce on
  hardware is the classic way to waste four weeks.
- **The lidar is 2D and mast-mounted.** It sees walls, poles and vehicles at one
  height. It does **not** see curbs, kerb ramps or the crosswalk surface. All
  terrain sensing has to come from the depth camera and the IMU.

## 5. Chassis / mechanics

| Item | Value |
|---|---|
| Legs | 6, radially mounted (front pair ±45°, middle pair ±90°, rear pair ±135°) |
| Body dimensions | ≈220 × 130 × 50 mm **[verify — placeholder in `props.xacro`]** |
| Standing height | ≈120 mm **[verify]** |
| Link lengths | coxa 45 / femur 75 / tibia 130 mm **[verify — placeholders]** |
| Total mass | ≈2.2 kg incl. battery **[verify]** |
| Battery | 7.4 V Li-ion pack **[verify capacity]** |

Every one of these feeds directly into the URDF. Getting them wrong is a silent
error: the policy trains fine and then falls over on hardware. Task **A3** in the
Week 1 list exists solely to close this out with calipers and a scale.

## 6. What the stock software gives us for free

Worth knowing so nobody rebuilds it: the vendor image already includes SLAM
(Gmapping / Karto / Hector / Cartographer), 2D navigation with TEB local
planning, RTAB-Map 3D mapping, and an IK-driven gait engine. Our contribution is
the **learned locomotion layer** and the **outdoor crosswalk navigation task** —
we should reuse their mapping/navigation stack where it is good enough rather
than reimplementing SLAM.

## 7. Open risk: ROS 1 vs ROS 2

The starter sim is **ROS 2 + Gazebo Classic**, because that is what current
`ros2_control` / `gazebo_ros2_control` tooling supports and what the students
will find documentation for. The stock JetHexa image is **ROS 1 Melodic**.

Three ways out, to be decided in Week 2 (task **D4**):
1. Deploy the policy on the Nano as a **plain Python process** over the servo bus
   driver, with no ROS at all on the control path. Lowest friction; my default.
2. `ros1_bridge` between the vendor stack and a ROS 2 policy node.
3. Reflash the Nano with Ubuntu 20.04 + ROS 2 Foxy and port the servo driver.
   Most work, cleanest end state, highest risk of bricking the one robot we have.

Do not let this decision drift past Week 2 — it determines what the RL team's
inference wrapper has to look like.

---

## Sources

- [Hiwonder JetHexa product page](https://www.hiwonder.com/products/jethexa)
- [Hiwonder — How does JetHexa work with lidar and camera?](https://www.hiwonder.com/blogs/news/how-does-jethexa-work-with-lidar-and-camera)
- [JetHexa Advanced Kit (Amazon listing)](https://www.amazon.com/HIWONDER-JetHexa-Hexapod-Navigation-Advanced/dp/B0C3426SH2)
- [JetHexa Advanced Kit (OzRobotics)](https://ozrobotics.com/shop/hiwonder-jethexa-ros-hexapod-robot-kit-powered-by-jetson-nano-with-lidar-depth-camera-advanced-kit/)
