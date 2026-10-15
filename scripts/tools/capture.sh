#!/bin/zsh
# Render cockpit views with a separate Godot process (never the editor). Usage:
#   capture.sh NAME [--size 1200x675] [--extra res://...tscn] [--shots "seat;left@x,y,z@x,y,z;..."] [--eye ... --look ...]
# With --shots: one process renders every view and writes previews/cockpit_v2/screenshots/NAME.png as a contact sheet.
cd "${0:A:h}/../.."
LOG=${TMPDIR:-/tmp}/cockpit_capture.log
perl -e 'alarm 120; exec @ARGV' /Applications/Godot.app/Contents/MacOS/Godot --path . \
  res://previews/cockpit_v2/cockpit_v2_preview.tscn -- --capture "$1" "${@:2}" > $LOG 2>&1
grep -E "COCKPIT_V2_(CAPTURE|SHEET)|SCRIPT ERROR|ERROR: [^R]" $LOG | grep -v "RID\|leaked" | head -20
