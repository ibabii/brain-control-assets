#!/bin/zsh
# Render the bathroom look-dev (separate Godot process). Usage:
#   capture_bathroom.sh NAME [--human] [--fx] [--size 1200x675] [--shots "fp;reveal;name@eye@look[@fov];..."]
# Writes previews/bathroom/screenshots/NAME.png (2-column contact sheet).
cd "${0:A:h}/../.."
LOG=${TMPDIR:-/tmp}/bathroom_capture.log
scripts/tools/godot_bg.sh --timeout 150 --path . \
  res://previews/bathroom/bathroom_preview.tscn -- --capture "$1" "${@:2}" > $LOG 2>&1
grep -E "BATHROOM_SHEET|SCRIPT ERROR|ERROR: [^R]|Assertion" $LOG | grep -v "RID\|leaked" | head -20
