#!/bin/zsh
# After commit + push: write SHA256SUMS in each shipped folder, commit them, print the SYNC line for gameplay.
# Usage: handoff.sh "notes" cockpit/art hands/art fly/art
# Gameplay verifies with: (cd <folder> && shasum -a 256 -c SHA256SUMS)
set -e
cd "${0:A:h}/../.."
notes=$1; shift
for d in "$@"; do
  # tracked files only (local preview snapshots stay out of the sums)
  (cd $d && git ls-files -- '*.glb' '*.tscn' '*.json' '*.gd' '*.import' '*.png' | grep -v '^SHA256SUMS$' | sed 's|^|./|' \
     | sort | xargs shasum -a 256 > SHA256SUMS)
done
git add "${@/%//SHA256SUMS}"
git diff --cached --quiet || git commit -qm "Handoff checksums: $*

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q origin main
echo "SYNC $(git rev-parse --short HEAD) $* ${notes:+# $notes}"
