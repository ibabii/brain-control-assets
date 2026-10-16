#!/bin/zsh
# Character-system phase 1 mock: every review sheet in one run (after scripts/characters/mock_build.sh).
# Writes previews/characters/screenshots/*.png and previews/bathroom/screenshots/mirror_{now,b}.png.
cd "${0:A:h}/../.."
G=/Applications/Godot.app/Contents/MacOS/Godot
D=previews/characters/screenshots
P=res://previews/characters/mock_preview.tscn
ALL=male_slim,bernard_b,male_heavy,female_slim,female,female_heavy
B4=male_slim,male_heavy,female_slim,female_heavy
T='#F1C6AC,#E2A184,#B9784F,#6E4330'
run() { perl -e 'alarm 240; exec @ARGV' $G --path . "$@" 2>&1 | grep -E "SCRIPT ERROR|_SHEET" | sed 's/.*screenshots\//  /'; }
mp() { run $P -- "$@"; }
head() { echo "front@0,$1,-1.1@0,$1,0@26;q@-0.85,$(($1+0.1)),-0.85@0,$(($1+0.02)),0@26;side@-1.15,$(($1+0.04)),0@0,$(($1+0.04)),0@26;back@0.8,$(($1+0.18)),0.85@0,$(($1+0.08)),0@26"; }

# 1. current vs style-updated Bernard (T-pose, faces) and in the bathroom mirror (the front-screen view)
mp --capture bernard_now_vs_b --models bernard_now,bernard_b --spacing 1.9 --size 1600x1000 --cols 2 \
  --shots "front@0,0.95,-30@0,0.95,0@6.6;back@0,0.95,30@0,0.95,0@6.6;face_now@0.95,1.62,-1.15@0.95,1.62,0@26;face_b@-0.95,1.64,-1.2@-0.95,1.64,0@26;q_now@0.15,1.75,-1.2@0.95,1.6,0@28;q_b@-1.75,1.78,-1.25@-0.95,1.64,0@28"
run res://previews/bathroom/bathroom_preview.tscn -- --capture mirror_now --human --size 1600x900 --shots "inmirror;reveal"
run res://previews/bathroom/bathroom_preview.tscn -- --capture mirror_b --human --human-model bernard_b --size 1600x900 --shots "inmirror;reveal"
# 2. heads and the build line-ups (T-pose = the skin bind; rest = arms down)
mp --capture head_bernard_b --models bernard_b --size 1200x1200 --cols 4 --shots "$(head 1.62)"
mp --capture head_female --models female --size 1200x1200 --cols 4 --shots "$(head 1.55)"
mp --capture female_tpose --models female --size 1400x1400 --cols 3 \
  --shots "front@0,0.9,-14@0,0.9,0@9;side@-14,0.9,0@0,0.9,0@9;back@0,0.9,14@0,0.9,0@9"
mp --capture lineup_tpose --models $ALL --spacing 1.75 --size 3000x900 --shots "front@0,0.95,-40@0,0.95,0@5.2"
mp --capture lineup_rest --models $ALL --spacing 0.75 --clip rest --from bernard_b --times 0 --size 2400x1000 --cols 1 \
  --shots "front@0,0.95,-14@0,0.95,0@17;q@-7,2.2,-12@0,0.95,0@17"
# 3. shared clips (every body plays bernard_b's library)
mp --capture shared_walk_feet --models bernard_b,female,female_heavy,male_heavy --spacing 1.0 --yaw 90 --clip walk_loop \
  --from bernard_b --times "0.0,0.27,0.53,0.8" --size 2000x700 --cols 2 --shots "front@0,0.5,-9@0,0.45,0@14"
# 4. skin tones in the kitchen and bathroom light
mp --capture tones_kitchen --stage kitchen --models bernard_b,female,bernard_b,female --tones "$T" --spacing 0.75 \
  --clip rest --from bernard_b --times 0 --size 2000x1000 --cols 1 --shots "wide@0,1.25,-4.6@0,0.95,0@30;faces@0,1.56,-2.9@0,1.53,0@26"
mp --capture tones_bathroom --stage bathroom --models bernard_b,female,bernard_b,female --tones "$T" --spacing 0.55 --z 1.2 \
  --yaw 180 --clip rest --from bernard_b --times 0 --size 2000x1000 --cols 1 --shots "wide@0,1.35,2.55@0,1.0,0.8@68;faces@0,1.6,2.55@0,1.52,1.2@40"
# 5. the hoodie on the four builds: deep squat (cameras outside every body) and a ragdoll fall per build
S=""; for x in 1.8 0.6 -0.6 -1.8; do S="$S;f$x@$x,0.62,-1.6@$x,0.5,0@38;b$x@$x,1.0,1.7@$x,0.55,0@38"; done
mp --capture squat_close --models $B4 --spacing 1.2 --clip squat --from bernard_b --times 1.0 --size 1200x1000 --cols 4 --shots "${S#;}"
S=""; for x in 1.8 0.6 -0.6 -1.8; do S="$S;s$x@$x,0.62,-1.7@$x,0.5,0@40"; done
mp --capture squat_side_close --models $B4 --spacing 1.2 --yaw 90 --clip squat --from bernard_b --times 1.0 --size 1200x1000 --cols 4 --shots "${S#;}"
rag=()
for m in ${(s:,:)B4}; do
  mp --capture rag_$m --models $m --clip rest --from bernard_b --ragdoll --follow --t 3 --size 1200x900 \
    --shots "low@-1.5,1.1,-1.3@0,0.12,0@40" >/dev/null
  rag+=($PWD/$D/rag_$m.png)
done
$G --headless -s scripts/tools/sheet.gd -- $PWD/$D/ragdoll_fall.png 800 2 $rag 2>&1 | grep SHEET | sed 's/.*screenshots\//  /'
rm -f $D/rag_*.png*
# 6. chest size 0 / 0.5 / 1 (Chest_Size; 0.5 = the default) at rest and in the deep squat
mp --capture chest_sizes --models female --chest "0,0.5,1" --spacing 0.75 --yaw 90 --clip rest --from bernard_b --times 0 \
  --size 2000x900 --cols 1 --shots "side@0,1.15,-3.6@0,1.0,0@28;q@-1.6,1.4,-3.2@0,1.05,0@28"
mp --capture chest_squat --models female --chest "0,0.5,1" --spacing 0.9 --yaw 90 --clip squat --from bernard_b --times 1.0 \
  --size 2000x900 --cols 1 --shots "side@0,0.7,-3.6@0,0.6,0@26;front@0,0.9,-3.4@0,0.6,-0.3@30"
