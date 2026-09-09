#!/usr/bin/env bash
# Run this script ON the VM, once, right after creating it.
#
#   ./vm_setup.sh
#
# The Ubuntu ships without docker or uv
set -euo pipefail

INSTALL_DIR="/opt/inferapi"

sudo apt-get update
# rsync is how the code gets here from your laptop, so it has to exist on both ends.
sudo apt-get install -y screen make rsync ca-certificates curl

if ! command -v docker; then
    echo "Installing docker"
    curl -fsSL https://get.docker.com | sudo sh
    # The Docker daemon listens on a socket that belongs to the docker group.
    # We add the user to that group so that docker commands work without sudo.
    sudo usermod -aG docker "$USER"
else
    echo "Docker seems installed"
fi

if ! command -v uv; then
    echo "Installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh
else
    echo "uv seems installed"
fi

# /opt holds software not installed with a package manager
# It belongs to root, so we create a directory using sudo then change the owner
sudo mkdir -p "$INSTALL_DIR"
sudo chown "$USER:$USER" "$INSTALL_DIR"

echo
echo "Docker, uv, screen, rsync and make are installed."
echo "${INSTALL_DIR} exists and belongs to ${USER}."
echo "Log out and back in before running docker: group membership is read at login."
echo "If it doesn't work, you might need to reboot your VM!"
