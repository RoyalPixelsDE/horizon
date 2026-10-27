#!/bin/bash
# con.sh RUN_DIR WAIT_S CMD...  - send console commands, print the log lines they produced.
run=$1 wait=$2; shift 2
n=$(wc -l < "$run/server.log")
for c in "$@"; do echo "$c" > "$run/console"; done
sleep "$wait"
tail -n +$((n + 1)) "$run/server.log" | sed -E 's/^\[[0-9:]+ INFO\]: //; s/^\[[0-9:]+\] \[Server thread\/INFO\]: //' | cut -c1-400
