#!/bin/zsh
# All asset checks, headless, result lines only. Usage: verify.sh [cockpit] [hands] [bathroom] [human]  (default: all). Exit 1 on failure.
cd "${0:A:h}/../.."
B=/Applications/Blender.app/Contents/MacOS/Blender
G=/Applications/Godot.app/Contents/MacOS/Godot
what=${@:-cockpit hands bathroom human}
rc=0
run() { local out; out=$("$@" 2>&1); local s=$?; print -r -- "$out"; return $s; }
if [[ $what == *cockpit* ]]; then
  run $B -b source/cockpit/cockpit_v2.blend --python scripts/cockpit_v2/audit.py | grep -E "^(CLIP|FLOAT|ZFIGHT|AUDIT)"
  [[ ${pipestatus[1]} == 0 ]] || rc=1
  run $B -b source/cockpit/cockpit_v2.blend --python scripts/cockpit_v2/tape_check.py | grep -E "^TAPE_"
  [[ ${pipestatus[1]} == 0 ]] || rc=1
fi
if [[ $what == *bathroom* ]]; then
  run $B -b source/bathroom/bathroom.blend --python scripts/bathroom/audit.py | grep -E "^(CLIP|FLOAT|ZFIGHT|BATHROOM)"
  [[ ${pipestatus[1]} == 0 ]] || rc=1
fi
if [[ $what == *human* ]]; then
  run perl -e 'alarm 120; exec @ARGV' $G --headless --path . -s scripts/human/check_human_rig.gd | grep -E "FAIL|HUMAN RIG CHECK"
  [[ ${pipestatus[1]} == 0 ]] || rc=1
fi
if [[ $what == *hands* ]]; then
  run perl -e 'alarm 120; exec @ARGV' $G --headless --path . -s scripts/hands/check_hand_rig.gd | grep -E "FAIL|HAND RIG CHECK"
  [[ ${pipestatus[1]} == 0 ]] || rc=1
fi
echo "VERIFY $([[ $rc == 0 ]] && echo PASS || echo FAIL)"
exit $rc
