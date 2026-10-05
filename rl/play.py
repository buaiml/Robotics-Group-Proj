#!/usr/bin/env python3
"""Watch a trained policy walk, in the MuJoCo viewer.

    python3 rl/play.py                      # latest run in runs/
    python3 rl/play.py rl/runs/20261001-1530   # a specific run
    python3 rl/play.py --headless           # no window: just print how far it walked
    python3 rl/play.py --home               # baseline: hold the stance, no policy
"""
import argparse
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mujoco
import numpy as np

from jethexa_env import JetHexaWalkEnv


def latest_run():
    runs = sorted((HERE / "runs").glob("*/model.zip"))
    if not runs:
        sys.exit("no trained runs in rl/runs/ yet - train one first: python3 rl/train.py")
    return runs[-1].parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?", help="run directory (default: the latest)")
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--home", action="store_true", help="no policy, just hold the home stance")
    args = ap.parse_args()

    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    venv = DummyVecEnv([JetHexaWalkEnv])
    if args.home:
        policy = lambda obs: np.zeros((1, 18))
        print("baseline: holding the home stance")
    else:
        from stable_baselines3 import PPO
        run = Path(args.run) if args.run else latest_run()
        venv = VecNormalize.load(str(run / "vecnormalize.pkl"), venv)
        venv.training, venv.norm_reward = False, False   # use the saved statistics as-is
        model = PPO.load(run / "model.zip", device="cpu")
        policy = lambda obs: model.predict(obs, deterministic=True)[0]
        print(f"policy: {run}")

    env = venv.envs[0] if args.home else venv.venv.envs[0]
    viewer = None
    if not args.headless:
        import mujoco.viewer
        viewer = mujoco.viewer.launch_passive(env.model, env.data)
        viewer.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
        viewer.cam.trackbodyid = env.base
        viewer.cam.distance, viewer.cam.elevation = 0.8, -20

    obs = venv.reset()
    results = []
    while len(results) < args.episodes:
        t = time.time()
        obs, _, done, info = venv.step(policy(obs))
        if done[0]:
            fell = not info[0].get("TimeLimit.truncated", False)
            results.append(info[0]["distance"])
            print(f"episode {len(results)}: {info[0]['distance']:+.2f} m in 20 s "
                  f"({info[0]['distance'] / 20:+.3f} m/s){'  - fell' if fell else ''}")
        if viewer:
            if not viewer.is_running():
                break
            viewer.sync()
            time.sleep(max(0.0, env.dt - (time.time() - t)))   # real time
    if results:
        print(f"mean {np.mean(results):+.2f} m per episode")
    if viewer:
        # The viewer's render thread and PyTorch crash each other during normal
        # interpreter shutdown ("core dumped"). Everything is printed by now,
        # so leave without it.
        viewer.close()
        sys.stdout.flush()
        os._exit(0)


if __name__ == "__main__":
    main()
