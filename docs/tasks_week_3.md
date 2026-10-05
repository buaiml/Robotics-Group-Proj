# Week 3: getting to know Gazebo, and deciding how we build this

This week is mostly research. There are two goals:

1. Get comfortable with Gazebo, so it feels like a tool you can use and not a
   window you're scared to click in.
2. Work out **how we want to do the rest of the project**. At the end of the
   week the group makes real decisions, and they should be based on what you
   found rather than on what the plan doc happens to say.

It's about 1.5 hours in total: half an hour of warm-up that everyone does, then
one area of your choice.

---

## Everyone: Gazebo warm-up (about 30 min)

Launch the sim ([commands.md](commands.md)) and try each of these once:

- **Pause, step, play.** Pause the sim and step it one tick at a time. Watch the
  real-time factor in the bottom corner. What happens to it when you run
  `stand.py`?
- **Throw things at the robot.** Use the shapes on the top toolbar to drop a box
  or a sphere onto it. Move them around with the translate tool.
- **Look inside.** Open the entity tree, click a leg link, and find its mass and
  pose in the component inspector.
- **Listen in from the terminal.** Run `gz topic -l` and `ros2 topic list`. Some
  topics exist on only one side, and the bridge is what connects them. Find one
  topic that appears in both lists.

Write down anything that confused you. Those notes become next week's lecture.

---

## Pick an area

Choose whichever area interests you. Two people in the same area is fine: split
the questions between you.

Every area ends the same way: a **one-page write-up** in
`docs/research/<area>.md` with

- **The question:** what you were trying to find out.
- **What you found:** with links, so someone else can check it.
- **What you'd recommend** we do.
- **What you're unsure about.**

Bring it to the meeting and present it in about 3 minutes. "I looked and
couldn't find a good answer" is a perfectly good result, as long as you say
where you looked.

### Simulation

- **Explore a Gazebo world file.** Open `worlds/flat_ground.sdf` and work out
  what each block does. Change gravity, the physics step size, or the ground
  friction, relaunch with `world:=`, and see what happens to the robot.
- **Research question: which simulator should we train in?** Our plan says:
  train in MuJoCo, check in Gazebo. Test that assumption. Compare MuJoCo, Isaac
  Lab, Genesis and Gazebo itself on four things:
  - How fast does each one run?
  - Does it need an NVIDIA GPU? (Most of our laptops don't have one.)
  - How hard is it to get our robot model into it?
  - Has anyone trained a legged robot in it?

### ROS 2

- **Map the running system.** With the sim up, run `rqt_graph`. Which nodes
  exist? Who publishes and who subscribes to `/joint_states`, the lidar and the
  camera? Draw the diagram in your own words.
- **Research question: how do we get our code onto the robot?** The robot runs
  ROS 1 Melodic on Ubuntu 18.04, while we use ROS 2 Humble. Look into three
  options and what each one costs us:
  - reflash the robot with a newer image (does Hiwonder have one?)
  - run a ROS 1 to ROS 2 bridge
  - run ROS 2 in a container on the Jetson Nano

### Control and gait

- **Watch a joint respond.** Plot `/joint_states` in `rqt_plot` while you send
  step commands to one joint (see [commands.md](commands.md)). How long does the
  joint take to get there? Does it overshoot?
- **Research question: how do hexapods usually walk?** Read up on tripod,
  wave and ripple gaits, and on central pattern generators (CPGs). Then find out
  what gait code Hiwonder's own software uses. Should we have a hand-written
  gait as a baseline or a fallback, even if RL works?

### Learning (RL)

- **Research question: is there a model zoo we can start from?** Search Hugging
  Face, GitHub and MuJoCo Menagerie for hexapod or legged-robot policies and
  environments. Is there anything close enough to our robot to learn from or
  borrow from?
- **Research question: which RL library should we use?** Compare Stable-Baselines3,
  CleanRL, rsl_rl and skrl on:
  - How beginner-friendly is it?
  - Are the docs any good?
  - Has anyone used it to make a legged robot walk?

  Try to run one of their example scripts.

### Perception and sensing

- **See what the robot sees in Gazebo.** Put a box, a step or a wall in front
  of the robot. Look at the lidar and depth camera in RViz (or with
  `gz topic -e`). What shows up, and what doesn't?
- **Research question: how would a small robot spot a kerb and a crosswalk?**
  Find out how other small robots detect steps, edges and road markings.
  Classical vision or a learned model? Could either run on a Jetson Nano?

### Navigation and planning

- **Bring a real place into Gazebo.** Gazebo Fuel is an online library of free
  models (buildings, roads, pavement). Add a few to a copy of our world with the
  Resource Spawner, and see how hard it would be to build something that looks
  like our route.
- **Research question: how does the robot get from building A to building B?**
  Look into Nav2, SLAM (building a map as you go) and GPS waypoints. For a route
  like ours, what do people actually use? Do we need a map made in advance?

### The real robot and hardware

- **Research question: can the Jetson Nano run the policy?** Find out:
  - how fast a small neural network runs on the Nano
  - how the robot's power budget and battery life look
  - what the robot's software already gives us for free
- **Research question: what are the rules and risks?** Can a robot be on campus
  paths and crosswalks at all? Who do we ask? What happens if it falls in the
  road? Suggest safety rules for outdoor tests.

---

## At the meeting: decisions to make

Each area presents, then we decide as a group:

1. Which simulator do we train in?
2. Which RL library do we use?
3. Do we build a hand-written gait as a baseline?
4. How does our ROS 2 code reach the robot?
5. Roughly how will the robot navigate the route?

Whatever we decide goes into [semester_plan.md](semester_plan.md), and the
pairs for the rest of the semester form around the areas people enjoyed.
