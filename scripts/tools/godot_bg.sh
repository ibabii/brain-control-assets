#!/bin/zsh
# Godot render runs without stealing focus: macOS `open -g` starts it in the background (never activated), the
# window goes off-screen, stdout/stderr come back here. Same args as Godot; `--path .` is made absolute.
# Usage: scripts/tools/godot_bg.sh [--timeout S] --path . res://scene.tscn -- args...
# Anything that needs no pixels should use `Godot --headless` instead.
T=240
[[ $1 == --timeout ]] && { T=$2; shift 2; }
args=()
prev=
for a in "$@"; do
  [[ $prev == --path && $a == . ]] && a=$PWD          # open starts the app in /
  args+=("$a"); prev=$a
done
tag=godotbg$$
(( ${args[(I)--]} )) || args+=(--)                    # the tag is a user arg (lets a timeout find the process)
args+=(--$tag)
out=$(mktemp -t godot_bg)
open -g -n -W -a /Applications/Godot.app --stdout $out --stderr $out --args --position 6000,6000 "${args[@]}" &
pid=$!
for _ in {1..$T}; do
  kill -0 $pid 2>/dev/null || break
  sleep 1
done
if kill -0 $pid 2>/dev/null; then
  pkill -f -- "--$tag"; echo "godot_bg: timeout after ${T}s"
fi
wait $pid 2>/dev/null
cat $out
rm -f $out
