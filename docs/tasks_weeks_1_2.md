# Weeks 1 and 2

One task per person per week, about 1.5 hours each.

Week 1 is the same for everyone. For Week 2, pick whichever area below you
actually find interesting — that matters more than balancing the areas, and
nothing here is on the critical path yet. If two of you land on the same area,
pair up and take a task each: the tasks in each area overlap on purpose, so you
have something to talk about. Whoever is newer to the topic presents it at the
meeting.

Areas that nobody picks just wait for Week 3.

---

## Week 1 — everyone

**Get the simulator running on your own machine.** Not one person for the group:
everyone, individually. Follow [setup.md](setup.md), build the workspace, launch
the sim, run `stand.py`, and watch the robot stand up. [commands.md](commands.md)
has everything you'll need to type.

It matters that all eight of you do this. If one person sets up everybody's
environment, seven people never learn how their tools fit together, and that
person becomes a bottleneck for fourteen weeks.

Then two things:

1. **Fix the instructions.** Wherever [setup.md](setup.md) was wrong, unclear or
   incomplete on your machine, PR a fix. By the eighth person it should be
   flawless.
2. **Break it a bit.** Change the stance angles in `stand.py`, drop the robot
   from a metre up, watch the joint numbers go by. File an issue for anything
   that looks wrong. You don't have to fix any of it.

Done early? Start on your Week 2 area.

---

## Week 2 — pick an area

### The robot model

Everything about our robot's shape is currently a guess taken from a product
photo. The real numbers exist — they're on the robot.

- **Get the vendor's URDF off the robot.** Hiwonder ships an accurate URDF with
  meshes as part of the robot's own ROS packages. Find it, copy it off, and
  report what's in it: link lengths, joint origins, masses, inertias, mesh
  files. This is the task that makes our sim real, and it's a file transfer
  rather than an afternoon with calipers.
- **Fold those numbers into our model.** Replace the placeholders in
  `urdf/props.xacro`. Keep our Harmonic and `ros2_control` wiring — we only want
  their geometry. Watch out: masses in vendor URDFs are often approximate, so
  put the robot on a scale once and check the total. Then run
  `scripts/check_model.py` and see whether the robot still stands.

### Legs and gait

- **Map the joints.** For each of the 18, command a small movement and write down
  which way the robot actually moves. Positive femur angle — up or down? Sign
  errors here waste days later. Produce a table plus a script that sweeps one
  joint on demand.
- **Write an open-loop tripod gait.** A node that walks the robot by playing
  scripted joint angles — no learning, no feedback, just sine waves or keyframes
  to `/joint_group_position_controller/commands`. It will probably look
  terrible. That's the point: it's the baseline the learned policy has to beat,
  and it tells us whether the model can walk at all.
- **Plot one leg's reachable workspace.** Sweep the three joints through their
  limits, plot every foot position you can reach. This tells us the real stride
  length and how tall a kerb the robot could conceivably step onto.

### Sensing

- **Get RViz onto the live data.** One config showing the robot model, the TF
  tree, the lidar scan and the depth point cloud together. Commit it to
  `config/`.
- **Record a bag and read it back.** Record while the robot stands and the
  sensors run, then open it: what topics, what rates, how many MB per minute.
  Write down the commands. We'll record a lot of these.
- **Work out what the robot can see of a kerb.** The lidar is mast-mounted and
  2D, so it cannot see a step at all — the depth camera is the only source. Put
  a box in the world and find out what the depth image actually gives you at
  10, 20 and 30 mm. This shapes the whole terrain approach.

### Learning

Groundwork. The real RL work starts once the teaching sessions catch up.

- **Read two papers and report back.** Rudin 2021 ("Learning to Walk in
  Minutes") and Lee 2020 (quadrupeds over rough terrain). Skim, don't study.
  Half a page in plain language: what did they feed the robot, what did they
  reward it for, how long did training take.
- **Work out our training budget.** Run `gz topic -e -t /stats -n 1` to get the
  real-time factor, then do the arithmetic: how long would 10⁸ steps take in
  Gazebo? Compare against what MuJoCo claims. Write down the numbers. We've
  asserted Gazebo is too slow to train in — check whether that's actually true
  instead of taking our word for it.
- **Draft what the policy sees and does.** For every input you'd want to give
  it, ask whether the real robot can measure that, how fast, and how noisily.
  [jethexa_hardware.md](jethexa_hardware.md) is the constraint list. Bring it to
  the meeting to be pulled apart.

### Worlds and terrain

- **Build a terrain test world.** An SDF world with flat ground, a gentle slope,
  and steps of 10, 20 and 30 mm. This becomes the rig everything gets tested on.
  Copy `worlds/flat_ground.sdf` and go from there.
- **Walk the route** (better with two people, outside). Measure and photograph
  the crossing between the two buildings: crosswalk width, kerb heights, ramp
  slopes, pavement and road width. Into `docs/route/` with a sketch map, plus
  the three things you think will stop a 12 cm robot.

### The real robot

- **Bring it up, and write down how.** Boot it, connect, run a vendor demo,
  drive it around, record some lidar and camera data. Recipe into
  `docs/robot_bringup.md` so nobody has to rediscover it. **Back up the SD card
  before you change anything** — it's the only copy of the vendor software.
- **Time the servo bus.** All 18 servos share one 115200-baud serial bus, which
  we estimate caps a command-and-read cycle near 25–30 Hz. That would undercut
  the 50 Hz control loop we've been assuming. Measure it: how fast can you
  actually command 18 joints and read them back?

### Tooling and framing

- **Make the checks run automatically.** `scripts/check_model.py` catches silent
  model breakage, but only if somebody remembers to run it. Wire it into CI on
  PRs, or a pre-commit hook, plus one command that builds and checks.
- **Write down what we're actually trying to do.** "Walk to the other building"
  isn't testable. How fast? How often may it fall? What terrain? What time
  limit? May a human touch it mid-run? One page in
  `docs/problem_statement.md`, and expect argument at the meeting.
- **Build a glossary.** URDF, link, joint, DoF, topic, TF, policy, reward, gait —
  one plain sentence each in `docs/glossary.md`. You'll learn the vocabulary by
  writing it, and everyone else gets to stop nodding along.

---

## After two weeks

All eight of you can launch the sim unaided, and the model is built from the
robot's real geometry rather than guesses. Beyond that it depends what people
picked — but we should have at least one of: something walking open-loop, the
sensors visible in RViz, or a written problem statement we agree on.

## Coming in Weeks 3 and 4

Setting up the MuJoCo training simulator, surveying the RL tools and model zoos,
and settling the observation and action spaces. Those need the teaching sessions
on simulators and reinforcement learning first.
