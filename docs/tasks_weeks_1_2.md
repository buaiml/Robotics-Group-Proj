# Weeks 1 and 2

Pick one task per week, about 1.5 hours each. If this is your first robotics
project, take one of the earlier ones in the list, they need the least
background. Ask in the channel if you get stuck for more than 20 minutes,
that's normal and not a sign you picked wrong.

## Week 1

1. **Get the simulator running** (2 people) — Build and run `jethexa_sim` on a clean Ubuntu 22.04 machine, then write the steps down so everyone else can copy them. This is the fiddliest task here, so take it if you're comfortable with Linux and the terminal. Start it first, everyone else is waiting on it.

2. **Break the simulator** — Run it, run `stand.py`, change the stance angles, drop the robot from a height, watch the joint numbers. File an issue for anything that looks wrong. You don't need to fix any of it.

3. **Measure the robot** (2 people, needs the robot) — Ruler, calipers, scale. Leg segment lengths, where the legs attach to the body and at what angle, body size, standing height, mass, where the sensors are, how far each joint can rotate. Write it in `docs/measurements.md`. Every number in our model is currently a guess, so this is more important than it sounds.

4. **Make one leg move** — Write a small script that moves a single joint back and forth, then one that makes a leg wave. You're copying the pattern in `scripts/stand.py`. Good first task if you've never touched ROS.

5. **Walk the route** (2 people) — Take a tape measure and a phone to the route between the two buildings. Measure the crosswalk, the kerb heights, the ramp slopes, the pavement and road width. Photograph anything in the way. Put it in `docs/route/` with a sketch map, and list the three things you think will stop the robot. It's about 12 cm tall.

## Week 2

1. **Put the real numbers in the model** (needs W1.3) — Replace the placeholder values in `urdf/props.xacro` with the measured ones, run the sim, see what changed.

2. **Make it stand properly** (needs W1.2) — The robot sinks and slides. Tune the contact settings (friction, stiffness, damping, timestep) until it holds still for 30 seconds. Mostly changing a number and rerunning, but write down what each one did.

3. **Forward kinematics of one leg** — Work out where the foot ends up given the three joint angles, then check your answer against the simulator. Some trigonometry and a short script. If you want to go further, try the reverse (foot position in, angles out) and mention it at the meeting.

4. **Get the real robot running** (2 people, needs the robot) — Boot it, connect to it, run one of the demos it came with, drive it around, record some lidar and camera data. Write down how you did it in `docs/robot_bringup.md` so the next person doesn't have to work it out again.

5. **Read about how robots learn to walk** — Rudin 2021 ("Learning to Walk in Minutes") and Lee 2020 (quadrupeds on rough terrain). Skim, don't study. Half a page in plain language: what did they feed the robot, what did they reward it for, how long did training take. Bring questions to the meeting rather than pretending it all made sense.

6. **Build a glossary** — Collect the terms flying around this project (URDF, link, joint, DoF, topic, TF, policy, reward, gait) and write one plain sentence each in `docs/glossary.md`. Genuinely useful for everyone, and you'll learn the vocabulary by writing it.

7. **Write down what we're actually trying to do** — "Walk to the other building" isn't testable. How fast? How often is it allowed to fall? What terrain? What time limit? Can a human touch it mid-run? One page in `docs/problem_statement.md`, and expect people to argue with it at the meeting.

## After two weeks

Anyone can launch the sim, the robot stands still, and the model matches the
real robot. Somebody has made a leg move on purpose, somebody has driven the real
robot, and we agree on what we're building.

## Coming in Weeks 3 and 4, not now

Setting up the training simulator, surveying the RL tools and model zoos, bench
testing the servos, and deciding what the policy sees and does. These need the
teaching sessions on simulators and reinforcement learning first.
