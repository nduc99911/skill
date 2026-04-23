#!/bin/bash

WORKSPACE="/root/.openclaw/workspace"
PUBLISHER_SCRIPT="$WORKSPACE/scripts/publisher.py"
LOG="$WORKSPACE/state/publish.log"
ERR="$WORKSPACE/state/publish_error.log"

mkdir -p "$WORKSPACE/state"

/usr/bin/python3 "$PUBLISHER_SCRIPT" >> "$LOG" 2>> "$ERR"
