#!/bin/zsh
# Faces sheet: every expression on a base, one close-up per face (+ an optional ~60 px-face row).
# Usage: faces_sheet.sh NAME BASE [fov] [eye_y] [tile WxH] [cols]   (screenshots/NAME.png)
cd "${0:A:h}/../.."
F=(rest neutral happy alarm dazed panic sleepy embarrassed wink surprised)
n=${#F}; sp=0.55; y=${4:-1.56}
S=""
for i in {1..$n}; do
  x=$(( ((n - 1) / 2.0 - (i - 1)) * sp ))
  S="$S;${F[$i]}@$x,$y,-1.3@$x,$y,0@${3:-14}"
done
scripts/tools/godot_bg.sh --timeout 240 --path . res://previews/characters/mock_preview.tscn -- --capture $1 --stage flat \
  --models $2 --faces ${(j:,:)F} --spacing $sp --size ${5:-400x400} --cols ${6:-5} --shots "${S#;}" 2>&1 \
  | grep -E "SCRIPT ERROR|SHEET" | sed 's/.*screenshots\//  /'
