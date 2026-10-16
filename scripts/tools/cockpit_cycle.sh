#!/bin/zsh
# One command for the cockpit edit loop: build, audit with details, reimport the GLB, verify. Result lines only.
#   cockpit_cycle.sh                 # stops after the audit if it finds clipping (fix, rerun)
#   NB_YAW=12 cockpit_cycle.sh       # build-time env knobs pass through
# Prints the build's own report lines (NOTEBOOK ...), each CLIP/ZFIGHT pair, then VERIFY PASS/FAIL.
cd "${0:A:h}/../.."
B=/Applications/Blender.app/Contents/MacOS/Blender
$B -b --factory-startup --python scripts/cockpit_v2/build.py 2>&1 | grep -E "^[A-Z_]{4,} |Traceback|Error:" | grep -vE "^(BANANA|INFO) " || exit 1
audit=$($B -b source/cockpit/cockpit_v2.blend --python scripts/cockpit_v2/audit.py 2>&1 | grep -E "^(AUDIT|CLIP|ZFIGHT|FLOAT)")
echo "$audit"
[[ "$audit" == *"AUDIT 0 "* ]] || { echo "CYCLE STOP: fix the audit first"; exit 1; }
scripts/tools/reimport.sh cockpit/art/cockpit_art.glb 2>&1 | tail -1
scripts/tools/verify.sh cockpit 2>&1 | tail -1
