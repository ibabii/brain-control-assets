---
name: asset-pipeline
description: Build, verify, capture and hand off Brain Control art (cockpit, hands, fly) from scripts. Use for any change to brain-control-assets models, notes, tape, hands or controls, and before telling the user or gameplay that art is done.
---

# Asset pipeline (brain-control-assets)

Everything is scripted and headless. Do not use the Blender MCP or the assets Godot editor for builds or checks:
headless runs are faster and deterministic. Never touch bridge 9080 (gameplay editor).

## Loop

1. **Edit** the build script, not the .blend:
   - cockpit: `scripts/cockpit_v2/`
   - hands: `scripts/hands/build.py`
   - fly: `scripts/fly/build.py`
2. **Build** (~8 s each):
   ```
   B=/Applications/Blender.app/Contents/MacOS/Blender
   $B -b --factory-startup --python scripts/cockpit_v2/build.py 2>&1 | grep -E "BUILT|Error|Traceback"
   $B -b --factory-startup --python scripts/hands/build.py -- --no-sheet 2>&1 | grep -E "RIG|Error|Traceback"
   ```
   Hands: drop `--no-sheet` only when the style sheet previews must change.
3. **Reimport** changed GLBs: `scripts/tools/reimport.sh hands/art/hand_r.glb hands/art/hand_l.glb`
   - Rescan or touch alone is not enough: the script drops Godot's .md5 first.
   - The cockpit capture re-imports by itself when the assets editor has rescanned; if in doubt, run reimport.sh on `cockpit/art/cockpit_art.glb`.
4. **Verify**: `scripts/tools/verify.sh [cockpit] [hands]`. It must print `VERIFY PASS`. It covers:
   - clipping, z-fighting and floating screws (audit.py)
   - tape lying on surfaces (tape_check.py)
   - the hand rig contract (check_hand_rig.gd)
5. **Look**, with one run and one image to read:
   ```
   scripts/tools/capture.sh review --size 1200x675 --shots "seat;caps@0.55,1.12,0.35@0.6,0.98,0.12;..."
   ```
   - Read `previews/cockpit_v2/screenshots/review.png`, a 2-column contact sheet.
   - Always include `seat` plus oblique views of what changed: side, top, thumb-side for hands. Don't trust the seat view alone.
   - Hands and props in the cockpit: `--extra res://previews/hands/hand_pose_preview.tscn --left press_finger --right grip --t 1.0`; fly: `--extra res://previews/fly/fly_preview.tscn`.
   - Full-resolution single shots only when a detail needs it. Delete throwaway screenshots before committing.
6. **Commit + push**, then hand off:
   ```
   scripts/tools/handoff.sh "what changed" cockpit/art hands/art
   ```
   - The script writes `SHA256SUMS` per folder, commits, pushes and prints `SYNC <commit> <folders> # notes`.
   - SendMessage to game-mechanics: a short summary, then the SYNC line as the last line.
   - Ship `.import` files too: hand and fly GLBs import at `animation/fps=100`, and the import scripts live in the art folder.

## Gotchas (each cost real time once)

- **Slab bevels:** `lib.slab` insets the outline by the bevel. A bevel of half the ring width or more eats the face. Cap the bevel below half the ring.
- **Scene BVH:** build it from triangles (`to_mesh` + `calc_loop_triangles` → `BVHTree.FromPolygons`). Repeated `BMesh.from_mesh` silently drops meshes.
- **Normals:** mesh normals are not reliably outward. Orient a nearest-point normal by the side you came from.
- **Godot import:** scene import resamples clips at 30 fps unless `animation/fps=100`. Hit frames and wing beats need 100.
- **Import scripts:** `Skeleton3D.get_bone_global_pose` is stale outside the tree; compose the local poses yourself.
- **Hands:** check the thumb from the thumb side and the palm. The thumb roots low by the wrist, the nail faces sideways, and it curls across the palm.
- **Tape:** only where it holds something (notes, labels, the OUT OF ORDER caps). The user removed decorative tape.

## Contracts

- `../coordination/interfaces.md` holds the hooks agreed with gameplay: control hooks, note text slots, Hand art, Fly.
- Changing names, anchors or axes needs gameplay's agreement first; propose by SendMessage and record it there.
- Gameplay replies to a SYNC line in one report: commits, per-folder checksums, reimport errors, one seat-view contact sheet (16:9 / 4:3 / 21:9), smoke test counts, local changes to upstream.
- To see art in a live gameplay moment (a press, the swat, a reveal), ask game-mechanics for a probe scenario. Their `-- --probe` + `tools/probe.py` pauses on an exact condition and shoots crops; don't guess timings yourself.
