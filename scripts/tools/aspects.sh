#!/bin/zsh
# Cockpit seat view at every target aspect plus one contact sheet. Usage:
#   aspects.sh NAME [preview args...]      e.g. aspects.sh notes --extra res://previews/cockpit_v2/today_fill.tscn
# Writes previews/cockpit_v2/screenshots/NAME_{169,43,219,deck}.png and NAME.png (2x2 sheet):
# 16:9 1920x1080, 4:3 1440x1080, 21:9 2520x1080, Steam Deck 1280x800. Extra args reach the preview and its --extra
# scene, and their result lines are printed (e.g. --stick 24 prints KNOB_VS_LABEL per aspect).
cd "${0:A:h}/../.."
G=/Applications/Godot.app/Contents/MacOS/Godot
D=$PWD/previews/cockpit_v2/screenshots
name=$1; shift
shots=()
for tag size in 169 1920x1080 43 1440x1080 219 2520x1080 deck 1280x800; do
  perl -e 'alarm 120; exec @ARGV' $G --path . res://previews/cockpit_v2/cockpit_v2_preview.tscn -- \
    --capture ${name}_$tag --size $size "$@" 2>&1 | grep -E "SCRIPT ERROR|^[A-Z_]{4,} " | grep -v COCKPIT_V2_CAPTURE | sed "s/^/[$tag] /"
  rm -f $D/${name}_$tag-overlay.png $D/${name}_$tag-overlay.png.import
  shots+=($D/${name}_$tag.png)
done
$G --headless -s scripts/tools/sheet.gd -- $D/$name.png 800 2 $shots 2>&1 | grep -E "SHEET|ERROR"
