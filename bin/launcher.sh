#!/usr/bin/env bash
# launcher.sh
# Stop all docker containers and start them again

export ALBERTO_HOME_DIR="$HOME/alberto"
export PATH="$PATH:$ALBERTO_HOME_DIR/bin"

echo "Restarting via script"
alberto restart