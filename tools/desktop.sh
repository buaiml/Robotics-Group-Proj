#!/usr/bin/env bash
# See the simulator's windows in a web browser.
#
# For containers (Docker on a Mac especially), where there is no screen for
# Gazebo to open a window on. This starts a virtual screen inside the
# container and serves it to your browser:
#
#   bash tools/desktop.sh          then open  http://localhost:6080/vnc.html
#
# then, in every terminal you launch GUI programs from:
#
#   export DISPLAY=:1 LIBGL_ALWAYS_SOFTWARE=1
#
# The container must publish the port (-p 127.0.0.1:6080:6080);
# `tools/docker_run.sh gui` does that, and starts this script for you.
#
# Why not forward the window to the Mac directly with XQuartz? XQuartz only
# offers OpenGL 2.1, and Gazebo's renderer needs 3.3 or newer. Inside the
# container, Mesa's software renderer provides 4.5. It's slower than a GPU, but
# it works on every machine.
#
# Safe to run again: it only starts what isn't already running. Everything runs
# detached (setsid), so closing this terminal doesn't take the screen with it.
set -euo pipefail

PORT="${JETHEXA_DESKTOP_PORT:-6080}"
DISP="${JETHEXA_DESKTOP_DISPLAY:-:1}"
GEOMETRY="${JETHEXA_DESKTOP_GEOMETRY:-1600x900}"
N="${DISP#:}"
VNC_PORT=$((5900 + N))

SUDO=""
if [ "$(id -u)" != "0" ]; then
  command -v sudo >/dev/null || { echo "ERROR: run as root, or install sudo" >&2; exit 1; }
  SUDO="sudo"
fi

# Is something answering on this port? (bash's /dev/tcp: no extra tools needed)
listening() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

# --- packages (already in the jethexa image; installed here for anyone else) ---
need=()
for p in tigervnc-standalone-server novnc python3-websockify openbox; do
  dpkg -s "$p" >/dev/null 2>&1 || need+=("$p")
done
if [ "${#need[@]}" -gt 0 ]; then
  echo "installing: ${need[*]}"
  $SUDO apt-get update -qq
  $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends "${need[@]}" >/dev/null
fi

# --- the virtual screen ---
# Checked by its VNC port rather than /tmp/.X11-unix/X1: on some systems (WSL)
# that folder is read-only and the server listens on a hidden socket instead.
if ! listening "$VNC_PORT"; then
  # No password: the VNC port only listens inside the container (-localhost),
  # and the browser port is published to the host's loopback only.
  setsid -f Xvnc "$DISP" -geometry "$GEOMETRY" -depth 24 -SecurityTypes None \
       -localhost -rfbport "$VNC_PORT" -AlwaysShared >/tmp/jethexa-xvnc.log 2>&1
  for _ in $(seq 50); do listening "$VNC_PORT" && break; sleep 0.1; done
  if ! listening "$VNC_PORT"; then
    echo "ERROR: the virtual screen did not start; see /tmp/jethexa-xvnc.log" >&2
    exit 1
  fi
  echo "virtual screen $DISP started ($GEOMETRY)"
else
  echo "virtual screen $DISP already running"
fi
# A window manager, so windows get title bars and can be moved and resized.
if ! pgrep -x openbox >/dev/null; then
  DISPLAY="$DISP" setsid -f openbox >/tmp/jethexa-openbox.log 2>&1
fi

# --- the browser bridge ---
if ! listening "$PORT"; then
  setsid -f websockify --web /usr/share/novnc "$PORT" "localhost:$VNC_PORT" >/tmp/jethexa-novnc.log 2>&1
  for _ in $(seq 50); do listening "$PORT" && break; sleep 0.1; done
  if ! listening "$PORT"; then
    echo "ERROR: the browser bridge did not start; see /tmp/jethexa-novnc.log" >&2
    exit 1
  fi
  echo "browser bridge on port $PORT started"
else
  echo "browser bridge on port $PORT already running"
fi

cat <<EOF

Open in your browser:  http://localhost:$PORT/vnc.html?autoconnect=1&resize=remote

Then, in each terminal you start Gazebo or other windows from:
  export DISPLAY=$DISP LIBGL_ALWAYS_SOFTWARE=1
EOF
