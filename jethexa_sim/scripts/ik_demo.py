#!/usr/bin/env python3
"""Inverse-kinematics demo for the JetHexa sim.

    ros2 run jethexa_sim ik_demo.py               # every segment, in order
    ros2 run jethexa_sim ik_demo.py height wave   # just the ones you name
    ros2 run jethexa_sim ik_demo.py --check       # is every pose reachable? (robot stays still)

Segments: stand, height, sway, twist, lean, wave.

The whole demo rests on one idea: decide where the FEET should be, and let
inverse kinematics work out the 18 joint angles. The feet stay planted on the
ground while the body moves above them - which only works because IK is solving
all six legs, 50 times a second.

Link lengths and leg mounts are read from the robot's own URDF at startup, so
when the model is updated with the real geometry, this demo follows it.

Stop stand.py first: two nodes sending joint commands will fight each other.
"""
import math
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np
import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.utilities import remove_ros_args
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

LEGS = ["lf", "lm", "lr", "rf", "rm", "rr"]  # joint order of config/controllers.yaml
TOPIC = "/joint_group_position_controller/commands"
RATE_HZ = 50.0
HOME_HEIGHT = 0.08  # body height above the ground in the home stance (m)
HOME_REACH = 0.13   # horizontal foot distance out from the femur joint (m).
                    # Wider is more stable AND keeps the knees less folded: at
                    # 0.12 m, leaning left the knee only 3.4 deg from its limit.

SEGMENTS = {
    # name: (seconds, what to say while it runs)
    "stand":  (4.0,  "Standing up: blending from wherever the joints are to the IK home stance."),
    "height": (10.0, "Body height: feet fixed, body rises to 12 cm and sinks to 6 cm.\n"
                     "     12 cm is the height the URDF claims - the lecture exercise asked what\n"
                     "     angles reach it. IK is answering that question, live, for all six legs."),
    "sway":   (10.0, "Roll, then pitch: the body tilts 10 degrees, feet stay put.\n"
                     "     Every foot target is the same world point, re-expressed in a tilted body."),
    "twist":  (6.0,  "Yaw: the body turns 12 degrees on the spot, feet planted."),
    "lean":   (8.0,  "Lean: the body circles over its feet - the centre of mass moves around\n"
                     "     inside the support polygon, which is why it doesn't fall."),
    "wave":   (10.0, "Wave: front-left foot lifts and draws circles. Five feet stay down, so the\n"
                     "     robot is still statically stable - the hexapod advantage from the lecture."),
}


# ---------------------------------------------------------------- geometry --

def load_geometry():
    """Read link lengths, leg mounts and joint limits from the robot's URDF."""
    share = get_package_share_directory("jethexa_sim")
    urdf = subprocess.run(["xacro", f"{share}/urdf/jethexa.urdf.xacro"],
                          check=True, capture_output=True, text=True).stdout
    root = ET.fromstring(urdf)
    # Top-level only: the <ros2_control> block ALSO contains <joint> elements with
    # the same names but no <origin>, and a whole-tree search picks those up.
    joints = {j.get("name"): j for j in root.findall("joint")}
    links = {link.get("name"): link for link in root.findall("link")}

    def origin(el):
        o = el.find("origin")
        xyz = [float(v) for v in o.get("xyz", "0 0 0").split()]
        rpy = [float(v) for v in o.get("rpy", "0 0 0").split()]
        return xyz, rpy

    foot = next(c for c in links["lf_tibia_link"].iter("collision")
                if c.get("name") == "lf_foot_collision")
    geo = {
        "L1": origin(joints["lf_femur_joint"])[0][0],   # coxa length
        "L2": origin(joints["lf_tibia_joint"])[0][0],   # femur length
        "L3": origin(foot)[0][0],                        # tibia length, to the foot centre
        "foot_r": float(foot.find("geometry/sphere").get("radius")),
        "limit": float(joints["lf_femur_joint"].find("limit").get("upper")),
        "mounts": {},
    }
    for leg in LEGS:
        xyz, rpy = origin(joints[f"{leg}_coxa_joint"])
        geo["mounts"][leg] = (np.array(xyz), rpy[2])
    return geo


class Leg:
    """One 3-DoF leg: coxa yaws, femur and tibia pitch.

    Sign convention, the one from the Week 2 lecture: a rotation about +y by
    theta maps x to (cos theta, 0, -sin theta), so a POSITIVE femur angle drives
    the foot DOWN. Internally the planar maths uses the usual y-up angles
    a = -femur, b = -tibia.
    """

    def __init__(self, mount, yaw, L1, L2, L3):
        self.mount, self.yaw = mount, yaw
        self.L1, self.L2, self.L3 = L1, L2, L3

    def _to_leg(self, v):
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        return c * v[0] + s * v[1], -s * v[0] + c * v[1], v[2]

    def _from_leg(self, x, y, z):
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        return self.mount + np.array([c * x - s * y, s * x + c * y, z])

    def ik(self, foot):
        """Foot position in the body frame -> (coxa, femur, tibia) in radians."""
        lx, ly, lz = self._to_leg(foot - self.mount)
        coxa = math.atan2(ly, lx)                    # turntable: point the leg at the foot
        X = math.hypot(lx, ly) - self.L1             # then a 2-link planar arm from the femur joint
        Y = lz
        cos_b = (X * X + Y * Y - self.L2 ** 2 - self.L3 ** 2) / (2 * self.L2 * self.L3)
        if not -1.0 <= cos_b <= 1.0:                 # outside the reachable annulus
            raise ValueError(f"foot target {foot.round(3)} is out of reach")
        b = -math.acos(cos_b)                        # knee UP: the branch the stand pose uses
        a = math.atan2(Y, X) - math.atan2(self.L3 * math.sin(b), self.L2 + self.L3 * math.cos(b))
        return coxa, -a, -b

    def fk(self, coxa, femur, tibia):
        """(coxa, femur, tibia) -> foot position in the body frame."""
        a, b = -femur, -tibia
        rho = self.L1 + self.L2 * math.cos(a) + self.L3 * math.cos(a + b)
        z = self.L2 * math.sin(a) + self.L3 * math.sin(a + b)
        return self._from_leg(rho * math.cos(coxa), rho * math.sin(coxa), z)


def rotation(roll, pitch, yaw):
    cr, sr, cp, sp, cy, sy = (math.cos(roll), math.sin(roll), math.cos(pitch),
                              math.sin(pitch), math.cos(yaw), math.sin(yaw))
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def ease(u):
    """0 -> 1 with zero velocity at both ends, so nothing jerks."""
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def envelope(u):
    """0 -> 1 -> 0, smooth at both ends: fade a motion in and out."""
    return math.sin(math.pi * min(max(u, 0.0), 1.0)) ** 2


# ---------------------------------------------------------------- the node --

class IKDemo(Node):
    def __init__(self, segments):
        # SIMULATION time, not wall-clock time. Gazebo stalls now and then (we
        # measured it dropping to 2% of real time with the GUI open). On a
        # wall clock the demo would keep marching while the robot is frozen,
        # then the joints snap to catch up. On sim time the demo pauses too.
        super().__init__("jethexa_ik_demo", parameter_overrides=[
            Parameter("use_sim_time", Parameter.Type.BOOL, True)])
        geo = load_geometry()
        self.geo = geo
        self.legs = {leg: Leg(*geo["mounts"][leg], geo["L1"], geo["L2"], geo["L3"]) for leg in LEGS}

        # Home stance: each foot straight out along its leg, on the ground.
        z_foot = -(HOME_HEIGHT - geo["foot_r"])
        self.home_feet = {}
        for leg, (mount, yaw) in geo["mounts"].items():
            r = geo["L1"] + HOME_REACH
            self.home_feet[leg] = mount + np.array([r * math.cos(yaw), r * math.sin(yaw), z_foot])
        self.home_angles = self.solve_all(self.home_feet)

        self.self_check()
        self.check_plan([name for name in segments if name != "stand"])

        self.pub = self.create_publisher(Float64MultiArray, TOPIC, 10)
        self.measured = {}
        self.create_subscription(JointState, "/joint_states", self.on_joint_states, 10)

        self.plan = [(name, SEGMENTS[name][0]) for name in segments]
        self.seg_index = -1
        self.seg_start = None
        self.start_angles = None
        self.last_cmd = None
        self.errors = []
        self.skipped = 0
        self.done = False
        self.create_timer(1.0 / RATE_HZ, self.tick)

    # -- maths helpers --------------------------------------------------------

    def solve_all(self, feet):
        angles = []
        for leg in LEGS:
            angles.extend(self.legs[leg].ik(feet[leg]))
        lim = self.geo["limit"]
        for i, a in enumerate(angles):
            if abs(a) > lim:
                joint = f"{LEGS[i // 3]}_{('coxa', 'femur', 'tibia')[i % 3]}"
                raise ValueError(f"{joint} would need {math.degrees(a):+.0f} deg, "
                                 f"past its +/-{math.degrees(lim):.0f} deg limit")
        return angles

    def self_check(self):
        """IK and FK must be exact inverses. Show it before trusting either."""
        worst = 0.0
        for leg in LEGS:
            back = self.legs[leg].fk(*self.legs[leg].ik(self.home_feet[leg]))
            worst = max(worst, float(np.linalg.norm(back - self.home_feet[leg])))
        g = self.geo
        self.get_logger().info(
            f"geometry from the URDF: coxa {g['L1']*1000:.0f} mm, femur {g['L2']*1000:.0f} mm, "
            f"tibia {g['L3']*1000:.0f} mm, reach {abs(g['L3']-g['L2'])*1000:.0f}-{(g['L2']+g['L3'])*1000:.0f} mm")
        self.get_logger().info(f"IK self-check: FK(IK(foot)) round trip is off by {worst*1e6:.3f} micrometres")

    def check_plan(self, names, samples=200):
        """Solve every pose of every segment BEFORE moving. IK tells you in
        advance whether a motion is physically possible - use that."""
        tightest = (math.inf, None)
        lim = self.geo["limit"]
        for name in names:
            for k in range(samples + 1):
                u = k / samples
                try:
                    angles = self.targets(name, u)
                except ValueError as exc:
                    raise SystemExit(f"plan check failed: '{name}' at {u * SEGMENTS[name][0]:.1f} s: {exc}")
                margin = min(lim - abs(a) for a in angles)
                if margin < tightest[0]:
                    tightest = (margin, name)
        if tightest[1]:
            self.get_logger().info(f"plan check: every pose reachable; tightest joint margin "
                                   f"{math.degrees(tightest[0]):.1f} deg (in '{tightest[1]}')")

    def feet_for_body(self, shift, rpy):
        """Feet fixed in the world; body moved by `shift` and turned by `rpy`.
        Returns each foot re-expressed in the moved body's frame."""
        R = rotation(*rpy)
        return {leg: R.T @ (p - shift) for leg, p in self.home_feet.items()}

    # -- segments -------------------------------------------------------------

    def targets(self, name, u):
        """Joint targets for segment `name` at progress u in [0, 1]."""
        if name == "stand":
            k = ease(u)
            return [s + (h - s) * k for s, h in zip(self.start_angles, self.home_angles)]

        zero = np.zeros(3)
        if name == "height":
            s = math.sin(2 * math.pi * u)
            dz = 0.04 * s if s > 0 else 0.02 * s          # up to 12 cm, down to 6 cm
            feet = self.feet_for_body(np.array([0, 0, dz]), (0, 0, 0))
        elif name == "sway":
            ang = math.radians(10)
            if u < 0.5:
                rpy = (ang * math.sin(4 * math.pi * u), 0, 0)
            else:
                rpy = (0, ang * math.sin(4 * math.pi * (u - 0.5)), 0)
            feet = self.feet_for_body(zero, rpy)
        elif name == "twist":
            feet = self.feet_for_body(zero, (0, 0, math.radians(12) * math.sin(2 * math.pi * u)))
        elif name == "lean":
            r = 0.025 * envelope(u)
            th = 2 * math.pi * 2 * u                      # two laps
            feet = self.feet_for_body(np.array([r * math.cos(th), r * math.sin(th), 0]), (0, 0, 0))
        elif name == "wave":
            feet = dict(self.home_feet)
            e = envelope(u)
            _, yaw = self.geo["mounts"]["lf"]
            out = np.array([math.cos(yaw), math.sin(yaw), 0])
            th = 2 * math.pi * 3 * u                      # three circles
            # Circle centre pushed 25 mm OUTWARD: circling inward and upward would
            # make the knee fold to ~129 deg, past the HX-35H's 120 deg limit.
            # check_plan() now rejects a shape like that before the robot moves.
            feet["lf"] = (self.home_feet["lf"] + e * (0.025 * out + np.array([0, 0, 0.045]))
                          + 0.015 * e * (math.cos(th) * out + np.array([0, 0, math.sin(th)])))
        else:
            raise KeyError(name)
        return self.solve_all(feet)

    # -- ROS plumbing ---------------------------------------------------------

    def on_joint_states(self, msg):
        self.measured.update(zip(msg.name, msg.position))

    def measured_vector(self):
        names = [f"{leg}_{j}_joint" for leg in LEGS for j in ("coxa", "femur", "tibia")]
        if not all(n in self.measured for n in names):
            return None
        return [self.measured[n] for n in names]

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def begin_segment(self, i):
        self.seg_index, self.seg_start = i, self.now()
        name, secs = self.plan[i]
        self.errors = []
        self.skipped = 0
        if name == "stand":
            # Blend from where the joints REALLY are. An earlier version fell back
            # to all-zeros when no reading had arrived yet, which commanded every
            # leg straight out for a moment - a visible twitch at the start.
            self.start_angles = self.measured_vector()
        print(f"\n[{i + 1}/{len(self.plan)}] {name} ({secs:.0f} s)\n     {SEGMENTS[name][1]}", flush=True)

    def end_segment(self):
        if self.skipped:
            print(f"     WARNING: {self.skipped} ticks ({self.skipped / RATE_HZ:.1f} s) held because a pose "
                  f"was unreachable", flush=True)
        if self.errors:
            print(f"     tracking: commanded vs measured joints, worst {max(self.errors):.1f} deg, "
                  f"typical {sorted(self.errors)[len(self.errors) // 2]:.1f} deg", flush=True)

    def tick(self):
        if self.done:
            return
        if self.seg_index < 0:
            if self.pub.get_subscription_count() == 0 or self.now() == 0.0:
                return                                    # controller or /clock not up yet
            if self.measured_vector() is None:
                return                                    # no joint readings yet: never guess
            if self.count_publishers(TOPIC) > 1:
                self.get_logger().warn("another node is also commanding the joints - stop stand.py")
            self.begin_segment(0)

        name, secs = self.plan[self.seg_index]
        u = (self.now() - self.seg_start) / secs
        if u >= 1.0:
            self.end_segment()
            if self.seg_index + 1 >= len(self.plan):
                self.publish(self.home_angles)
                print("\nDone - holding the home stance. The controller keeps it after exit.", flush=True)
                self.done = True
                return
            self.begin_segment(self.seg_index + 1)
            name, secs = self.plan[self.seg_index]
            u = 0.0

        try:
            cmd = self.targets(name, u)
        except ValueError as exc:
            if not self.skipped:
                self.get_logger().warn(f"{name}: {exc}; holding the last command")
            self.skipped += 1
            return

        # How far the real joints lag the previous command: the position
        # controller is not instant, and neither is a real servo.
        meas = self.measured_vector()
        if meas is not None and self.last_cmd is not None:
            self.errors.append(max(math.degrees(abs(c - m)) for c, m in zip(self.last_cmd, meas)))
        self.publish(cmd)

    def publish(self, angles):
        self.pub.publish(Float64MultiArray(data=list(angles)))
        self.last_cmd = list(angles)


def main():
    argv = remove_ros_args(sys.argv)[1:]
    check_only = "--check" in argv
    argv = [a for a in argv if a != "--check"]
    chosen = argv or list(SEGMENTS)
    unknown = [s for s in chosen if s not in SEGMENTS]
    if unknown:
        print(f"unknown segment(s): {', '.join(unknown)}. Choose from: {', '.join(SEGMENTS)}")
        sys.exit(2)
    if chosen[0] != "stand":
        chosen = ["stand"] + chosen                       # always start from a known pose

    rclpy.init()
    node = IKDemo(chosen)        # the constructor already runs the plan check
    if check_only:
        node.destroy_node()
        rclpy.shutdown()
        return
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
        # a few more spins so the final home command goes out
        for _ in range(5):
            rclpy.spin_once(node, timeout_sec=0.05)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
