#!/bin/bash
# stop.sh RUN_DIR - stop a server started by serve.sh and wait for it to exit.
pid=$(cat "$1/server.pid"); echo stop > "$1/console"
while kill -0 "$pid" 2>/dev/null; do sleep 1; done
