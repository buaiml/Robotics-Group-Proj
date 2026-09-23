# Week 2 mini-lecture — leg kinematics and classical gaits

25 minutes, whiteboard. The aim is that afterwards everyone can answer: *where
does a foot go when I move three joints, and why are we not just using the gait
the robot already has?*

Have the sim running headless before you start, in a terminal you can switch to.

---

## 0. Why this, before anything else (2 min)

The robot has 18 joints and no intuition attached to them. Until you can say
where a foot ends up given three angles, you cannot design a gait, a reward, or
even a sensible starting pose. Every later decision sits on this.

---

## 1. The chain and its frames (4 min)

Draw one leg. Three joints, three links:

```
body ──[coxa joint: yaw about z]── coxa ──[femur joint: pitch about y]── femur ──[tibia joint: pitch about y]── tibia ── foot
        rotates the leg                    lifts the leg                       extends/folds
        horizontally
```

Points to make:

- **The coxa joint is the odd one out.** It yaws about z, swinging the leg
  horizontally. The other two pitch about y, in a vertical plane. So the leg is
  *a 2-link planar arm on a turntable* — that is the whole trick, and it makes
  the maths tractable.
- **Each segment runs along its own +x axis.** Frames are attached at joints, and
  every link's local x points down its own length.
- Our numbers, from `urdf/props.xacro`: coxa 45 mm, femur 75 mm, tibia 130 mm.
- Six legs mounted at ±45°, ±90°, ±135°. Ask: why radial rather than four legs in
  a rectangle? (Answer comes back in section 4.)

---

## 2. Forward kinematics (8 min)

Work in the leg's vertical plane, *after* the coxa yaw. Key fact to put on the
board first, because everything follows from it:

> A rotation about **+y** by angle θ maps **x̂ → (cos θ, 0, −sin θ)**.

Note the minus sign on z: **positive femur angle drives the foot down**. Get this
wrong and every sign in your gait is inverted.

Then just add the links nose to tail:

```
x =  L1 + L2·cos(θ2) + L3·cos(θ2 + θ3)
z =     − L2·sin(θ2) − L3·sin(θ2 + θ3)
```

with θ3 measured *relative to the femur*, which is why the third term uses
θ2 + θ3. And the coxa yaw θ1 rotates that whole (x, z) result into the body
frame:

```
x_body = x·cos(θ1),   y_body = x·sin(θ1),   z_body = z
```

### The worked example — do this live

`stand.py` commands every leg to θ2 = −35°, θ3 = +75°. Put that through the
equations on the board:

| | |
|---|---|
| cos(−35°) = 0.819, sin(−35°) = −0.574 | θ2 + θ3 = 40°, cos = 0.766, sin = 0.643 |
| x = 0.045 + 0.075(0.819) + 0.130(0.766) | = **0.206 m** |
| z = −0.075(−0.574) − 0.130(0.643) | = **−0.0405 m** |

So the foot sits 40.5 mm below the coxa joint. Add the 12 mm foot radius and the
body should ride **52.5 mm** off the ground.

Now switch to the terminal:

```bash
gz model -m jethexa -p
```

It reports `base_footprint` at z = −0.0675. The URDF puts `base_link` 0.120 above
the footprint, so `base_link` is at 0.120 − 0.0675 = **0.0525 m**.

**52.5 mm predicted, 52.5 mm measured.** Agreement to the millimetre, on the
first try, with no fitting.

Two things to draw out of that:

1. The maths and the simulator agree, so both are probably right. This is what a
   sanity check looks like, and it is worth more than either one alone.
2. It explains something we had written down as a defect. The README says the
   robot "stands too low" — 5.3 cm against the 12 cm the URDF claims. **It is not
   a bug.** The stance angles in `stand.py` were picked by hand and they simply
   put the foot where the maths says they put it. The fix is better angles, not a
   different model.

---

## 3. Inverse kinematics (6 min)

The useful direction: *I want the foot* here, *what angles?*

Coxa is free — it just points the leg:

```
θ1 = atan2(y, x)
```

The remaining two joints are a 2-link planar arm. Let r be the horizontal
distance from the femur joint to the target and s the drop below it, so
d = √(r² + s²). Law of cosines on the triangle (L2, L3, d):

```
cos(θ3) = (d² − L2² − L3²) / (2·L2·L3)
```

Three things to make sure land:

- **There are two solutions**, ±θ3 — knee forward or knee back, the classic
  "elbow up / elbow down". Both put the foot in the same place. A gait has to
  pick one and stay consistent, or the leg snaps between configurations
  mid-stride.
- **There is a reachable annulus.** d must satisfy |L3 − L2| ≤ d ≤ L2 + L3, which
  for us is **55 mm to 205 mm** from the femur joint. Inside 55 mm the leg cannot
  fold tightly enough; past 205 mm it is not long enough. Outside that range the
  law of cosines hands you a |cos| > 1 and your code gets a NaN. Ask them what a
  NaN joint command does to a policy.
- **Singularities are at the boundary.** Fully extended, the leg loses a degree
  of freedom and the IK becomes numerically nasty. Real gaits stay well inside
  the annulus.

### Exercise to leave them with

To get the body to the 12 cm the URDF claims, the foot needs to be 108 mm below
the coxa joint. That is inside the annulus, so it is reachable — **what are the
angles?** Whoever is writing the stance or the open-loop gait needs exactly this
number.

---

## 4. Gaits and static stability (5 min)

Now the part that answers "why six legs".

**Support polygon.** Draw the hexagon of feet from above, shade the convex hull
of the feet currently on the ground. If the centre of mass projects inside that
hull, the robot is **statically stable** — it can stop mid-stride and simply
stand there.

This is the big structural advantage. A biped or a quadruped in a trot is
*dynamically* stable: it is falling and catching itself, and a stumble is
unrecoverable without active control. A hexapod can keep three feet down at all
times and never fall over even if the controller does nothing clever. That
matters for us: it means **a bad policy fails gently**, which is the difference
between a scuffed foot and a broken servo.

**Duty factor** = fraction of the cycle a leg spends on the ground. Then:

| Gait | Legs swinging | Feet down | Trade |
|---|---|---|---|
| **Tripod** | 3 at once (alternating triangles) | 3 | Fastest; support polygon shrinks to a triangle |
| **Ripple** | 2, offset in phase | 4 | Middle ground |
| **Wave** | 1 at a time | 5 | Slowest, most stable, best on bad terrain |

Stock JetHexa firmware ships tripod and ripple. Note the pattern: **speed and
stability trade directly against each other**, and the choice is a human's to
make in a classical gait. A learned policy can choose per step.

---

## 5. Close: so why are we using RL at all? (2 min)

Don't answer this. Pose it and let the group argue for the last two minutes.

The honest case *for* the classical gait: it works today, needs no training, is
interpretable, and on flat ground it will probably beat our first policy for
weeks. We are keeping it as the baseline precisely because it is hard to beat.

Things to steer the argument towards:

- A scripted gait has **no feedback**. It plays the same joint angles whether the
  robot is level, tilted, or has a foot hanging over a kerb. The IMU is not in
  the loop.
- Foot placement is fixed by a human in advance. On a 20 mm step, the foothold
  the script chose may be mid-air.
- It assumes a model we know is wrong — rigid links, known friction, instant
  servos. Our servos have a lag we have not even measured yet.
- Conversely: RL does not remove any of those problems, it **moves them into the
  reward function and the randomization ranges**. That is the trade, and it is
  what the next few weeks are about.

Leave them with: *what would the policy need to sense for any of that to help?*
That question is the observation-space task, and it is the next thing we decide.

---

## Materials

- Board: the FK equations, the leg diagram, the support-polygon hexagon.
- A terminal with the sim running headless, for the `gz model -m jethexa -p`
  reveal. Start it before the meeting — it takes ~30 s to come up.
- `urdf/props.xacro` open, so the link lengths are visibly *from* somewhere.

## If you have extra time

Ask someone to change the stance angles in `stand.py` live, have the room predict
the new body height from the FK, then run it and check. It takes two minutes and
it converts the whole lecture from "notes" to "a tool I can use".
