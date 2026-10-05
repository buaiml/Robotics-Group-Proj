# Week 3 demo: what we have, and what's missing (about 8 minutes)

A live tour of the sim, ending on the question the group spends this week on:
*how do we actually make it walk?* Each part lines up with one of the
[Week 3 research areas](../tasks_week_3.md), so people can see what they'd be
picking.

Every command here has been run on the project machine. The whole thing
takes about 8 minutes, and the IK demo is 54 seconds of it.

---

## Before the meeting (5 min)

1. Open **three** terminals, each with `wsl -d jethexa`. Make the font big
   (Ctrl + scroll) — people at the back need to read it.
2. Terminal 1: start the sim, and leave it running.
   ```bash
   ros2 launch jethexa_sim jethexa_gazebo.launch.py
   ```
3. When the robot has settled, check the bottom-right corner of Gazebo:
   **real-time factor should read about 100%**. If it shows a few percent, see
   [If something goes wrong](#if-something-goes-wrong).
4. Do a full dry run of the steps below, then restart the sim (Ctrl+C in
   terminal 1, launch again) so you start with no boxes lying around.

---

## 1. "This is our robot" — 1 min · *Simulation*

Gazebo on screen.

- Hit **pause**, then **step** a few times. "The sim is a loop. Every step,
  physics moves the world forward 2 ms. Right now it's running at real time —
  that number in the corner."
- Rotate the camera round the robot. "Eighteen motors, three per leg. A
  lidar on the mast, a depth camera on the front. Same as the real one."
- Hit **play** again.

## 2. "It's a ROS system" — 1.5 min · *ROS 2*

Terminal 2:

```bash
ros2 topic echo /joint_states --once
```

"Eighteen joint angles, straight out of the simulator. Anything in our
project can read these — a controller, a recorder, a neural network."

```bash
rqt_graph
```

"Every box is a program; every arrow is a topic. Gazebo on one side, ROS on
the other, and the bridge in the middle. When we move to the real robot, the
Gazebo side gets swapped for the actual hardware and everything else stays."

Close `rqt_graph`.

## 3. "We can control it" — 3 min · *Control and gait*

Terminal 2:

```bash
ros2 run jethexa_sim ik_demo.py
```

It narrates itself in six parts. What to say:

- **height:** "The feet stay put and the body rises. Nobody typed in joint
  angles — inverse kinematics works out all eighteen, fifty times a second."
- **sway / twist:** "Same trick, but now the body tilts and turns. Same
  question each time: where is each foot, so what must each joint be?"
- **lean:** "The body circles over its feet. It doesn't fall because its
  centre of mass never leaves the area between the feet."
- **wave:** "Five feet down, one waving. A hexapod can keep three or more
  feet on the ground the whole time it walks — that's the big advantage of six
  legs over four."
- Point at the `tracking` lines: "Commanded versus where the joints actually
  went — about one degree off. The motors keep up."

## 4. "Let's break it" — 1 min · *Simulation / Perception*

Terminal 3:

```bash
ros2 run jethexa_sim drop_box.py
ros2 run jethexa_sim drop_box.py --mass 2
ros2 run jethexa_sim drop_box.py --x 0.3 --z 0.01 --size 0.3 0.6 0.02 --static
```

The first two drop crates on it; the third puts a 2 cm step in front of it.

"It held the weight, but notice it didn't *react*. It has no idea there's a
crate on it, and no idea there's a step in front of it. Nothing we showed you
looks at the sensors."

## 5. "So what's missing" — 1.5 min · *the week's question*

"Everything you just saw was hand-written maths. It can stand, lean and wave
— but it **can't walk**, it can't **feel** the ground, and it can't **see**
where it's going. Getting it from one building to the next needs all three.

There are a lot of ways to do that, and we haven't picked one. That's this
week."

Put up [tasks_week_3.md](../tasks_week_3.md) and go through the areas:
simulation, ROS 2, control and gait, learning, perception, navigation,
hardware. Then the five decisions at the bottom — those are what everyone's
research feeds into next week.

---

## If something goes wrong

**Real-time factor is a few percent, and everything moves in slow motion.**
WSL is drawing on the laptop's built-in graphics instead of the NVIDIA card.
In a terminal:

```bash
printenv MESA_D3D12_DEFAULT_ADAPTER_NAME
```

It should print `NVIDIA`. If it prints nothing, close all the terminals and
open fresh ones. Still nothing: start the sim with it set by hand:

```bash
MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA ros2 launch jethexa_sim jethexa_gazebo.launch.py
```

The IK demo times itself by sim time, so a slow sim makes it slow but never
wrong.

**Gazebo won't close, or a second copy is running.**

```bash
pkill -f '[g]z sim'
```

**`ik_demo.py` says it is waiting for the controller.** The sim hasn't
finished starting. Give it ten more seconds.

**Nothing works.** Run the sim without the window and narrate the terminal
output instead — the demo prints everything it's doing:

```bash
ros2 launch jethexa_sim jethexa_gazebo.launch.py gui:=false
```
