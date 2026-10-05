#!/usr/bin/env python3
"""Check the robot model survives URDF -> SDF conversion intact.

    python3 scripts/check_model.py [path/to/jethexa.urdf.xacro]

Why this exists: sdformat renames collisions during conversion (it prefixes
every one with <link>_fixed_joint_lump__ and appends _collision). A contact
sensor whose <collision> reference does not match the emitted name still loads
without complaint and simply never fires. That is a silent failure, and it cost
an afternoon to find once already.

Run this after touching collisions, sensors or the joint structure.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_JOINTS = 18


def fail(msg: str) -> None:
    print(f"FAIL  {msg}")
    sys.exit(1)


def main() -> None:
    here = Path(__file__).resolve().parent
    xacro_path = Path(sys.argv[1]) if len(sys.argv) > 1 else here.parent / "urdf" / "jethexa.urdf.xacro"
    if not xacro_path.is_file():
        fail(f"no such file: {xacro_path}")

    for tool in ("xacro", "gz"):
        if shutil.which(tool) is None:
            fail(f"{tool} not on PATH - source your ROS 2 and Gazebo environment first")

    urdf_text = ""
    with tempfile.TemporaryDirectory() as tmp:
        urdf = Path(tmp) / "robot.urdf"
        proc = subprocess.run(["xacro", str(xacro_path)], capture_output=True, text=True)
        if proc.returncode != 0:
            fail(f"xacro failed:\n{proc.stderr.strip()}")
        urdf_text = proc.stdout
        urdf.write_text(urdf_text)

        proc = subprocess.run(["gz", "sdf", "-p", str(urdf)], capture_output=True, text=True)
        if not proc.stdout.strip():
            fail(f"gz sdf conversion produced nothing:\n{proc.stderr.strip()}")
        sdf = proc.stdout

    collisions = set(re.findall(r"<collision name='([^']+)'", sdf))
    contact_refs = re.findall(r"<contact>\s*<collision>([^<]+)</collision>", sdf)
    revolute = re.findall(r"<joint name='([^']+)' type='revolute'", sdf)
    sensors = re.findall(r"<sensor name='([^']+)' type='([^']+)'", sdf)

    print(f"links      {len(re.findall(r'<link name=', sdf))}")
    print(f"collisions {len(collisions)}")
    print(f"revolute   {len(revolute)}")
    print(f"sensors    {len(sensors)}")

    # 1. any contact sensor must reference a collision that actually exists.
    #    There are none right now (see urdf/leg.xacro), but if someone adds
    #    them this catches the silent-failure mode.
    dangling = [ref for ref in contact_refs if ref not in collisions]
    if dangling:
        print("\nContact sensors reference collisions that do not exist:")
        for ref in dangling:
            print(f"  missing: {ref}")
        print("\nAvailable collision names:")
        for name in sorted(collisions):
            print(f"  {name}")
        fail(f"{len(dangling)} dangling contact reference(s) - these sensors would never fire")

    # 2. the actuated joints must all survive
    if len(revolute) != EXPECTED_JOINTS:
        fail(f"expected {EXPECTED_JOINTS} revolute joints, found {len(revolute)}: {sorted(revolute)}")

    # 3. the sensor payload must be present
    by_type = {}
    for name, kind in sensors:
        by_type.setdefault(kind, []).append(name)
    for kind in ("gpu_lidar", "camera", "depth_camera", "imu"):
        if kind not in by_type:
            fail(f"missing a sensor of type {kind}")

    # 4. ros2_control has to be wired to the gz system, not the Classic one.
    #    Checked against the URDF: <ros2_control> is not an SDF element, so the
    #    conversion drops it.
    if "gz_ros2_control/GazeboSimSystem" not in urdf_text:
        fail("ros2_control is not using gz_ros2_control/GazeboSimSystem")
    if "gazebo_ros2_control" in urdf_text or "libgazebo_ros" in urdf_text:
        fail("model still references Gazebo Classic plugins")
    if urdf_text.count("<joint name=") < EXPECTED_JOINTS:
        fail("ros2_control block is missing joint interfaces")

    print(
        f"\nOK  {EXPECTED_JOINTS} joints, sensor payload intact, "
        f"{len(contact_refs)} contact sensor(s), no dangling collision refs"
    )


if __name__ == "__main__":
    main()
