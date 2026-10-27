#!/bin/bash
# hz_harness.sh SRC HARNESS... - run Horizon parity harnesses from checkout SRC in the builder container,
# with the main clone's .local and the host JDK 25; own target dir per checkout.
set -u
SRC=$1; shift
MAIN=$HOME/projects/royalpixels/horizon
B=$HOME/.cache/horizon-build
docker run --rm --cpus=6 -u "$(id -u):$(id -g)" -v "$SRC":/src -v "$MAIN/.local":/src/.local -v "$MAIN/.git":"$MAIN/.git" \
  -v "$HOME/.jdks/jdk-25.0.4+7":/jdk -v "$B/cargo":/cargo -v "$B/target-split":/target \
  -e CARGO_HOME=/cargo -e CARGO_TARGET_DIR=/target -e HOME=/tmp -e PATH=/jdk/bin:/usr/local/cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  -w /src horizon-builder bash -c 'git config --global --add safe.directory "*"; for h in "$@"; do python3 tools/test_${h}_parity.py; echo "$h exit=$?"; done' _ "$@"
