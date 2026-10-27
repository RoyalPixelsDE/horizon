#!/bin/bash
# Release build + package of ~/.cache/hz-next, 3-seed parity rerun, mob comparison, /pregen speed runs.
set -u; O=$HOME/.cache/horizon-build/run12; mkdir -p $O; rm -f $O/summary.txt
log() { echo "$* $(date +%T)" >> $O/summary.txt; }
HZ_SRC=~/.cache/hz-next ~/worldgen-cmp/scripts/hzbuild.sh > $O/build.log 2>&1 || { log "build failed"; exit 1; }
log "build ok"
rm -rf ~/worldgen-cmp/dl/hz-next/bin && cp -r ~/.cache/horizon-build/dist ~/worldgen-cmp/dl/hz-next/bin
~/worldgen-cmp/scripts/hz_run.sh ~/.cache/hz-next 'set -e; cargo build --release --locked -p horizon-client --no-default-features --features mods --bin horizon-client 2>&1 | tail -1; cargo build --release --locked -p horizon-prepare 2>&1 | tail -1; bundle=$(/target/release/horizon-prepare compile-exporters --root "$PWD" | tail -1); rm -rf exporters; mkdir -p exporters; cp -R "$bundle/server" "$bundle/client" "$bundle/manifest.json" exporters/; f=/target/pkg/horizon-server-linux-x86_64; rm -rf /target/pkg; mkdir -p /target/pkg; cargo run --release --locked -p xtask -- package-server /target/release/horizon-client $f 2>&1 | tail -1; $f/horizon-engine --help | grep -q -- --resources && echo engine-ok; cd /target/pkg && tar czf horizon-server-linux-x86_64.tar.gz horizon-server-linux-x86_64 && sha256sum horizon-server-linux-x86_64.tar.gz > horizon-server-linux-x86_64.tar.gz.sha256 && ls -l' > $O/package.log 2>&1 && log "package ok" || log "package failed"
cd ~/worldgen-cmp
rm -rf runs/r3-hznew-* results/r3b/*-hznew-* results/r3b/*-v-hznew.json results/r3b/*-loot-hznew.json
scripts/r3.sh none > $O/r3.txt 2>&1; log "r3 done"
R=$HOME/projects/royalpixels/horizon/.local/horizon-client/26.3
for s in 12345 1 8675309; do
  d=runs/mobs/horizon-$s; rm -rf $d
  GEN_SPAWN_MOBS=1 HZ_DIR=$PWD/dl/hz-next/bin HZ_RESOURCES=$R python3 -I scripts/gen.py horizon $s 256 $d --dims 0 > $d.out 2>&1
  echo "mobs $s $(python3 -I scripts/animals.py runs/mobs/vanilla-$s/world $d/world 15 | tail -1) vanilla2: $(python3 -I scripts/animals.py runs/mobs/vanilla-$s/world runs/mobs/vanilla2-$s/world 15 | tail -1)" >> $O/summary.txt
done
for s in 12345 1 8675309; do
  d=runs/perf/pregen-$s; rm -rf $d
  HZ_DIR=$PWD/dl/hz-next/bin HZ_RESOURCES=$R python3 -I scripts/gen.py horizon $s 500 $d --pregen > $d.out 2>&1
  log "pregen $s $(tail -1 $d.out | cut -c1-400)"
done
log "ALL DONE"
