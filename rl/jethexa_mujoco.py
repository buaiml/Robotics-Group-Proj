#!/usr/bin/env python3
"""Build a MuJoCo model of the JetHexa from the SAME xacro that Gazebo uses.

There is one robot description in this repo (jethexa_sim/urdf/). Training in
MuJoCo and checking in Gazebo only means something if both simulators load the
same robot, so this file never keeps its own copy of the geometry: it runs
xacro, strips the Gazebo-only parts, and adds what MuJoCo needs on top.

    python3 rl/jethexa_mujoco.py                     # summary of the model
    python3 rl/jethexa_mujoco.py --export /tmp/j.xml # the MJCF, to read
    python3 rl/jethexa_mujoco.py --view              # look at it, standing

When the robot-model work replaces the placeholder geometry with the vendor
URDF's numbers, this picks the change up automatically.
"""
import argparse
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import mujoco
import numpy as np

LEGS = ["lf", "lm", "lr", "rf", "rm", "rr"]
# Same order as config/controllers.yaml, so a policy's 18 outputs map onto the
# Gazebo controller (and later the real robot) without reshuffling.
JOINTS = [f"{leg}_{part}_joint" for leg in LEGS for part in ("coxa", "femur", "tibia")]

# The stance from jethexa_sim/scripts/stand.py: coxa 0, femur -35 deg, tibia 75 deg.
HOME = np.array([0.0, math.radians(-35.0), math.radians(75.0)] * len(LEGS))

# Servo model. The HX-35H is a position servo: it is told an angle and pushes
# towards it, up to its torque limit. A MuJoCo position actuator does the same.
# KP is a guess - nobody has measured the real servo's stiffness yet. That is a
# task, and it matters: a policy trained on a stiffer servo than the real one
# will not transfer.
SERVO_KP = 40.0        # N.m per rad of error
SERVO_KV = 0.6         # N.m per rad/s, damping
SERVO_EFFORT = 2.45    # N.m, HX-35H running torque (props.xacro joint_effort)
SERVO_ARMATURE = 0.005 # kg.m^2, reflected inertia of the gearbox; keeps it stable

TIMESTEP = 0.002       # s, same as worlds/flat_ground.sdf


def find_xacro():
    """The robot's xacro file, wherever this checkout keeps it."""
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / "jethexa_sim" / "urdf" / "jethexa.urdf.xacro",        # repo clone
        Path.home() / "jethexa_ws" / "src" / "jethexa_sim" / "urdf" / "jethexa.urdf.xacro",  # docker
    ]
    try:
        from ament_index_python.packages import get_package_share_directory
        candidates.append(Path(get_package_share_directory("jethexa_sim")) / "urdf" / "jethexa.urdf.xacro")
    except Exception:
        pass
    for c in candidates:
        if c.is_file():
            return c
    sys.exit("cannot find jethexa.urdf.xacro; looked in:\n  " + "\n  ".join(map(str, candidates)))


def urdf_for_mujoco():
    """Expand the xacro and make the result digestible by MuJoCo."""
    try:
        urdf = subprocess.check_output(["xacro", str(find_xacro())], text=True)
    except FileNotFoundError:
        sys.exit("xacro not found - is ROS sourced? (open a new terminal, or: source /etc/profile.d/jethexa.sh)")

    # Gazebo-only sections. MuJoCo would ignore most of it, but plugins and
    # sensors referencing gz names are noise in the exported file.
    urdf = re.sub(r"<ros2_control\b.*?</ros2_control>", "", urdf, flags=re.S)
    urdf = re.sub(r"<gazebo\b.*?</gazebo>", "", urdf, flags=re.S)

    # base_footprint is a massless ROS convention frame on the ground. MuJoCo
    # needs the free-floating body to be a top-level body with mass, so drop it
    # and its fixed joint; base_link becomes the root.
    urdf = re.sub(r'<link name="base_footprint"\s*/>', "", urdf)
    urdf = re.sub(r'<joint\b[^>]*>(?:(?!</joint>).)*?<parent link="base_footprint"\s*/>.*?</joint>',
                  "", urdf, flags=re.S)

    # fusestatic=false keeps base_link (and the sensor links) as real bodies
    # instead of merging them into the world, which would bolt the robot down.
    urdf = re.sub(r"(<robot\b[^>]*>)",
                  r'\1<mujoco><compiler fusestatic="false" discardvisual="true" '
                  r'balanceinertia="true"/></mujoco>', urdf, count=1)
    return urdf


def build_spec():
    spec = mujoco.MjSpec.from_string(urdf_for_mujoco())
    spec.option.timestep = TIMESTEP
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST

    # Let the body move freely in the world.
    spec.body("base_link").add_freejoint(name="root")

    # Ground, plus a light and a checkerboard so the viewer is readable.
    tex = spec.add_texture(name="grid", type=mujoco.mjtTexture.mjTEXTURE_2D,
                           builtin=mujoco.mjtBuiltin.mjBUILTIN_CHECKER,
                           rgb1=[0.25, 0.3, 0.35], rgb2=[0.15, 0.2, 0.25],
                           width=256, height=256)
    mat = spec.add_material(name="grid", texrepeat=[20, 20], reflectance=0.1)
    mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = tex.name
    spec.worldbody.add_geom(name="floor", type=mujoco.mjtGeom.mjGEOM_PLANE,
                            size=[20, 20, 0.1], material="grid",
                            friction=[1.0, 0.005, 0.0001])
    spec.worldbody.add_light(pos=[0, 0, 3], dir=[0, 0, -1], type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL)

    for g in spec.geoms:
        if g.name and g.name.endswith("_foot_collision"):
            g.rgba = [0.9, 0.5, 0.1, 1]
    for g in spec.body("base_link").geoms:
        g.rgba = [0.2, 0.4, 0.8, 1]

    # One position servo per joint, in controller order.
    for name in JOINTS:
        spec.joint(name).armature = SERVO_ARMATURE
        act = spec.add_actuator(name=name, target=name, trntype=mujoco.mjtTrn.mjTRN_JOINT)
        act.set_to_position(kp=SERVO_KP, kv=SERVO_KV)
        act.forcelimited = mujoco.mjtLimited.mjLIMITED_TRUE
        act.forcerange = [-SERVO_EFFORT, SERVO_EFFORT]
        act.ctrllimited = mujoco.mjtLimited.mjLIMITED_TRUE
        act.ctrlrange = spec.joint(name).range
    return spec


def build_model():
    return build_spec().compile()


def standing_height(model):
    """Base height at which the feet just touch the floor in the HOME stance."""
    data = mujoco.MjData(model)
    for i, name in enumerate(JOINTS):
        data.qpos[model.joint(name).qposadr[0]] = HOME[i]
    data.qpos[2] = 0.0
    data.qpos[3:7] = [1, 0, 0, 0]
    mujoco.mj_kinematics(model, data)
    feet = [model.geom(f"{leg}_foot_collision").id for leg in LEGS]
    lowest = min(data.geom_xpos[g][2] - model.geom_size[g][0] for g in feet)
    return -lowest + 0.001


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export", metavar="FILE", help="write the MJCF to FILE")
    ap.add_argument("--view", action="store_true", help="open the MuJoCo viewer, robot holding HOME")
    args = ap.parse_args()

    spec = build_spec()
    model = spec.compile()
    print(f"bodies {model.nbody - 1}  joints {model.njnt}  actuators {model.nu}  "
          f"mass {model.body_subtreemass[model.body('base_link').id]:.2f} kg  "
          f"standing height {standing_height(model) * 1000:.1f} mm")
    if args.export:
        Path(args.export).write_text(spec.to_xml())
        print("wrote", args.export)
    if args.view:
        import mujoco.viewer
        data = mujoco.MjData(model)
        data.qpos[2] = standing_height(model)
        for i, name in enumerate(JOINTS):
            data.qpos[model.joint(name).qposadr[0]] = HOME[i]
        data.ctrl[:] = HOME
        mujoco.viewer.launch(model, data)


if __name__ == "__main__":
    main()
