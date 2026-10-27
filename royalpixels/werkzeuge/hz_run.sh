#!/bin/bash
# hz_run.sh <src-dir> <command...> - run a command in the builder container on a checkout, with the main
# clone's .local (vanilla data) and the host JDK; shared cargo cache and target dir.
set -u
SRC=$1; shift
MAIN=$HOME/projects/royalpixels/horizon
B=$HOME/.cache/horizon-build
GITDIR=$(git -C "$SRC" rev-parse --git-common-dir)
GITDIR=$(cd "$SRC" && cd "$GITDIR" && pwd)
# Every worktree is /src in the container and they share one target dir: fresh mtimes make cargo rebuild
# this tree's own crates instead of reusing another tree's.
find "$SRC" -path "$SRC/.local" -prune -o \( -name "*.rs" -o -name Cargo.toml \) -print0 | xargs -0 touch
docker run --rm -u "$(id -u):$(id -g)" -v "$SRC":/src -v "$MAIN/.local":/src/.local -v "$GITDIR":"$GITDIR" \
  -v "$HOME/.jdks/jdk-25.0.4+7":/jdk -v "$B/cargo":/cargo -v "$B/target":/target \
  -e CARGO_HOME=/cargo -e CARGO_TARGET_DIR=/target -e HOME=/tmp -e HORIZON_TEST_RESOURCES=/src/.local/horizon-client/26.3 \
  -e PATH=/jdk/bin:/usr/local/cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  -w /src horizon-builder bash -c 'git config --global --add safe.directory "*"; '"$*"
