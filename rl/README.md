# RL proof of concept

A first, deliberately simple attempt at teaching the JetHexa to walk with
reinforcement learning: MuJoCo for the physics, Gymnasium for the environment,
Stable-Baselines3's PPO for the learning.

It exists to show the **whole loop working end to end**: robot model →
environment → training → a policy you can watch. Every number in it is a first
guess. Replacing those guesses with good ones is the actual project, and the
Week 3 research decides whether we keep any of these tools at all.

## Run it

Inside WSL, run these from the repo root. In the Docker container `rl/` is
mounted at `~/rl`, so run them from `~` and they work as written.

Check the environment works, and how fast it runs (10 seconds):

```bash
python3 rl/train.py --check
```

Train. The default 3 million steps took about 13 minutes on the project laptop
(32 cores, 16 robots in parallel); expect longer with fewer cores. `Ctrl+C`
stops early and still saves:

```bash
python3 rl/train.py
```

Watch the result (opens a MuJoCo window):

```bash
python3 rl/play.py
```

Compare with doing nothing:

```bash
python3 rl/play.py --home
```

Look at the robot MuJoCo is simulating, or export it to read:

```bash
python3 rl/jethexa_mujoco.py --view
```

```bash
python3 rl/jethexa_mujoco.py --export /tmp/jethexa.xml
```

If `import torch` fails, your environment predates this folder. Install the
packages without re-running the whole setup:

```bash
pip install --user -r rl/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

## What's in here

| File | What it does |
|---|---|
| `jethexa_mujoco.py` | Builds the MuJoCo robot from the **same** xacro Gazebo uses, adds servos and a floor |
| `jethexa_env.py` | The RL problem: what the policy observes, what it controls, what it's rewarded for |
| `train.py` | Runs PPO with 16 robots practising in parallel, saves to `rl/runs/` |
| `play.py` | Loads a trained policy and shows it walking |

## Reading the training output

```
steps 2,023,424  reward   202.7  length   500  distance  +4.94 m  (3,670 steps/s)
...
without training noise: +5.56 m per 20 s episode (+0.278 m/s)
```

- **steps** — how much practice so far.
- **reward** — the number PPO is maximising. Should climb.
- **length** — steps per episode before falling. 500 means it lasted the full
  20 seconds.
- **distance** — metres forward per episode. This is the one we actually care
  about, and it is *not* the same as reward: a policy can score well by
  standing very still and very level. Watch for that.
- **without training noise** — printed once at the end, and the number that
  counts. During training PPO adds random noise to every action; this is the
  policy on its own. If it's far below the training distance, the policy never
  learned to walk (see below).

## What went wrong while building this

Three failed versions, each a classic. All three looked like progress in some
column of the training output.

1. **It learned to fall over on purpose.** Episode length *dropped* as training
   went on. Each step cost more in penalties than staying up earned, so the
   best strategy was to end the episode quickly. Fixed by raising the "alive"
   reward above the penalties, and by not counting a small crouch as a fall.
2. **It "walked" 3 m per episode in training and 0.07 m on its own.** The
   policy's decisions barely changed from step to step; the random training
   noise was shaking it forward. Fixed by giving it a clock to step in time
   with (`GAIT_HZ`), starting with less noise, and penalising jerky actions
   harder.
3. **A version with smoother noise (gSDE) learned to stand still.** Reward
   climbed steadily, distance stayed at 0.02 m: standing earns the alive
   bonus with no risk. We dropped it rather than tune it, but it's worth
   understanding why it happened.

The working version walks about 5 m in 20 seconds: a real gait, with feet
lifting up to 5 cm, joints within the servo's speed limit, and the body
tilting under 7°.

## Decisions baked in, and why

- **Observations are only what the real robot can measure**: IMU (which way is
  down, how fast it's rotating), servo positions, and the policy's own last
  action. Most simulation examples also give the policy the body's true speed,
  its height, and whether each foot is touching the ground. Our robot can't
  measure any of those, so a policy that relied on them would never run on it.
- **25 Hz control**, not the 50 Hz most papers use, because of the servo bus
  limit in [jethexa_hardware.md](../docs/jethexa_hardware.md).
- **Actions are offsets from the standing pose**, ±0.5 rad, so a policy that
  outputs zeros simply stands.
- **A 2×128 network**, small enough for the Jetson Nano.

## Known gaps — good starting tasks

- **The servo model is a guess.** `SERVO_KP` in `jethexa_mujoco.py` sets how
  stiff the joints are. The real HX-35H has never been measured. A policy
  trained on the wrong stiffness will not transfer.
- **No noise or randomisation.** The simulated robot is perfect and identical
  every time. Real sensors are noisy and the real robot's mass and friction are
  uncertain. Adding that ("domain randomisation") is how sim-to-real works.
- **Flat ground only, walk forward only.** No steering, no slopes, no kerbs.
- **Never been run in Gazebo or on the robot.** The joint order matches the
  Gazebo controller, so the next step is a ROS node that loads a policy and
  publishes to `/joint_group_position_controller/commands`.
- **It runs the servos flat out.** Over half the time at least one servo is at
  its torque limit. The real ones would overheat. Penalise effort harder, or
  find out the real thermal limits.
- **It walks at 0.28 m/s, almost double the target.** The reward stops paying
  above `TARGET_SPEED` but doesn't discourage going faster. Is the real robot
  even capable of that?
- **The reward is hand-tuned on one run.** Change a weight in `_reward()`,
  retrain, and compare. That is most of what RL work looks like day to day.
