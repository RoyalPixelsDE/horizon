#!/bin/bash
# 3 seeds x (vanilla, vanilla again, Paper+Chunky, Horizon 0.2.69, Horizon with our fixes), 1000 x 1000 blocks,
# all dimensions. Worlds stay in runs/r3-*; results in results/r3b/.
set -u
cd ~/worldgen-cmp
R=500; PLAYER=$1
SEEDS="12345 1 8675309"
mkdir -p results/r3b
hz() { # binaries resources dir [gen.py args]
  HZ_DIR=$1 HZ_RESOURCES=$2 python3 -I scripts/gen.py horizon $S $R $3 "${@:4}" > $3.out 2>&1
}
for S in $SEEDS; do
  echo "== seed $S $(date +%T)"
  V=runs/r3-vanilla-$S
  [ -f $V/stats.json ] || { rm -rf $V; python3 -I scripts/gen.py vanilla $S $R $V > $V.out 2>&1 || exit 1; }
  for p in vanilla2 paper hz069 hznew; do
    W=runs/r3-$p-$S
    if [ ! -f $W/stats.json ]; then
      rm -rf $W
      case $p in
        vanilla2) python3 -I scripts/gen.py vanilla $S $R $W > $W.out 2>&1 ;;
        paper) python3 -I scripts/gen.py paper $S $R $W > $W.out 2>&1 ;;
        hz069) hz $PWD/dl/hz-0.2.69/horizon-server-linux-x86_64 $PWD/dl/hz-0.2.69/horizon-server-linux-x86_64/.local/horizon-client/26.3 $W --player $PLAYER ;;
        hznew) hz $PWD/dl/hz-next/bin $HOME/projects/royalpixels/horizon/.local/horizon-client/26.3 $W ;;
      esac || { echo "gen $p $S failed"; exit 1; }
    fi
    [ -f results/r3b/$S-v-$p.json ] || python3 -I scripts/compare.py $V/world $W/world results/r3b/$S-v-$p.json --radius $R --jobs 10 >/dev/null 2>&1 || { echo "compare $p $S failed"; exit 1; }
    python3 -I scripts/check_fixes.py $W/world > results/r3b/$S-$p-fixes.txt 2>&1
    echo "  $p done $(date +%T)"
  done
  python3 -I scripts/check_fixes.py $V/world > results/r3b/$S-vanilla-fixes.txt 2>&1
  for p in paper hz069 hznew; do
    [ -f results/r3b/$S-loot-$p.json ] || python3 -I scripts/loot_check.py $V/world runs/r3-$p-$S/world $R runs/r3-loot-work results/r3b/$S-loot-$p.json > /dev/null 2>&1 || echo "loot $p $S failed"
  done
  rm -rf runs/r3-loot-work
  df -h ~ | tail -1
done
echo ALL DONE $(date +%T)
