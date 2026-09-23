#!/usr/bin/env bash
# Build and run the JetHexa container.
#
#   tools/docker_run.sh build     build the image (~20 min the first time)
#   tools/docker_run.sh shell     open a shell in it (default)
#   tools/docker_run.sh gui       same, but try to forward the Gazebo GUI
#   tools/docker_run.sh run CMD   run one command without a terminal, e.g.
#                                 tools/docker_run.sh run colcon build
#
# The repo's jethexa_sim/ is mounted at ~/jethexa_ws/src/jethexa_sim inside the
# container, so you edit on the host and build in the container.
#
# Works from Linux, macOS, and Git Bash on Windows.
set -euo pipefail

IMAGE="${JETHEXA_IMAGE:-jethexa:humble}"
CONTAINER="${JETHEXA_CONTAINER:-jethexa-dev}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CMD="${1:-shell}"

die() { echo "ERROR: $*" >&2; exit 1; }
command -v docker >/dev/null || die "docker is not installed or not on PATH"

# Git Bash on Windows rewrites any argument that looks like a Unix path. That
# silently turns the container side of `-v host:/home/jethexa/...` into a
# Windows path, so the mount lands nowhere and the workspace looks empty.
# Switch that off, and give Docker a C:/... host path it understands instead.
ON_WINDOWS=0
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    ON_WINDOWS=1
    export MSYS_NO_PATHCONV=1
    REPO_ROOT="$(cd "$REPO_ROOT" && pwd -W)"
    ;;
esac

# The Gazebo<->ROS bridge package only exists for amd64, so on Apple Silicon
# build and run the amd64 image under Docker Desktop's emulation. Slower, but it
# is the exact image the project was tested with. Training does not happen in
# here anyway - MuJoCo runs natively on macOS.
PLATFORM_ARGS=()
if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
  PLATFORM_ARGS=(--platform linux/amd64)
fi

need_image() {
  docker image inspect "$IMAGE" >/dev/null 2>&1 \
    || die "image $IMAGE not found - run: tools/docker_run.sh build"
}

build() {
  # Match the host user so files in the mounted repo are not root-owned - but
  # only on Linux, as a normal user. Everywhere else 1000 is right:
  #   Windows: Git Bash reports a synthetic UID like 197609.
  #   macOS:   UID 501 / GID 20, and GID 20 is 'dialout' in Ubuntu. Docker
  #            Desktop on Windows and macOS doesn't map file ownership anyway.
  #   root:    `sudo tools/docker_run.sh build` would pass UID 0, which already
  #            exists, so no jethexa user would be created at all.
  local uid=1000 gid=1000
  if [ "$(uname -s)" = "Linux" ] && [ "$(id -u)" != "0" ]; then
    uid="$(id -u)"
    gid="$(id -g)"
  fi
  echo "building $IMAGE from $REPO_ROOT (uid $uid)"
  if [ "${#PLATFORM_ARGS[@]}" -gt 0 ]; then
    echo "Apple Silicon: building the amd64 image under emulation (expect ~1 hour)."
    echo "Turn on 'Use Rosetta for x86_64/amd64 emulation' in Docker Desktop first."
  fi
  docker build ${PLATFORM_ARGS[@]+"${PLATFORM_ARGS[@]}"} \
    -f "$REPO_ROOT/tools/Dockerfile" \
    --build-arg "UID=$uid" \
    --build-arg "GID=$gid" \
    -t "$IMAGE" \
    "$REPO_ROOT"
  echo
  echo "built $IMAGE. Now: tools/docker_run.sh shell"
}

# Arguments every run needs.
#   --shm-size: ROS 2 and Gazebo use shared memory; Docker's 64 MB default
#     causes crashes that look like random node failures.
RUN_ARGS=(
  ${PLATFORM_ARGS[@]+"${PLATFORM_ARGS[@]}"}
  --rm
  --shm-size=1g
  -v "$REPO_ROOT/jethexa_sim:/home/jethexa/jethexa_ws/src/jethexa_sim"
  -e "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-42}"
)

shell_run() {
  need_image
  docker run -it --name "$CONTAINER" "${RUN_ARGS[@]}" "$IMAGE" bash -l
}

gui_run() {
  need_image
  local extra=()
  if [ -n "${DISPLAY:-}" ] && [ -d /tmp/.X11-unix ]; then
    # Linux host with X11. xhost is the usual missing piece.
    echo "forwarding X11 on DISPLAY=$DISPLAY"
    if command -v xhost >/dev/null; then
      xhost +local:docker >/dev/null 2>&1 || true
    else
      echo "note: xhost not found; if the GUI is refused, install x11-xserver-utils"
    fi
    extra=(-e "DISPLAY=$DISPLAY" -v /tmp/.X11-unix:/tmp/.X11-unix)
  else
    echo "no X11 socket found. On Windows or macOS, run the sim headless:"
    echo "  ros2 launch jethexa_sim jethexa_gazebo.launch.py gui:=false"
    echo "continuing without GUI forwarding."
  fi
  # ${arr[@]+...} rather than "${arr[@]}": macOS ships bash 3.2, where set -u
  # treats an empty array as unbound and would kill the script right here.
  docker run -it --name "$CONTAINER" "${RUN_ARGS[@]}" ${extra[@]+"${extra[@]}"} "$IMAGE" bash -l
}

run_cmd() {
  need_image
  [ $# -gt 0 ] || die "usage: tools/docker_run.sh run <command...>"
  # No -it and no fixed name: there may be no terminal (scripts, CI), and
  # several of these can run at once.
  docker run "${RUN_ARGS[@]}" "$IMAGE" bash -lc "$*"
}

case "$CMD" in
  build) build ;;
  shell) shell_run ;;
  gui)   gui_run ;;
  run)   shift; run_cmd "$@" ;;
  *)     die "unknown command '$CMD' (expected: build, shell, gui, run)" ;;
esac
