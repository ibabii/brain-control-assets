#!/bin/zsh
# Character-system phase 1 mock (coordination/character_system_plan.md): T-pose-bound bodies from the Human build with
# a spec (scripts/human/build.py SPEC), one folder each under previews/characters/mock/<id>/ (human.glb + human_rig.json,
# imported with human/art/human_import.gd). Usage: mock_build.sh [id ...]  (default: all). Never touches human/art.
cd "${0:A:h}/../.."
B=/Applications/Blender.app/Contents/MacOS/Blender
F='"look":"B","sex":"female","head":1.1,"sy":0.95,"narrow":0.02,"chest":true,"hair":"bun","clips":"basic","mock":true'
M='"look":"B","head":1.13,"mock":true'
typeset -A SPECS
SPECS=(
  bernard_now '{"mock":true}'
  bernard_b   "{$M}"
  male_slim   "{$M,\"build\":-1,\"clips\":\"basic\"}"
  male_heavy  "{$M,\"build\":1,\"clips\":\"basic\"}"
  female      "{$F}"
  female_slim "{$F,\"build\":-1}"
  female_heavy "{$F,\"build\":1}"
  female_base "{$F}"
)
ids=($@)
(( $#ids )) || ids=(bernard_now bernard_b male_slim male_heavy female female_slim female_heavy)
files=()
for id in $ids; do
  out=previews/characters/mock/$id name=human
  [[ $id == female_base ]] && out=characters/female_base/art name=female_base     # contract-shaped package (wobble test)
  mkdir -p $out
  HUMAN_ARM_UP=78 HUMAN_OUT=$PWD/$out HUMAN_NAME=$name HUMAN_SPEC=${SPECS[$id]} $B -b --factory-startup --python scripts/human/build.py -- A \
    2>&1 | grep -E "Traceback|Error:|HUMAN A|sampled worst [0-9.]*[1-9]" | sed "s/^/[$id] /"
  rm -f $out/human_A.glb
  [[ -f $out/$name.glb.import ]] || sed -e '/^uid=/d' -e '/^path=/d' -e '/^dest_files=/d' \
    -e "s|source_file=.*|source_file=\"res://$out/$name.glb\"|" human/art/human.glb.import > $out/$name.glb.import
  [[ $name != human && ! -f $out/$name.tscn ]] && printf '[gd_scene format=3]\n\n[ext_resource type="PackedScene" path="res://%s/%s.glb" id="1"]\n\n[node name="%s" instance=ExtResource("1")]\n' $out $name $name > $out/$name.tscn
  files+=($out/$name.glb)
done
scripts/tools/reimport.sh $files 2>&1 | grep -v "^\[" | tail -3
