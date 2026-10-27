#!/bin/bash
# serve_hz.sh SEED RUN_DIR PORT - a fresh Horizon dedicated server with a FIFO console in the background (as serve.sh).
set -eu
HZ=~/worldgen-cmp/dl/hz-next/bin RES=~/projects/royalpixels/horizon/.local/horizon-client/26.3
seed=$1 run=$2 port=$3
rm -rf "$run"; mkdir -p "$run"
$HZ/horizon-server --dir "$run" init --eula --world world --seed "$seed" --port "$port" --no-whitelist --offline --yes >/dev/null
sed -i 's/every = "6h"/every = "0"/; s/bind = "127.0.0.1:8130"/bind = ""/' "$run/server.toml"
sed -i "s#resources = \"\"#resources = \"$RES\"#" "$run/server.toml"
cd "$run"; mkfifo console
nohup bash -c "exec 3<>console; exec $HZ/horizon-server --dir $PWD run <&3 > server.log 2>&1" >/dev/null 2>&1 &
echo $! > server.pid
until grep -q 'Done (' server.log 2>/dev/null; do sleep 1; done
echo ready
