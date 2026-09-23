# Setting up the environment

Target: **Ubuntu 22.04 + ROS 2 Humble + Gazebo Harmonic**. The reasoning for
those versions is in the [README](../README.md#versions-and-why).

Everyone should use the same environment. Eight different ROS installs would
eat a large share of this project's total time budget.

## Which route is yours?

**Windows, with an Ubuntu 22.04 WSL instance** — most people. Open your WSL
terminal, clone the repo there, and run:

```bash
git clone https://github.com/buaiml/Robotics-Group-Proj.git && cd Robotics-Group-Proj
```

```bash
sudo bash tools/provision_ubuntu2204.sh
```

It installs everything for **your** user, whatever it's called. It never creates
another account, and it never touches your password, sudo settings or WSL login.
It takes about 20 minutes. Open a new terminal afterwards.

Check first that your instance really is 22.04. ROS 2 Humble does not exist for
24.04, and the script will refuse:

```bash
lsb_release -rs
```

**Mac, with Docker Desktop** — see [In Docker](#in-docker). On an Apple Silicon
(M1–M4) Mac, read [Apple Silicon Macs](#apple-silicon-macs) first.

**Anything else** — the rest of this page.

## Already done on the project machine

A WSL instance named `jethexa` is provisioned and verified:

```bash
wsl -d jethexa
```

Nothing to install; the workspace is at `~/jethexa_ws` and the environment is
sourced automatically.

## What has actually been tested

Be clear about this before promising anyone it will work.

| Setup | Status |
|---|---|
| Windows + WSL2, `sudo bash tools/provision_ubuntu2204.sh` inside WSL | **Tested end to end** (the main student route) |
| Windows + WSL2, existing instance (`setup_wsl.ps1 -UseExisting`) | **Tested end to end** |
| Students with different usernames and passwords | **Tested**: seven account scenarios, each in a clean container. Passwords checked against the stored hash |
| Windows + Docker Desktop, via `tools/docker_run.sh` from Git Bash | **Tested end to end** (build, launch, controllers) |
| Windows + WSL2, fresh instance (`setup_wsl.ps1` with no flags) | Each step tested separately; not run as one piece |
| Windows + antivirus that intercepts HTTPS (Norton here) | **Tested**, with a certificate in `tools/extra-ca/` |
| Native Ubuntu 22.04 or a VM | Not tested; same script as WSL minus `/etc/wsl.conf` |
| Linux + Docker | Helper logic tested; build not run on a Linux host |
| Intel Mac + Docker Desktop | Same amd64 image as tested on Windows; helper tested under macOS bash 3.2; not run on a real Mac |
| **Apple Silicon Mac** + Docker Desktop | **Not run on a real Mac.** Uses the tested amd64 image under emulation (below). A native arm64 build is refused on its first screen (tested) |
| Raspberry Pi / any arm64 Linux | **Will not work** as-is: no arm64 build of the Gazebo-ROS bridge |
| Behind a proxy that needs `HTTP_PROXY` settings | **Not handled** |

### Apple Silicon Macs

`ros-humble-ros-gzharmonic`, the Gazebo-ROS bridge, is only published for
amd64. Everything else in the stack exists for arm64. So on an M-series Mac the
helper builds and runs the **amd64** image under Docker Desktop's emulation:

1. Docker Desktop → Settings → General → turn on *Use Rosetta for x86_64/amd64
   emulation on Apple Silicon*.
2. `tools/docker_run.sh build` adds `--platform linux/amd64` automatically.
   Expect about an hour for the first build, not twenty minutes.

Gazebo will run slower under emulation. That's acceptable, because Gazebo is
the validation sim. For training, MuJoCo has native Apple Silicon wheels and
runs fine directly on macOS, outside Docker.

If the provisioning script finds itself on arm64 anyway, it stops on the first
screen and says why, instead of failing fifteen minutes in.

## On a machine where WSL is already set up, from Windows

The same as running the script inside WSL (see the top of this page), but
driven from PowerShell. Useful if you'd rather not open WSL yourself:

```bash
powershell -ExecutionPolicy Bypass -File tools\setup_wsl.ps1 -UseExisting -Name <your-instance>
```

It works out whose instance it is: the existing first user, whatever that user
is called. It installs for that user and changes nothing about the account:
not the password, not sudo settings, not which user WSL logs in as. Afterwards
it **checks that the login is the same as before** and fails loudly if not.
It also checks for Ubuntu 22.04 before starting.

Get the instance name wrong and it lists the ones that exist. To target a
specific user instead of the first one, add `-User <name>`.

**It must be Ubuntu 22.04.** ROS 2 Humble has no packages for 24.04. An instance
created with a plain `wsl --install -d Ubuntu` is 24.04 or newer, so if the
check refuses, build a 22.04 instance alongside it:

```bash
powershell -ExecutionPolicy Bypass -File tools\setup_wsl.ps1 -Name jethexa22
```

## On a fresh Windows machine

One command, which creates the instance, provisions it, restarts it and
verifies the result:

```bash
powershell -ExecutionPolicy Bypass -File tools\setup_wsl.ps1
```

It refuses to touch an existing instance unless you pass `-UseExisting` (install
into it) or `-Force` (delete and rebuild it). Takes 20–30 minutes, nearly all of
it downloading packages.

**Credentials, for a fresh instance only.** User `jethexa`, password **a single
space**. Instances that already existed keep their own user and password. `sudo` needs no
password at all, so the only places you'll ever type it are `su` or SSH into the
instance. `wsl -d jethexa` logs straight in without asking.

A space is an awkward thing to type at an invisible prompt, so if a student
reports that login "does nothing", that's the first thing to check. Override
either value on a fresh install:

```bash
powershell -ExecutionPolicy Bypass -File tools\setup_wsl.ps1 -User myname -Password mypassword
```

<details>
<summary>The same thing by hand, if the script fails</summary>

```bash
wsl --install --distribution Ubuntu-22.04 --name jethexa --no-launch
```

```bash
wsl -d jethexa -u root -- bash /mnt/c/path/to/repo/tools/provision_ubuntu2204.sh
```

The restart is not optional — `/etc/wsl.conf` only applies on restart, so
without it you log in as `root` instead of `jethexa`:

```bash
wsl --terminate jethexa
```

</details>

## In Docker

The provisioning script detects that it's in a container and adapts: it skips
the login account and `/etc/wsl.conf`, and cleans up apt lists to keep the image
smaller. Build from the **repo root**, not from `tools/`:

```bash
docker build -f tools/Dockerfile -t jethexa:humble .
```

Or use the helper, which also matches the container's user to yours so mounted
files don't end up owned by root:

```bash
tools/docker_run.sh build
```

Then:

```bash
tools/docker_run.sh shell
```

That mounts `jethexa_sim/` from the repo into `~/jethexa_ws/src/`, so you edit
on the host and build in the container. To run a single command without opening
a shell:

```bash
tools/docker_run.sh run "cd ~/jethexa_ws && colcon build --symlink-install"
```

The helper works from Linux, macOS and **Git Bash on Windows**. Running raw
`docker run -v ...` from Git Bash does not work: Git Bash rewrites the container
path and the mount silently lands nowhere. Use the helper, or prefix the command
with `MSYS_NO_PATHCONV=1`.

The image is about 6.7 GB and takes around 20 minutes to build the first time.

**If the build stops at "checking HTTPS works"** with a message about something
intercepting HTTPS, your antivirus or network is re-signing certificates. The
message explains it, and [`tools/extra-ca/README.md`](../tools/extra-ca/README.md)
has the three-step fix. This happened on the project machine (Norton), so it is
not hypothetical.

**Run the sim headless.** A GUI out of a container needs X11 forwarding, which
is straightforward on a Linux host and awkward on Windows and macOS:

```bash
ros2 launch jethexa_sim jethexa_gazebo.launch.py gui:=false
```

On a Linux host you can try `tools/docker_run.sh gui`, which forwards
`/tmp/.X11-unix` and runs `xhost +local:docker`. Everywhere else, stay headless
and inspect the sim through topics and `gz model -m jethexa -p` — which is how
most of the work gets done anyway.

Two flags in the run command that are not optional, and why:

- `--shm-size=1g`. The ROS middleware and Gazebo both use shared memory, and
  Docker's 64 MB default causes crashes that look like random node failures.
- `--network host` where supported (Linux). Lets ROS nodes inside and outside
  the container discover each other. Docker Desktop on Mac/Windows doesn't
  support it; you just lose cross-boundary discovery, which is fine if
  everything runs in the one container.

If you want a login account in the container anyway:

```bash
docker run --rm -it -e JETHEXA_CREATE_USER=1 jethexa:humble bash -l
```

## On native Ubuntu 22.04, or a VM

```bash
sudo bash tools/provision_ubuntu2204.sh
```

Then open a new shell so `/etc/profile.d/jethexa.sh` is picked up.

This is the same script in all four cases — WSL, Docker, VM, bare metal. It
works out where it's running and the only things that change are whether it
creates a login account and whether it writes `/etc/wsl.conf`. Everything about
ROS and Gazebo is identical, which is the point: nobody should be debugging a
difference between two students' setups that came from the installer.

## Build the workspace

```bash
mkdir -p ~/jethexa_ws/src && cp -r jethexa_sim ~/jethexa_ws/src/ && cd ~/jethexa_ws && colcon build --symlink-install
```

## Check it worked

```bash
python3 ~/jethexa_ws/src/jethexa_sim/scripts/check_model.py
```

Expect `18 joints, sensor payload intact, 0 contact sensor(s), no dangling
collision refs`. Then launch it:

```bash
ros2 launch jethexa_sim jethexa_gazebo.launch.py
```

## Installing by hand

`tools/provision_ubuntu2204.sh` does all of this for you. The steps are here for
when you need to debug one of them, or install onto a machine you don't want a
script touching. Run as root, or prefix with `sudo`.

**1. Base packages and locale.** ROS is unhappy without a UTF-8 locale.

```bash
apt-get update && apt-get install -y ca-certificates curl gnupg lsb-release locales software-properties-common git build-essential cmake python3-pip python3-dev
```

```bash
locale-gen en_US en_US.UTF-8 && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
```

**2. The ROS 2 apt source.** Current practice is a `.deb` that installs the key
and list file, rather than piping a key into apt yourself.

```bash
add-apt-repository -y universe
```

```bash
ROS_APT_SOURCE_VERSION=$(curl -sL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F '"tag_name"' | awk -F'"' '{print $4}')
```

```bash
curl -sL -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo $VERSION_CODENAME)_all.deb"
```

```bash
apt-get install -y /tmp/ros2-apt-source.deb
```

**3. The Gazebo apt source.** Separate repository, run by OSRF.

```bash
curl -sL https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
```

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" > /etc/apt/sources.list.d/gazebo-stable.list
```

```bash
apt-get update
```

**4. ROS 2 Humble.**

```bash
apt-get install -y ros-humble-desktop ros-dev-tools
```

**5. Control, navigation and build tooling.**

```bash
apt-get install -y ros-humble-ros2-control ros-humble-ros2-controllers ros-humble-xacro ros-humble-joint-state-publisher-gui ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-slam-toolbox python3-colcon-common-extensions python3-rosdep python3-vcstool
```

**6. Gazebo Harmonic and its ROS bridge.** Note `ros-humble-ros-gzharmonic`, not
`ros-humble-ros-gz` — the latter pairs Humble with Fortress, which is
end-of-life.

```bash
apt-get install -y gz-harmonic ros-humble-ros-gzharmonic
```

```bash
rosdep init; rosdep update --rosdistro humble
```

**7. `gz_ros2_control`, from source.** There is no Humble + Harmonic binary, so
this one gets built. `GZ_VERSION=harmonic` is what makes it build against
gz-sim 8 instead of Fortress — without it you get a package that loads and then
fails to find the simulator.

```bash
mkdir -p /opt/gz_ws/src && git clone --branch humble --depth 1 https://github.com/ros-controls/gz_ros2_control.git /opt/gz_ws/src/gz_ros2_control
```

```bash
cd /opt/gz_ws && source /opt/ros/humble/setup.bash && GZ_VERSION=harmonic colcon build --merge-install --cmake-args -DCMAKE_BUILD_TYPE=Release
```

**8. The account.** A single space as a password is deliberate; `printf` rather
than `echo` so it isn't mangled, and `chpasswd` rather than `passwd` so it works
unattended.

```bash
useradd -m -s /bin/bash -G sudo jethexa && printf '%s:%s
' jethexa ' ' | chpasswd
```

```bash
echo "jethexa ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/jethexa && chmod 0440 /etc/sudoers.d/jethexa
```

```bash
printf '[user]
default=jethexa
' > /etc/wsl.conf
```

**9. Python packages** for the training sim, needed from Week 3.

```bash
pip3 install mujoco gymnasium numpy matplotlib
```

**10. Environment.** Put this in `/etc/profile.d/jethexa.sh` so it applies to
login shells. Do *not* put it only in `~/.bashrc` — that returns early for
non-interactive shells, so `wsl -d jethexa -- bash -lc "..."` would get none of it.

```bash
cat > /etc/profile.d/jethexa.sh <<'EOF'
export GZ_VERSION=harmonic
export ROS_DOMAIN_ID=42
[ -f /opt/ros/humble/setup.bash ] && . /opt/ros/humble/setup.bash
[ -f /opt/gz_ws/install/setup.bash ] && . /opt/gz_ws/install/setup.bash
[ -f "$HOME/jethexa_ws/install/setup.bash" ] && . "$HOME/jethexa_ws/install/setup.bash"
true
EOF
```

Open a new shell, then check:

```bash
echo "$ROS_DISTRO $GZ_VERSION" && gz sim --versions
```

Expect `humble harmonic` and `8.x.x`.

## What the provisioning script installs

| | |
|---|---|
| ROS 2 | `ros-humble-desktop`, `ros-dev-tools`, colcon |
| Control | `ros2_control`, `ros2_controllers` |
| Navigation | `navigation2`, `nav2_bringup`, `slam_toolbox` |
| Simulation | `gz-harmonic`, `ros-humble-ros-gzharmonic` |
| Control bridge | `gz_ros2_control`, **built from source** at `/opt/gz_ws` |
| Python | `mujoco`, `gymnasium`, numpy, matplotlib |
| Account | user `jethexa`, password a single space, passwordless sudo |

`gz_ros2_control` is built from source because no Humble + Harmonic binary
exists — the released binary pairs Humble with Fortress, which is end-of-life.
The build needs `GZ_VERSION=harmonic` set, which the script handles.

## Things that bit us, so they don't bite you

**Windows line endings break everything that runs in Linux.** Git on Windows
often has `core.autocrlf=true`, which checks files out with CRLF. A CRLF shell
script dies on its first line with `set: pipefail
: invalid option name`, and
a CRLF shebang makes `ros2 run` look for an interpreter called `python3
`.
The repo's `.gitattributes` now forces LF for everything Linux-bound, so fresh
clones are fine. If you cloned before it existed, the simplest fix is a fresh
clone into a new folder. To fix it in place instead, **commit your work first** —
the second command throws away anything uncommitted:

```bash
git status
```

```bash
git rm --cached -r -q . && git reset --hard
```

**Auto-detecting Docker doesn't work inside `docker build`.** Build containers
have no `/.dockerenv`, and on Docker Desktop the kernel reports "microsoft", so
the provisioning script concludes it's in WSL. The Dockerfile therefore sets
`JETHEXA_ENV=docker` explicitly. If you write your own Dockerfile around the
script, do the same, or you'll get a login account and `/etc/wsl.conf` baked
into the image.

**The GUI under WSL.** WSLg renders the Gazebo GUI, but sensor update rates run
well below what they request under software rendering (we measured lidar at
~4.4 Hz against 10 Hz). If the GUI misbehaves, uncomment
`LIBGL_ALWAYS_SOFTWARE=1` in `/etc/profile.d/jethexa.sh`. For batch work, use
`gui:=false`.

**WSL shuts an instance down** when the last process exits, which kills anything
you backgrounded with `nohup`. Keep a shell open, or use `systemd-run`.

**`~/.bashrc` returns early for non-interactive shells**, so environment setup
placed there never runs under `wsl -d jethexa -- bash -lc "..."`. That is why
the environment lives in `/etc/profile.d/jethexa.sh` instead.

**The `ros2` CLI daemon** intermittently throws `!rclpy.ok()` on this setup. Run
`ros2 daemon stop` and retry; it is a CLI issue, not a problem with your nodes.

**PowerShell eats `$VAR` before WSL sees it.** `wsl -d jethexa -- bash -lc 'echo
"$ROS_DISTRO"'` comes back empty even though the variable is set, because
PowerShell expands it first. Use `printenv ROS_DISTRO` instead, or run the
command from inside the instance. This cost us a false alarm about the
environment being broken when it wasn't.
