#!/bin/bash
# Generate the stronghold, fortress and bastion boxes of each seed in vanilla, a second vanilla run and Horizon.
set -u; cd ~/worldgen-cmp
R=$HOME/projects/royalpixels/horizon/.local/horizon-client/26.3
for s in 12345 1 8675309; do
  for p in vanilla vanilla2 horizon; do
    d=runs/speedrun/$p-$s; rm -rf $d; mkdir -p runs/speedrun
    plat=$p; [ $p = vanilla2 ] && plat=vanilla
    HZ_DIR=$PWD/dl/hz-next/bin HZ_RESOURCES=$R timeout 3000 python3 -I scripts/gen.py $plat $s 0 $d --boxes results/speedrun/boxes-$s.json --dims 0,1 > $d.out 2>&1
    echo "$s $p $? $(date +%T)"
  done
done
