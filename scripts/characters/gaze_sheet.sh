#!/bin/zsh
# Gaze limits sheet: one labelled face per direction at the rig json eye limits (look.eye_yaw / eye_pitch).
# Usage: gaze_sheet.sh NAME BASE eye_y   (screenshots/NAME.png; adds temporary g_* expressions to the head part.json,
# rebuilt away by the next build_char.sh)
cd "${0:A:h}/../.."
python3 - $2 <<'PY'
import json, sys
base = sys.argv[1]
lk = json.load(open(f'characters/{base}/art/{base}_rig.json'))['look']
Y, P = lk['eye_yaw'], lk['eye_pitch']
head = json.load(open(f'characters/{base}/art/character.json'))['parts']['head']
p = f'characters/parts/{head}/art/part.json'
j = json.load(open(p))
for n, (y, q) in dict(C=(0, 0), L=(Y, 0), R=(-Y, 0), U=(0, P), D=(0, -P), UL=(Y, P), UR=(-Y, P), DL=(Y, -P), DR=(-Y, -P)).items():
    j['expressions']['g_' + n] = {'show': [], 'brow': [0, 0], 'pupil': 1.0, 'look': [[y, q], [y, q]]}
json.dump(j, open(p, 'w'), indent=1)
PY
D=(UL U UR L C R DL D DR); n=9; sp=0.8; S=""; F=""
for i in {1..$n}; do
  x=$(( ((n - 1) / 2.0 - (i - 1)) * sp ))
  S="$S;${D[$i]}@$x,$3,-0.85@$x,$3,0@26"; F="$F,g_${D[$i]}"
done
scripts/tools/godot_bg.sh --timeout 240 --path . res://previews/characters/mock_preview.tscn -- --capture $1 --stage flat \
  --models $2 --faces ${F#,} --spacing $sp --labels --size 800x800 --cols 3 --shots "${S#;}" 2>&1 \
  | grep -E "SCRIPT ERROR|SHEET" | sed 's/.*screenshots\//  /'
