#!/bin/zsh
# Force Godot to reimport the given res files (no editor/MCP needed), headless. Usage: reimport.sh hands/art/hand_r.glb ...
# A plain rescan or touch is not enough: Godot skips files whose .md5 still matches, so drop the md5 first.
set -e
cd "${0:A:h}/../.."
for f in "$@"; do
  find .godot/imported -name "${f:t}-*.md5" -delete 2>/dev/null || true
  touch "$f"
done
perl -e 'alarm 180; exec @ARGV' /Applications/Godot.app/Contents/MacOS/Godot --headless --path . --import 2>&1 \
  | sed 's/\x1b\[[0-9;]*m//g' | grep -E "reimport \| [^ ]+\.(glb|gltf)|SCRIPT ERROR|ERROR: [^R]" | grep -v "RID\|leaked" || true
echo "REIMPORT done: $#"
