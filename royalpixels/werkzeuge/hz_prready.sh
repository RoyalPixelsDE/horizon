#!/bin/bash
# hz_prready.sh name=ref ... - run tools/pr_ready.py --base upstream/main for each ref in the builder container.
# Output: ~/.cache/horizon-build/prready/<name>.md (the PR block) and <name>.log (progress), plus a summary line.
set -u
SRC=$HOME/projects/royalpixels/horizon
B=$HOME/.cache/horizon-build
O=$B/prready
cd "$SRC"
for pair in "$@"; do
  name=${pair%%=*}; ref=${pair#*=}
  git checkout -q --detach "$ref" || { echo "$name checkout failed"; continue; }
  start=$(date +%s)
  docker run --rm -u "$(id -u):$(id -g)" -v "$SRC":/src -v "$HOME/.jdks/jdk-25.0.4+7":/jdk \
    -v "$B/cargo":/cargo -v "$B/target":/target -e CARGO_HOME=/cargo -e CARGO_TARGET_DIR=/target -e HOME=/tmp \
    -e PATH=/jdk/bin:/usr/local/cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    -w /src horizon-builder bash -c 'git config --global --add safe.directory "*"; python3 tools/pr_ready.py --base upstream/main' \
    >"$O/$name.md" 2>"$O/$name.log"
  rc=$?
  echo "$name $(git rev-parse --short HEAD) exit=$rc $(( ($(date +%s)-start)/60 ))min" | tee -a "$O/summary.txt"
done
