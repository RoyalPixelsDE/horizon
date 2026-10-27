#!/bin/bash
# serve.sh vanilla|paper WORLD_DIR RUN_DIR PORT  - copy a world, start a server with a FIFO console in the background.
# Send commands: echo "cmd" > RUN_DIR/console ; output: RUN_DIR/server.log
set -eu
DL=~/worldgen-cmp/dl
type=$1 world=$2 run=$3 port=$4
rm -rf "$run"; mkdir -p "$run"; cp -r "$world" "$run/world"
cd "$run"
echo eula=true > eula.txt
printf 'online-mode=false\nserver-port=%s\nmax-tick-time=-1\nview-distance=6\nsimulation-distance=4\nspawn-protection=0\n' "$port" > server.properties
jar=$DL/mc/server-26.3.jar; [ "$type" = paper ] && jar=$DL/paper-26.3-223.jar
mkfifo console
# the read-write open keeps the FIFO alive between writers, so no tail -f wrapper is needed
nohup bash -c "exec 3<>console; exec $DL/jdk/bin/java -Xmx3G -jar $jar nogui <&3 > server.log 2>&1" >/dev/null 2>&1 &
echo $! > server.pid
until grep -q 'Done (' server.log 2>/dev/null; do sleep 1; done
echo ready
