#!/usr/bin/env python3
"""Train a walking policy for the JetHexa in MuJoCo, with PPO.

    python3 rl/train.py --check            # 10 s: does the env work, how fast is it
    python3 rl/train.py                    # train (default 3M steps, ~15-20 min)
    python3 rl/train.py --steps 500000     # a quick look
    python3 rl/play.py                     # watch the latest run

Each run is saved to rl/runs/<date-time>/ (not committed to git). The progress
line printed during training reads:

    steps     how many control steps the policy has practised so far
    reward    average total reward per episode - should climb
    length    average episode length in steps; 500 = never fell over
    distance  average metres walked forward per 20 s episode - the real goal
"""
import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np

from jethexa_env import JetHexaWalkEnv


def check():
    from gymnasium.utils.env_checker import check_env
    env = JetHexaWalkEnv()
    check_env(env.unwrapped, skip_render_check=True)
    print(f"env ok: observation {env.observation_space.shape[0]} numbers, "
          f"action {env.action_space.shape[0]} numbers, {1 / env.dt:.0f} Hz control")

    obs, _ = env.reset(seed=0)
    t, n, ret, done = time.time(), 0, 0.0, False
    while not done:
        obs, r, term, trunc, info = env.step(env.action_space.sample())
        ret, n, done = ret + r, n + 1, term or trunc
    rate = n / (time.time() - t)
    print(f"random actions: {n} steps ({'fell' if term else 'survived'}), "
          f"reward {ret:.1f}, distance {info['distance']:+.3f} m")
    print(f"speed: {rate:.0f} steps/s on one core = {rate * env.dt:.0f}x real time")


def evaluate(model, out):
    """The real test: the policy's own decisions, with the training noise off.

    The distance printed during training includes the random exploration noise
    PPO adds to every action. A policy can look like it walks only because
    that noise shakes it forward. If this number is far below the training
    one, that is what happened.
    """
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    venv = VecNormalize.load(str(out / "vecnormalize.pkl"), DummyVecEnv([JetHexaWalkEnv]))
    venv.training, venv.norm_reward = False, False
    obs, done, = venv.reset(), [False]
    dist = []
    while len(dist) < 3:
        obs, _, done, info = venv.step(model.predict(obs, deterministic=True)[0])
        if done[0]:
            dist.append(info[0]["distance"])
    print(f"without training noise: {np.mean(dist):+.2f} m per 20 s episode "
          f"({np.mean(dist) / 20:+.3f} m/s)")


def train(args):
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import SubprocVecEnv, VecNormalize

    # One thread. The network is tiny; with more, PyTorch spends its time
    # coordinating threads instead of computing (measured: several times slower).
    torch.set_num_threads(1)
    out = Path(args.out) / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True)

    # Several copies of the robot practising at once, each in its own process.
    env = make_vec_env(JetHexaWalkEnv, n_envs=args.envs, seed=args.seed,
                       vec_env_cls=SubprocVecEnv,
                       monitor_kwargs={"info_keywords": ("distance",)})
    # Rescale observations and rewards to roughly unit size. PPO is much happier
    # with that, but it means these statistics must be saved with the policy.
    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.0)

    model = PPO(
        "MlpPolicy", env,
        # Two hidden layers of 128: small enough for the Jetson Nano to run at
        # 25 Hz without trouble (semester_plan.md).
        # log_std_init sets how much random noise PPO adds to actions at the
        # start (exp(-1.6) = 0.2). Much more, and the policy can learn to rely
        # on the noise shaking it forward instead of learning to step.
        policy_kwargs=dict(net_arch=[128, 128], log_std_init=-1.6),
        n_steps=256, batch_size=2048, n_epochs=5,
        learning_rate=3e-4, gamma=0.99, gae_lambda=0.95, clip_range=0.2,
        seed=args.seed, device="cpu", verbose=0,
    )

    class Progress(BaseCallback):
        def __init__(self):
            super().__init__()
            self.t0, self.last = time.time(), 0

        def _on_step(self):
            return True

        def _on_rollout_end(self):
            if self.num_timesteps - self.last < 50_000 or not self.model.ep_info_buffer:
                return
            self.last = self.num_timesteps
            eps = list(self.model.ep_info_buffer)
            fps = self.num_timesteps / (time.time() - self.t0)
            print(f"steps {self.num_timesteps:>9,}  "
                  f"reward {np.mean([e['r'] for e in eps]):7.1f}  "
                  f"length {np.mean([e['l'] for e in eps]):5.0f}  "
                  f"distance {np.mean([e['distance'] for e in eps]):+6.2f} m  "
                  f"({fps:,.0f} steps/s)", flush=True)

    print(f"training for {args.steps:,} steps with {args.envs} parallel robots -> {out}", flush=True)
    try:
        model.learn(total_timesteps=args.steps, callback=Progress())
    except KeyboardInterrupt:
        print("stopped early - saving what we have")
    model.save(out / "model.zip")
    env.save(str(out / "vecnormalize.pkl"))
    env.close()
    evaluate(model, out)
    print(f"saved {out}\nwatch it:  python3 rl/play.py {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="test the environment and exit")
    ap.add_argument("--steps", type=int, default=3_000_000)
    ap.add_argument("--envs", type=int, default=min(16, os.cpu_count() or 4))
    ap.add_argument("--seed", type=int, default=0)
    # Inside rl/, not the repo root: in Docker only rl/ is mounted, and anything
    # saved outside it disappears with the container.
    ap.add_argument("--out", default=str(HERE / "runs"))
    args = ap.parse_args()
    check() if args.check else train(args)


if __name__ == "__main__":
    main()
