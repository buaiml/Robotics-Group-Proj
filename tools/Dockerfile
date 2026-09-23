# JetHexa development environment: Ubuntu 22.04 + ROS 2 Humble + Gazebo Harmonic.
#
# Build from the repo root, not from tools/:
#   docker build -f tools/Dockerfile -t jethexa:humble .
#
# See docs/setup.md for running it.

FROM ubuntu:22.04

# Same provisioning script the WSL and native installs use. It detects that it
# is in a container and skips the login account and /etc/wsl.conf accordingly.
# Extra root CAs, for machines where antivirus or a proxy intercepts HTTPS.
# Usually this folder holds only a README and nothing happens. See
# tools/extra-ca/README.md. The provisioning script trusts any *.crt here.
COPY tools/extra-ca/ /usr/local/share/ca-certificates/extra/

COPY tools/provision_ubuntu2204.sh /tmp/provision.sh
# Strip CR first. .gitattributes forces LF, but a checkout made before it
# existed, with core.autocrlf=true, still has CRLF, and bash then fails on its
# first line with "set: pipefail\r: invalid option name".
#
# JETHEXA_ENV=docker is required, not decoration: inside `docker build` there
# is no /.dockerenv, and on Docker Desktop the kernel reports "microsoft", so
# the script's own detection concludes it is in WSL and would bake a login user
# and /etc/wsl.conf into the image.
RUN sed -i 's/\r$//' /tmp/provision.sh \
 && JETHEXA_ENV=docker bash /tmp/provision.sh \
 && rm -f /tmp/provision.sh

# Non-root user, so files created in a mounted workspace are not owned by root
# on the host. UID 1000 matches the first user on most Linux desktops; override
# at build time if yours differs:
#   docker build --build-arg UID=1001 ...
ARG UID=1000
ARG GID=1000
ARG USERNAME=jethexa
# The group may legitimately exist already (it's fine to join it), but the user
# must not fail quietly: with a swallowed error, the build instead dies several
# steps later at `USER jethexa` with a message that points nowhere near here.
RUN (getent group "${GID}" >/dev/null || groupadd -g "${GID}" "${USERNAME}") \
 && if getent passwd "${UID}" >/dev/null; then \
      echo "ERROR: UID ${UID} already belongs to '$(getent passwd "${UID}" | cut -d: -f1)' in the base image." >&2; \
      echo "Rebuild with --build-arg UID=1000 (tools/docker_run.sh build picks this for you)." >&2; \
      exit 1; \
    fi \
 && useradd -m -u "${UID}" -g "${GID}" -s /bin/bash "${USERNAME}" \
 && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" \
 && chmod 0440 "/etc/sudoers.d/${USERNAME}" \
 && printf '%s:%s\n' "${USERNAME}" ' ' | chpasswd

# The environment the provisioner installed applies to login shells. Containers
# often start non-login shells, so source it from .bashrc too.
RUN echo '. /etc/profile.d/jethexa.sh' >> "/home/${USERNAME}/.bashrc" \
 && chown "${UID}:${GID}" "/home/${USERNAME}/.bashrc"

# Create the workspace BEFORE switching user. WORKDIR creates missing
# directories as root even when USER is set, which would leave the workspace
# unwritable by the very user meant to build in it.
RUN mkdir -p "/home/${USERNAME}/jethexa_ws/src"  && chown -R "${UID}:${GID}" "/home/${USERNAME}/jethexa_ws"

USER ${USERNAME}
WORKDIR /home/${USERNAME}/jethexa_ws

# Start in a login shell so ROS and Gazebo are already on PATH.
SHELL ["/bin/bash", "-lc"]
CMD ["bash", "-l"]
