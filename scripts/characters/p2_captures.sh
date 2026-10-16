#!/bin/zsh
# Character system phase 2 review sheets (after scripts/characters/build_char.sh): assembled bases + parts,
# build keys, paint, bare bodies, squat, pocket close-up, ragdoll falls. Writes previews/characters/screenshots/p2_*.png.
cd "${0:A:h}/../.."
G=/Applications/Godot.app/Contents/MacOS/Godot
D=previews/characters/screenshots
mp() { scripts/tools/godot_bg.sh --timeout 240 --path . res://previews/characters/mock_preview.tscn -- "$@" 2>&1 | grep -E "SCRIPT ERROR|_SHEET" | sed 's/.*screenshots\//  /'; }
N=":top=:bottom=:shoes="
B4="male_base:Build_Slim=1,male_base:Build_Heavy=1,female_base:Build_Slim=1,female_base:Build_Heavy=1"
L="male_base:Build_Slim=1:top=tshirt_m:c.skin=F1C6AC:c.hair=8A3B22:c.top=9BC59D:c.rib=83A785:c.bottom=B8A57E,male_base,male_base:Build_Heavy=1:c.skin=6E4330:c.hair=2A1E1A:c.top=E8765E:c.rib=C5644F:c.bottom=454C48,female_base:Build_Slim=1:c.skin=B9784F:c.hair=2A1E1A:c.top=F1E4CF:c.rib=CCC1AF:c.bottom=2F4560,female_base,female_base:Build_Heavy=1:Chest_Size=1:top=hoodie_f:c.skin=4E2F22:c.hair=121010:c.top=BAC6B2:c.rib=9EA897:c.bottom=4A6A8C"   # crowd presets from characters/presets.json; the yellow hoodie is the Human
mp --capture p2_lineup --models "$L" --spacing 0.75 --clip rest --from male_base --times 0 --size 2400x1100 --cols 1 \
  --shots "front@0,0.95,-14@0,0.95,0@17;q@-7,2.2,-12@0,0.95,0@17;faces@0,1.55,-6@0,1.5,0@26"
mp --capture p2_bare --models "male_base$N,male_base$N:Build_Heavy=1,female_base$N,female_base$N:Build_Heavy=1" \
  --spacing 1.75 --size 2400x900 --cols 1 --shots "front@0,0.95,-30@0,0.95,0@7;back@0,0.95,30@0,0.95,0@7"
mp --capture p2_squat --models $B4 --spacing 1.2 --clip squat --from male_base --times 1.0 --size 1600x1000 --cols 2 \
  --shots "front@0,0.75,-6@0,0.55,0@26;back@0,0.9,6@0,0.55,0@26"
mp --capture p2_pocket --models "male_base:Build_Slim=1,female_base:Build_Slim=1" --spacing 0.9 --clip squat --from male_base \
  --times "0.5,1.0" --size 1600x900 --cols 2 --shots "f@0,0.8,-2.2@0,0.75,0@30;s@-2,0.8,-1.2@0,0.75,0@30"
rag=()
for m in ${(s:,:)B4}; do
  n=${${m//[:=]/_}//./}
  mp --capture rag_$n --models $m --clip rest --from male_base --ragdoll --follow --t 3 --size 1200x900 --cols 2 \
    --shots "low@-1.5,1.1,-1.3@0,0.12,0@40;top@0.01,2.2,0@0,0.1,0@40" >/dev/null
  rag+=($PWD/$D/rag_$n.png)
done
$G --headless -s scripts/tools/sheet.gd -- $PWD/$D/p2_ragdoll.png 1600 1 $rag 2>&1 | grep SHEET | sed 's/.*screenshots\//  /'
rm -f $D/rag_*.png*
