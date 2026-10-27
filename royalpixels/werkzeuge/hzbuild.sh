#!/bin/bash
# hzbuild.sh [cargo args...] - build Horizon in a Rust container (ALSA/udev headers there, not on the host).
# Without args: the server build as packaging/server/Dockerfile does it, plus horizon-prepare, copied to
# ~/.cache/horizon-build/dist (horizon-engine, horizon-server, horizon-prepare, research-lock.json).
set -eu
SRC=${HZ_SRC:-$HOME/projects/royalpixels/horizon}
B=$HOME/.cache/horizon-build
find "$SRC" -path "$SRC/.local" -prune -o \( -name "*.rs" -o -name Cargo.toml \) -print0 | xargs -0 touch
run() {
  docker run --rm -u "$(id -u):$(id -g)" -v "$SRC":/src -v "$B/cargo":/cargo -v "$B/target":/target \
    -e CARGO_HOME=/cargo -e CARGO_TARGET_DIR=/target -w /src horizon-builder cargo "$@"
}
if [ $# -gt 0 ]; then run "$@"; exit; fi
run build --release --locked -p horizon-client --no-default-features --bin horizon-client
run build --release --locked -p horizon-server --bin horizon-server
run build --release --locked -p horizon-prepare --bin horizon-prepare
mkdir -p "$B/dist"
cp "$B/target/release/horizon-client" "$B/dist/horizon-engine"
cp "$B/target/release/horizon-server" "$B/target/release/horizon-prepare" "$B/dist/"
cp "$SRC/research-lock.json" "$B/dist/"
