#!/bin/zsh
# Render the Human look-dev (separate Godot process). Usage:
#   [SCENE=human_rig_preview] capture_human.sh NAME [--mode single|lineup|faces] [--size 1200x900] [--shots "name@eye@look[@fov];..."]
# Writes previews/human/screenshots/NAME.png (2-column contact sheet).
cd "${0:A:h}/../.."
LOG=${TMPDIR:-/tmp}/human_capture.log
perl -e 'alarm 120; exec @ARGV' /Applications/Godot.app/Contents/MacOS/Godot --path . \
  res://previews/human/${SCENE:-human_preview}.tscn -- --capture "$1" "${@:2}" > $LOG 2>&1
grep -E "HUMAN_SHEET|SCRIPT ERROR|ERROR: [^R]|Assertion" $LOG | grep -v "RID\|leaked" | head -20
