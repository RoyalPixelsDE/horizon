#!/bin/bash
# hz_check.sh name=ref[@worktree]:harness,harness ... - pr_ready --quick plus named harnesses per ref.
set -u
MAIN=$HOME/projects/royalpixels/horizon
O=$HOME/.cache/horizon-build/prready; mkdir -p "$O"
for spec in "$@"; do
  name=${spec%%=*}; rest=${spec#*=}; refpart=${rest%%:*}; harnesses=${rest#*:}; [ "$harnesses" = "$rest" ] && harnesses=
  ref=${refpart%%@*}; src=$MAIN; [ "$refpart" != "$ref" ] && src=${refpart#*@}
  [ "$src" = "$MAIN" ] && git -C "$MAIN" checkout -q --detach "$ref"
  start=$(date +%s)
  ~/worldgen-cmp/scripts/hz_run.sh "$src" 'python3 tools/pr_ready.py --quick --base upstream/main' >"$O/$name.md" 2>"$O/$name.log"
  rc=$?; line="$name $(git -C "$src" rev-parse --short HEAD) pr_ready=$rc"
  for h in ${harnesses//,/ }; do
    ~/worldgen-cmp/scripts/hz_run.sh "$src" "python3 tools/test_${h}_parity.py" >"$O/$name.$h.log" 2>&1
    line="$line $h=$?"
  done
  echo "$line $(( ($(date +%s)-start)/60 ))min" | tee -a "$O/summary.txt"
done
