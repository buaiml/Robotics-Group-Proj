"""Gymnasium environment: teach the JetHexa to walk forward on flat ground.

This is a PROOF OF CONCEPT, built to show the whole loop working end to end -
model, environment, training, playback. Every number in it is a first guess,
and most of the interesting work this semester is replacing those guesses with
better ones. Places to start are marked "QUESTION:".

The three things that define an RL problem are all in this file:

    observation  what the policy is told each step       _observe()
    action       what the policy controls                step(), ACTION_SCALE
    reward       what counts as doing well               _reward()
"""
import gymnasium as gym
import mujoco
import numpy as np

from jethexa_mujoco import HOME, JOINTS, build_model, standing_height

# --- control ---------------------------------------------------------------
# 25 Hz, not the 50 Hz most papers use: all 18 servos share one serial bus,
# which we estimate tops out around 25-30 full read-and-command cycles a second
# (jethexa_hardware.md). A policy trained to act at 50 Hz may not survive on the
# robot. QUESTION: the real-robot group is measuring this - update when they do.
CONTROL_HZ = 25

# The policy outputs 18 numbers in [-1, 1]. Each becomes a joint target of
# HOME + ACTION_SCALE * action. Smaller = safer but less able to take big steps.
ACTION_SCALE = 0.5      # rad

EPISODE_SECONDS = 20
TARGET_SPEED = 0.15     # m/s. Fast enough to cross a road in good time? QUESTION.
# A clock the policy can see: sin and cos of a phase that goes round GAIT_HZ
# times a second. Without it, the first version of this file "walked" only
# thanks to the random noise PPO adds while training: its actual decisions
# barely changed over time, and with the noise switched off it stood still.
# Walking is rhythmic; a rhythm to lock onto makes a real gait easy to find.
GAIT_HZ = 1.5
BELLY_HEIGHT = 0.026    # m, body centre height when the belly touches the floor


class JetHexaWalkEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self):
        self.model = build_model()
        self.data = mujoco.MjData(self.model)
        self.frame_skip = round(1.0 / (CONTROL_HZ * self.model.opt.timestep))
        self.dt = self.frame_skip * self.model.opt.timestep
        self.max_steps = int(EPISODE_SECONDS * CONTROL_HZ)

        j = [self.model.joint(n) for n in JOINTS]
        self.qadr = np.array([x.qposadr[0] for x in j])
        self.vadr = np.array([x.dofadr[0] for x in j])
        self.lo = np.array([x.range[0] for x in j])
        self.hi = np.array([x.range[1] for x in j])
        self.base = self.model.body("base_link").id
        self.start_height = standing_height(self.model)

        self.action_space = gym.spaces.Box(-1.0, 1.0, (len(JOINTS),), np.float32)
        obs_size = 3 + 3 + 18 + 18 + 18 + 2
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, (obs_size,), np.float32)

    # --- observation -------------------------------------------------------
    # Only things the REAL robot can measure. That rules out what most sim
    # examples use for free: the body's true velocity, its height above the
    # ground, and foot contact (our robot has no foot sensors).
    def _observe(self):
        d = self.data
        R = d.xmat[self.base].reshape(3, 3)
        gravity = R.T @ np.array([0.0, 0.0, -1.0])  # IMU: which way is down
        gyro = d.qvel[3:6]                           # IMU: body rotation rate
        joint_pos = d.qpos[self.qadr] - HOME         # servos report position
        # The servos do NOT report velocity; on the robot this would have to be
        # estimated from successive positions. QUESTION: does that noise hurt?
        joint_vel = d.qvel[self.vadr]
        phase = 2 * np.pi * GAIT_HZ * self.steps * self.dt
        return np.concatenate([
            gravity, 0.25 * gyro, joint_pos, 0.05 * joint_vel, self.prev_action,
            [np.sin(phase), np.cos(phase)],
        ]).astype(np.float32)

    # --- reward ------------------------------------------------------------
    def _reward(self, vx, vy, action):
        d = self.data
        R = d.xmat[self.base].reshape(3, 3)
        tilt = 1.0 - R[2, 2]                         # 0 when level
        terms = {
            "forward": 2.0 * min(vx, TARGET_SPEED),  # go forward, up to target
            # Paid every step it stays up. It must outweigh the penalties below,
            # or the best strategy is to fall over at once and stop paying them -
            # the first version of this file learned exactly that.
            "alive": 0.25,
            "sideways": -1.0 * vy ** 2,              # walk straight
            "turning": -0.05 * d.qvel[5] ** 2,
            "tilt": -0.5 * tilt,                     # stay level
            # Smoothness. Also what stops the policy "walking" by vibrating: at
            # -0.01 a shaky shuffle paid better than a real gait, at -0.05 it
            # doesn't.
            "jerk": -0.05 * np.sum((action - self.prev_action) ** 2),
            "effort": -1e-3 * np.sum(d.actuator_force ** 2),           # battery
        }
        return sum(terms.values()), terms

    # --- gym API -----------------------------------------------------------
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        d = self.data
        mujoco.mj_resetData(self.model, d)
        d.qpos[2] = self.start_height
        d.qpos[3:7] = [1, 0, 0, 0]
        # A little randomness, so the policy cannot memorise one exact start.
        d.qpos[self.qadr] = HOME + self.np_random.uniform(-0.05, 0.05, len(JOINTS))
        d.ctrl[:] = HOME
        # Let it settle onto its feet before the policy takes over.
        mujoco.mj_step(self.model, d, nstep=100)
        self.prev_action = np.zeros(len(JOINTS))
        self.steps = 0
        self.x_start = d.qpos[0]
        return self._observe(), {}

    def step(self, action):
        action = np.clip(np.asarray(action, dtype=np.float64), -1.0, 1.0)
        d = self.data
        d.ctrl[:] = np.clip(HOME + ACTION_SCALE * action, self.lo, self.hi)

        x0, y0 = d.qpos[0], d.qpos[1]
        mujoco.mj_step(self.model, d, nstep=self.frame_skip)
        vx = (d.qpos[0] - x0) / self.dt
        vy = (d.qpos[1] - y0) / self.dt

        reward, terms = self._reward(vx, vy, action)
        self.prev_action = action
        self.steps += 1

        # Fallen: belly on the floor, or tipped past 60 degrees. The body is
        # 50 mm thick and stands only ~48 mm up, so "belly on the floor" means
        # the body centre is within ~26 mm of it - not much room for crouching.
        upright = d.xmat[self.base].reshape(3, 3)[2, 2]
        terminated = bool(d.qpos[2] < BELLY_HEIGHT or upright < 0.5)
        truncated = self.steps >= self.max_steps
        info = {"distance": d.qpos[0] - self.x_start, **{"r_" + k: v for k, v in terms.items()}}
        return self._observe(), reward, terminated, truncated, info
