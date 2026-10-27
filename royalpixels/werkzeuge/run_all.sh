#!/bin/bash
# Full matrix: 5 seeds x 3 platforms, 10,000 x 10,000 blocks, all dimensions. Keeps at most two worlds on disk.
set -u
cd ~/worldgen-cmp
R=5000
PLAYER=$1
SEEDS="12345 1 8675309 -1234567890123456789 4815162342"
mkdir -p results/full
for S in $SEEDS; do
  V=runs/full-vanilla-$S P=runs/full-paper-$S H=runs/full-horizon-$S
  [ -f results/full/$S-done ] && continue
  echo "== seed $S $(date)"
  [ -f $V/stats.json ] || { rm -rf $V; python3 -I scripts/gen.py vanilla $S $R $V > $V.out 2>&1 || exit 1; }
  if [ "$S" = 12345 ] && [ ! -f results/full/$S-v-v2.json ]; then
    V2=runs/full-vanilla2-$S
    python3 -I scripts/gen.py vanilla $S $R $V2 > $V2.out 2>&1 || exit 1
    cp $V2/stats.json results/full/$S-vanilla2-stats.json
    python3 -I scripts/compare.py $V/world $V2/world results/full/$S-v-v2.json --radius $R --jobs 10 || exit 1
    rm -rf $V2
  fi
  if [ ! -f results/full/$S-v-p.json ]; then
    rm -rf $P; python3 -I scripts/gen.py paper $S $R $P > $P.out 2>&1 || exit 1
    cp $P/stats.json results/full/$S-paper-stats.json
    python3 -I scripts/compare.py $V/world $P/world results/full/$S-v-p.json --radius $R --jobs 10 || exit 1
    rm -rf $P
  fi
  if [ ! -f results/full/$S-v-h.json ]; then
    rm -rf $H; python3 -I scripts/gen.py horizon $S $R $H --player $PLAYER > $H.out 2>&1 || exit 1
    cp $H/stats.json results/full/$S-horizon-stats.json
    python3 -I scripts/compare.py $V/world $H/world results/full/$S-v-h.json --radius $R --jobs 10 || exit 1
  fi
  cp $V/stats.json results/full/$S-vanilla-stats.json
  python3 -I scripts/loot_check.py $V/world $H/world $R $V results/full/$S-loot-v-h.json || exit 1
  rm -rf $V $H
  touch results/full/$S-done
  df -h ~ | tail -1
done
echo ALL DONE $(date)
