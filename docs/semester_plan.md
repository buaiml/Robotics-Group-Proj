# Semester Plan — JetHexa Learned Locomotion + Crosswalk Navigation

## 0. What this project is actually for

Two goals, in this order:

1. **Eight students understand legged locomotion, reinforcement learning, and
   sim-to-real transfer well enough to make their own design decisions.**
2. A JetHexa walks on a learned gait, and navigates between two buildings using
   crosswalks.

Goal 2 is the vehicle for goal 1. When the two conflict — and they will, around
Week 7 when the training run isn't converging — goal 1 wins. A student who can
explain *why* their reward function produced a limping gait has had a better
semester than one who cloned a repo that worked.

The test we apply all semester: **can you explain, at the weekly meeting, why
this is set the way it is?** If nobody on the team can answer that for a piece
of the system, that piece is a liability regardless of whether it runs.

## 1. The budget

| | |
|---|---|
| People | 8 students |
| Individual work | 1–2 h/week (plan against **1.5 h**) |
| Weekly meeting | 1 h, everyone, teaching + unblocking |
| Weeks | 14 (adjust if your semester differs) |
| **Total individual work** | **~170 person-hours** |

170 person-hours is roughly one person-month for a problem that is, in its full
form, a multi-person-year problem. Two consequences:

- **Every task is one sitting.** Scoped to fit a single 1–2 hour session, start
  to finish, with something committed at the end. A student who misses a week
  does not block anyone.
- **We are selective about what we build from scratch.** Not because building is
  bad — because time spent fighting a CMake error is time not spent understanding
  advantage estimation. See §2.

## 2. Build vs. borrow

The rule is **borrow the plumbing, build the ideas.**

**We build ourselves, because building it is how you learn it:**

| Thing | Why it's ours |
|---|---|
| The leg kinematics and the URDF | You cannot reason about a gait you can't describe geometrically |
| The observation space | Every entry is a claim about what the robot needs to know, and whether it can measure it |
| The reward function | This *is* the task specification. Outsourcing it means not knowing what you asked for |
| The env loop (reset, termination, curriculum) | Where most silent bugs live |
| The terrain generator | Forces you to think about what "hard terrain" means |
| The sim-to-real bridge | The actual research contribution of this project |
| Every hyperparameter you change | Changing values you can't explain is not experimentation |

**We borrow, with understanding required:**

| Thing | Condition |
|---|---|
| The PPO implementation | You must be able to walk through the update step at the meeting. Use a library; know what it does |
| ROS/Gazebo/colcon boilerplate | Infrastructure, not insight |
| SLAM and the global planner | We are not writing a SLAM system this semester. Know the algorithm class and its failure modes |
| Logging, checkpointing, plotting | Pure tooling |
| Reference hyperparameters from published legged-locomotion work | Start there, then justify every deviation |

**Reading other people's solutions is encouraged — copying them into the repo
unread is not.** If you find a hexapod RL repo that solves half our problem, the
right move is a one-page brief at the meeting: what they did, what we'd take,
what we'd do differently and why. That brief is worth more to the team than the
code.

## 3. The weekly meeting (1 h)

This is where the teaching happens. Structure:

| | |
|---|---|
| 0:00–0:25 | **Topic of the week** — taught by a rotating pair (see §6) |
| 0:25–0:40 | **Demos** — anyone who has something running shows it, including failures |
| 0:40–0:55 | **Blockers and decisions** — decisions get written down in `docs/decisions/` |
| 0:55–1:00 | Who's doing what this week |

**The teaching pair prepares during their weekly hours** — that's their task for
the week, and it is a real task. Teaching a topic is the fastest way to learn it,
and it means by Week 14 every student has had to genuinely understand at least
two things rather than eight things vaguely.

Format for the 25 minutes: whiteboard or a handful of slides, one worked
example, one open question for the group. Not a lecture read from notes.

## 4. What the semester realistically ends with

Stated plainly so nobody is surprised in Week 13.

**Must hit**
- A trustworthy JetHexa model in both Gazebo and a fast training sim, its
  geometry taken from the vendor URDF and its actuator behaviour from the
  servo datasheet and bench tests.
- A PPO policy that walks on flat ground in simulation under a velocity command.
- That policy running on the real robot, walking on flat indoor floor.
- A Gazebo campus world with a crosswalk, and a planner that routes through it.
- Eight students who can each explain the full pipeline at a whiteboard.

**Should hit** (expected; first to be cut)
- Moderate terrain in sim: slopes, 10–20 mm steps, rough ground.
- Domain randomization, so sim-to-real isn't luck.
- Navigation driving the learned gait end-to-end **in simulation**, A→B through
  a crosswalk.

**Stretch** (a win, not a plan)
- Real robot walking a short outdoor segment including one kerb.
- Full real-world building-to-building run.

**Out of scope, decided now:** traffic-light reading, vehicle intent prediction,
end-to-end learned navigation (the policy walks; a classical planner decides
where), outdoor localization robustness, night/wet conditions.

## 5. Phases

| Weeks | Phase | Exit criterion |
|---|---|---|
| **1–2** | Foundations | All eight run the sim unaided; model rebuilt from the vendor URDF; people have found the area they want |
| **3–4** | Tooling, RL basics & environment | Training sim installed; tool/model-zoo survey done; servos bench tested; observation and action spaces agreed; student-built MuJoCo model + Gymnasium env that runs random actions |
| **5–6** | First policy | Something walks forward on flat ground, and the team can explain why it does |
| **7–8** | Robustness | Velocity conditioning, domain randomization, light terrain. **Midterm demo** |
| **9–10** | Sim-to-real | Policy on the Jetson; robot stands, then walks on flat floor |
| **11–12** | World & navigation | Campus world with crosswalks; planner routes through one; `cmd_vel` drives the policy in sim |
| **13** | Integration | Full A→B run in sim; stretch attempt outdoors |
| **14** | Wrap | Final demo, report, handoff for next semester |

Slack is built into Weeks 8 and 13. Expect to spend it.

## 6. Teaching calendar

One topic per week, taught by a rotating pair. Pairs are assigned in Week 1 so
people can prepare; the topic lands the week *before* the team needs it.

| Wk | Topic | Core question the pair must answer |
|---|---|---|
| 1 | Project framing + how a robot is described | What is a URDF, a link, a joint, a frame? Why does the JetHexa have 18 of them? |
| 2 | Leg kinematics and classical gaits | Forward and inverse kinematics of a 3-DoF leg; tripod vs. ripple; why would we *not* just use IK? |
| 3 | How physics simulators work | Contacts, friction, integrators, timestep. Why do two simulators disagree? |
| 4 | RL as a problem statement | MDPs; observation, action, reward, episode. Why position targets and not torques? |
| 5 | Policy gradients → PPO | What is an advantage? What does the clipped objective actually prevent? |
| 6 | Reward design and reward hacking | Show three real examples of policies exploiting a reward. How do we detect it? |
| 7 | Domain randomization and the reality gap | Why does a perfect sim policy fail on hardware? What is system identification? |
| 8 | *(midterm demo + retrospective — no topic)* | — |
| 9 | Deployment on embedded hardware | Control loops, latency, jitter, inference cost, and how each one breaks a policy |
| 10 | Sensors: lidar vs. depth cameras | What can a 2D lidar not see? Why does that matter for kerbs? |
| 11 | SLAM and localization, at a level we can use | What is a costmap? When does SLAM fail outdoors? |
| 12 | Path planning | A*/Dijkstra, global vs. local planners, and how a crosswalk becomes a constraint |
| 13 | Evaluating RL honestly | Seeds, variance, cherry-picked videos, and what a fair benchmark looks like |
| 14 | *(final demo — no topic)* | — |

Each pair teaches twice over the semester. Assign in Week 1 and publish the
calendar, so nobody is surprised.

## 7. Teams

Weeks 1–2 have no fixed teams: everyone sets up their own environment, then
picks whichever area of the robot or pipeline they find interesting. Use those
two weeks to find out what people actually want to work on, then form the pairs
below in Week 3 around what you saw.

| Pair | Name | Owns from Week 3 |
|---|---|---|
| **A** | Model & Sim | URDF/MJCF, actuator model, domain randomization |
| **B** | RL | env, reward, training runs, policy |
| **C** | World & Terrain | Gazebo worlds, campus map, terrain generation |
| **D** | Perception & Deploy | sensors, SLAM/planning, on-robot integration |

Pair by experience rather than by friendship: someone who has done a fair amount
of programming with someone who hasn't. Each week the pair takes two overlapping
tasks on the same topic and decides between themselves who does which. They
review each other's PRs, and they take turns presenting, with whoever is newer
to the topic going first — if they can't explain the pair's work, the pair isn't
finished. That constraint is the point: it makes the more experienced partner
teach rather than just ship.

Two people at 1.5 h/week is **~3 person-hours per pair per week**. Size tasks to
that. Pair B is the critical path; spare capacity goes to B, or to whoever is
blocking B.

**Rotate at Week 8**: the more experienced partner moves one pair to the right,
the other stays. Fresh eyes on a stale problem, each area keeps continuity, and
those students end the semester having seen two quarters of the system.

Revisit the pairings at the midpoint. Someone who has outgrown the
less-experienced side of a pair should be moved, and told why — this is meant to
be a ladder, not a fixed hierarchy for fourteen weeks.

## 8. Standing decisions

Made now so they aren't remade weekly. Each one is also a teachable moment — the
reasoning matters more than the conclusion.

- **Algorithm: PPO.** On-policy, forgiving of reward shaping, standard in
  published legged locomotion, and well-documented enough to be understood rather
  than invoked. (Taught Week 5.)
- **Action space: joint position targets.** The serial-bus servos accept position
  commands only; a torque policy cannot be deployed. See
  [`jethexa_hardware.md`](jethexa_hardware.md) §3.
- **Two simulators.** Gazebo runs ~real-time with one robot; PPO needs ~10⁸
  steps. Train in **MuJoCo**, validate in **Gazebo** with the full ROS stack.
  (Taught Week 3.)
- **No foot-contact observations.** The hardware has no foot switches; a policy
  that uses them is untransferable. See hardware doc §4.
- **Small actor network** (2×128 or 2×256 MLP) — the Jetson Nano must run it at
  50 Hz.

Any of these can be overturned by a student who argues it well at a meeting.
That is a good outcome, not a disruption. Write the result in `docs/decisions/`.

## 9. Working agreements for a 1.5 h/week project

- **Commit something every session.** A branch with a half-finished script and an
  honest note beats perfect work that lives on one laptop.
- **Write down where you stopped** — two lines in the PR: what works, what's next.
  You will not remember in seven days.
- **Shared environment from Day 1.** One Docker image or one documented install.
  Debugging eight different Ubuntu setups would consume the entire semester.
- **Long training runs launch Friday, get checked Monday.** Checkpointing and
  auto-resume from the very first run — nobody has time to babysit.
- **Every experiment gets a row in the log**: config, seed, result, one-line
  conclusion. An unlogged run did not happen.
- **Decisions are written down**, dated, in `docs/decisions/`. Undocumented
  decisions get relitigated in Week 11.

## 10. Risks

| Risk | Mitigation |
|---|---|
| **Scope vs. budget** — the biggest risk by far | Tiered scope in §4; cut from the bottom, early and openly |
| Learning goal quietly replaced by "make it work" | The explain-it test; teaching rotation; demos include failures |
| Setup eats Weeks 1–3 | Shared image, owned by one person, copied by everyone |
| Context lost between weekly sessions | One-sitting tasks; written stop-notes; everything in the repo |
| One robot, eight people, few hours | Hardware slots booked ahead; hardware work batched, not trickled |
| A student disappears for three weeks | No task spans sittings; no critical single owner |
| Team B becomes the only team that understands RL | Week 8 rotation; RL topics taught by pairs from *other* teams |
