#!/bin/zsh
# Cockpit seat view at every supported aspect plus one contact sheet. Usage:
#   aspects.sh NAME [preview args...]      e.g. aspects.sh notes --extra res://previews/cockpit_v2/today_fill.tscn
#   ASPECTS_43=1 aspects.sh NAME ...       also 4:3 (outside the locked 16:10-21:9 frame: a bars check only)
# Writes previews/cockpit_v2/screenshots/NAME_{169,deck,219}.png and NAME.png: 16:9 1920x1080, 16:10 / Steam Deck
# 1280x800, 21:9 2520x1080 (the user locked the frame to 16:10-21:9, with bars outside). Extra args reach the preview and
# its --extra scene, and their result lines are printed (e.g. --stick 24 prints KNOB_VS_LABEL per aspect).
cd "${0:A:h}/../.."
G=/Applications/Godot.app/Contents/MacOS/Godot
D=$PWD/previews/cockpit_v2/screenshots
name=$1; shift
shots=()
set=(169 1920x1080 deck 1280x800 219 2520x1080)
[[ -n $ASPECTS_43 ]] && set+=(43 1440x1080)
for tag size in $set; do
  perl -e 'alarm 120; exec @ARGV' $G --path . res://previews/cockpit_v2/cockpit_v2_preview.tscn -- \
    --capture ${name}_$tag --size $size "$@" 2>&1 | grep -E "SCRIPT ERROR|^[A-Z_]{4,} " | grep -v COCKPIT_V2_CAPTURE | sed "s/^/[$tag] /"
  rm -f $D/${name}_$tag-overlay.png $D/${name}_$tag-overlay.png.import
  shots+=($D/${name}_$tag.png)
done
$G --headless -s scripts/tools/sheet.gd -- $D/$name.png 800 2 $shots 2>&1 | grep -E "SHEET|ERROR"
