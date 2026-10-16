#!/bin/zsh
# Hair sheet: front / 3/4 / side / back close-ups of one base's head (labelled).
# Usage: hair_sheet.sh NAME MODEL eye_y   (screenshots/NAME.png; MODEL may carry overrides, e.g. female_base:hair=x)
cd "${0:A:h}/../.."
y=$3; yl=$(( $3 + 0.05 ))
scripts/tools/godot_bg.sh --timeout 240 --path . res://previews/characters/mock_preview.tscn -- --capture $1 --stage flat \
  --models $2 --faces rest --labels --size 700x700 --cols 4 \
  --shots "front@0,$yl,-1.0@0,$yl,0@28;3/4@-0.72,$(( yl + 0.12 )),-0.72@0,$yl,0@28;side@-1.0,$yl,0@0,$yl,0@28;back@0.5,$(( yl + 0.15 )),0.87@0,$yl,0@28" \
  2>&1 | grep -E "SCRIPT ERROR|SHEET" | sed 's/.*screenshots\//  /'
