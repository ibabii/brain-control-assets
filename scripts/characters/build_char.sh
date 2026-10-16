#!/bin/zsh
# Character system phase 2: build a base body and its parts (scripts/characters/build_char.py), write .import files
# (bodies use human/art/human_import.gd), reimport. Usage: build_char.sh [male] [female]   (default: both)
cd "${0:A:h}/../.."
B=/Applications/Blender.app/Contents/MacOS/Blender
typeset -A SPECS
SPECS=(
  male   '{"look":"B","head":1.25,"sy":0.975,"keep_eye":true,"mock":true}'
  female '{"look":"B","sex":"female","head":1.25,"sy":0.95,"narrow":0.03,"chest":true,"hair":"bun","clips":"basic","mock":true}'
)
bases=($@)
(( $#bases )) || bases=(male female)
for b in $bases; do
  CHAR_CHECK=${CHAR_CHECK:-} CHAR_BASE=$b HUMAN_ARM_UP=78 HUMAN_SPEC=${SPECS[$b]} $B -b --factory-startup --python scripts/characters/build_char.py \
    2>&1 | grep -E "Traceback|Error:|CHAR_BUILT|CLEAR|sampled worst [0-9.]*[1-9]|^  File" | sed "s/^/[$b] /"
done
files=()
for g in characters/*_base/art/*.glb characters/parts/*/art/*.glb; do
  imp=$g.import
  if [[ ! -f $imp ]]; then
    if [[ $g == characters/*_base/* ]]; then
      sed -e '/^uid=/d' -e '/^path=/d' -e '/^dest_files=/d' -e "s|source_file=.*|source_file=\"res://$g\"|" \
        human/art/human.glb.import > $imp
    else
      sed -e '/^uid=/d' -e '/^path=/d' -e '/^dest_files=/d' -e "s|source_file=.*|source_file=\"res://$g\"|" \
        -e 's|import_script/path=.*|import_script/path=""|' human/art/human.glb.import > $imp
    fi
  fi
  # the running assets editor may import a new glb first, with default settings: bodies need the rig import script
  [[ $g == characters/*_base/* ]] && sed -i '' 's|^import_script/path=.*|import_script/path="res://human/art/human_import.gd"|' $imp
  files+=($g)
done
scripts/tools/reimport.sh $files 2>&1 | grep -v "^\[" | tail -4
