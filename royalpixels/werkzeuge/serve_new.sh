#!/bin/bash
# serve_new.sh SEED RUN_DIR PORT - a fresh vanilla 26.3 dedicated server with a FIFO console (as serve.sh, new world).
set -eu
DL=~/worldgen-cmp/dl seed=$1 run=$2 port=$3
rm -rf "$run"; mkdir -p "$run"; cd "$run"
echo eula=true > eula.txt
printf 'level-seed=%s\nonline-mode=false\nserver-port=%s\nmax-tick-time=-1\nspawn-protection=0\n' "$seed" "$port" > server.properties
mkfifo console
nohup bash -c "exec 3<>console; exec $DL/jdk/bin/java -Xmx3G -jar $DL/mc/server-26.3.jar nogui <&3 > server.log 2>&1" >/dev/null 2>&1 &
echo $! > server.pid
until grep -q 'Done (' server.log 2>/dev/null; do sleep 1; done
echo ready
