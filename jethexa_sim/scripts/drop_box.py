#!/usr/bin/env python3
"""Drop a box into the running sim, from the terminal.

    ros2 run jethexa_sim drop_box.py                       # 10 cm crate onto the robot
    ros2 run jethexa_sim drop_box.py --mass 2              # a heavy one
    ros2 run jethexa_sim drop_box.py --x 0.3 --z 0.01 --size 0.6 0.4 0.02 --static
                                                           # a 2 cm step in front of it

Each call adds a new box (box_1, box_2, ...). Use --static for terrain the
robot should push against rather than knock over.
"""
import argparse
import subprocess
import sys
import time

SDF = """<sdf version="1.9"><model name="{name}"><static>{static}</static>
<link name="link">
  <inertial><mass>{mass}</mass><inertia>
    <ixx>{ixx}</ixx><iyy>{iyy}</iyy><izz>{izz}</izz>
  </inertia></inertial>
  <collision name="collision"><geometry><box><size>{sx} {sy} {sz}</size></box></geometry></collision>
  <visual name="visual"><geometry><box><size>{sx} {sy} {sz}</size></box></geometry>
    <material><diffuse>{color} 1</diffuse><ambient>{color} 1</ambient></material></visual>
</link></model></sdf>"""


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", help="model name (default: box_<timestamp>)")
    p.add_argument("--x", type=float, default=0.0)
    p.add_argument("--y", type=float, default=0.0)
    p.add_argument("--z", type=float, default=0.6, help="drop height, m (default 0.6)")
    p.add_argument("--size", type=float, nargs=3, default=[0.1, 0.1, 0.1],
                   metavar=("X", "Y", "Z"), help="metres (default 0.1 0.1 0.1)")
    p.add_argument("--mass", type=float, default=0.3, help="kg (default 0.3)")
    p.add_argument("--static", action="store_true", help="fixed in place, like terrain")
    args = p.parse_args(sys.argv[1:] if "--ros-args" not in sys.argv
                        else sys.argv[1:sys.argv.index("--ros-args")])

    sx, sy, sz = args.size
    m = args.mass
    sdf = SDF.format(
        name=args.name or "box_%d" % (time.time() * 1000 % 1e6),
        static="true" if args.static else "false",
        mass=m, sx=sx, sy=sy, sz=sz,
        # solid cuboid: I = m/12 (b^2 + c^2)
        ixx=m / 12 * (sy * sy + sz * sz),
        iyy=m / 12 * (sx * sx + sz * sz),
        izz=m / 12 * (sx * sx + sy * sy),
        color="0.5 0.5 0.5" if args.static else "0.9 0.4 0.1",
    )
    cmd = ["ros2", "run", "ros_gz_sim", "create", "-string", sdf,
           "-x", str(args.x), "-y", str(args.y), "-z", str(args.z)]
    if args.name:
        cmd += ["-name", args.name]
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
