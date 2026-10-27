#!/bin/bash
# hz_tests.sh SRC BRANCH CARGO_TEST_ARGS... - run horizon-client tests with HORIZON_TEST_RESOURCES set,
# so tests that skip without the game data really run. Output ends with the test summary lines.
SRC=$1 BRANCH=$2; shift 2
MAIN=$HOME/projects/royalpixels/horizon
B=$HOME/.cache/horizon-build
TARGET=${TARGET:-$B/target}
git -C "$SRC" checkout -q "$BRANCH" || exit 1
docker run --rm --cpus=6 -u "$(id -u):$(id -g)" -v "$SRC":/src -v "$MAIN/.local":/src/.local \
  -v "$MAIN/.git":"$MAIN/.git" -v "$B/cargo":/cargo -v "$TARGET":/target \
  -e CARGO_HOME=/cargo -e CARGO_TARGET_DIR=/target -e HOME=/tmp \
  -e HORIZON_TEST_RESOURCES=/src/.local/horizon-client/26.3 -w /src horizon-builder \
  cargo test -q -p horizon-client "$@" 2>&1 | grep -E "^test |test result|panicked|error(\[|:)" | tail -25
