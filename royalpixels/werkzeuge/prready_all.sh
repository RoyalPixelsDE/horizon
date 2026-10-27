#!/bin/bash
# prready_all.sh BRANCH[:BASE]... - run upstream's pr_ready --quick per branch in the builder container.
# SRC (default the main clone) may be a worktree; BASE defaults to upstream/main. One log per branch.
SRC=${SRC:-$HOME/projects/royalpixels/horizon}
MAIN=$HOME/projects/royalpixels/horizon
B=$HOME/.cache/horizon-build
TARGET=${TARGET:-$B/target}
cd "$SRC" || exit 1
for arg in "$@"; do
  b=${arg%%:*}; base=upstream/main; [ "$arg" != "$b" ] && base=${arg#*:}
  git checkout -q "$b" || exit 1
  log=~/worldgen-cmp/prready/${b//\//_}.log
  docker run --rm --cpus=6 -u "$(id -u):$(id -g)" -v "$SRC":/src -v "$MAIN/.git":"$MAIN/.git" \
    -v "$B/cargo":/cargo -v "$TARGET":/target \
    -e CARGO_HOME=/cargo -e CARGO_TARGET_DIR=/target -e HOME=/tmp -w /src horizon-builder \
    bash -c "git config --global --add safe.directory '*'; python3 tools/pr_ready.py --base $base --quick" >"$log" 2>&1
  echo "$b exit=$?" | tee -a ~/worldgen-cmp/prready/summary.txt
done
