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
   - bathroom: `scripts/bathroom/build.py` (room + one GLB per prop); the Human: `scripts/human/build.py`
   - shared: `scripts/cockpit_v2/lib.py` (slabs, tubes, frames) and `sculpt.py` (metaball families → voxel union,
     surface rays, projected decals)
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
   - the bathroom (scripts/bathroom/audit.py): clipping between assemblies, z-fighting, things standing on air
   - the Human rig (scripts/human/check_human_rig.gd): contract, IK reach and poles, ragdoll drop (Jolt)
5. **Look**, with one run and one image to read:
   ```
   scripts/tools/capture.sh review --size 1200x675 --shots "seat;caps@0.55,1.12,0.35@0.6,0.98,0.12;..."
   ```
   - Read `previews/cockpit_v2/screenshots/review.png`, a 2-column contact sheet.
   - Always include `seat` plus oblique views of what changed: side, top, thumb-side for hands. Don't trust the seat view alone.
   - Bathroom: `scripts/tools/capture_bathroom.sh NAME [--human] [--fx] --shots "fp;reveal;door;mirror;tub;toilet"`
     (`--fx` shows the hidden effects). Human: `scripts/tools/capture_human.sh NAME [--mode lineup|faces]`.
   - Hands and props in the cockpit: `--extra res://previews/hands/hand_pose_preview.tscn --left press_finger --right grip --t 1.0`; fly: `--extra res://previews/fly/fly_preview.tscn`.
   - Full-resolution single shots only when a detail needs it. Delete throwaway screenshots before committing.
6. **Commit + push**, then hand off:
   ```
   scripts/tools/handoff.sh "what changed" cockpit/art hands/art
   ```
   - The script writes `SHA256SUMS` per folder, commits, pushes and prints `SYNC <commit> <folders> # notes`.
   - SendMessage to game-mechanics: a short summary, then the SYNC line as the last line.
   - Ship `.import` files too: hand and fly GLBs import at `animation/fps=100`, and the import scripts live in the art folder.

## Shortcuts (2026-10-16 self-eval)

- `scripts/tools/cockpit_cycle.sh`: build, audit with each CLIP pair, reimport and verify in one call (env knobs pass
  through, e.g. `NB_YAW=12`). Use it instead of chaining four commands per iteration.
- `scripts/tools/aspects.sh NAME [preview args]`: seat view at 16:9, 16:10 (Deck) and 21:9 plus a sheet. The frame is
  locked to 16:10–21:9 with bars outside (user, 2026-10-16); `ASPECTS_43=1` adds 4:3 as a bars check only. Anything at
  a frame edge, or with a px rule (caps, gaps), is checked at every aspect. Preview result lines print per aspect.
- `Blender -b source/cockpit/cockpit_v2.blend --python scripts/tools/probe.py -- NAME...` prints world bounds and
  the 1080p seat rect; `-- --near x,y,z R` lists what is within R of a point.
- `Godot --headless -s scripts/tools/sheet.gd -- OUT.png 800 2 a.png b.png ...` makes a contact sheet from any PNGs.

## Before building a proposal or spec (checklist)

1. **Probe the spot first:** `probe.py --near` the anchor point with the prop's reach (hang length, swing radius,
   arm path). If a neighbour is inside it, reply with the conflict and 2–3 placements before building anything.
   (The octopus hang point sat 2.3 cm above the answering machine; the notebook pivot swung into the A-key hand.)
2. **Mock as a preview script,** not a rebuild: move or scale the existing nodes in a `previews/.../*_mock.gd` and fit
   them by their on-screen rect from a fixed seat camera, so oblique shots stay consistent. Render every option at
   every aspect in one sheet.
3. **Hands vs props:** the hand preview's arm is not the game's arm. State that, and ask mechanics for
   `tests/clearance_check` numbers (CPU-skinned) before calling a placement clear.
4. **Px rules move with geometry:** a turn or resize changes cap height, row width and occlusion. Rebuild the check
   into the build log (as `paper.notebook` prints its far-end cap and full-row fit) instead of eyeballing.

## Handoff hygiene

- Commit before you start the next pass: mechanics rsyncs the working tree, and uncommitted edits broke a sync once.
  Tell them to take `git archive` at the SYNC hash.
- Check `ListAgents` before messaging a session; if it's offline, give the orchestrator the paths instead.
- Unchanged GLBs must stay byte-identical: if a rebuild with no source change shows a modified GLB, find the
  jittering mesh (normals jittered ~3e-5; the signature now rounds normals to 3 decimals).

## Gotchas (each cost real time once)

- **Slab bevels:** `lib.slab` insets the outline by the bevel. A bevel of half the ring width or more eats the face. Cap the bevel below half the ring.
- **Small rounded boxes:** `lib.box` bevel over about ¼ of the smallest side collapses the inset outline into spikes
  (a 3 cm soap bar came out 19 cm tall). The bathroom's `rbox` caps it.
- **Audits:** inside/outside (ray parity) only means something against closed meshes. Skip open sheets like puddles,
  lofts and wall quads, or the audit reports false clipping.
- **Stable handoffs:** every build exports through `lib.export_glb`, which keeps the old file when the content signature
  (resolved nodes, meshes, materials, animations, floats rounded) is unchanged. Unchanged assets stay byte-identical,
  so gameplay skips reimporting them. Tape walks vary per build (BVH tie-breaking), so `conform_tapes` caches results
  in `source/cockpit/tape_cache.json`. Delete an entry, or the file, to re-roll a tape on purpose.
- **Skeleton modifiers** (IK, ragdoll): their result is applied only for rendering. Read posed bones inside
  `Skeleton3D.skeleton_updated`; `get_bone_global_pose` elsewhere returns the unmodified pose.
- **Baking a skinned mesh:** remove the bmesh deform layer before writing new vertex groups. The old group indices
  alias the new groups, which shredded the Human's fingers.
- **Bone vs node names:** a node named like a bone (an empty called "Head") makes Godot rename the bone ("Head_2").
- **Scene BVH:** build it from triangles (`to_mesh` + `calc_loop_triangles` → `BVHTree.FromPolygons`). Repeated `BMesh.from_mesh` silently drops meshes.
- **Normals:** mesh normals are not reliably outward. Orient a nearest-point normal by the side you came from.
- **Godot import:** scene import resamples clips at 30 fps unless `animation/fps=100`. Hit frames and wing beats need 100.
- **Import scripts:** `Skeleton3D.get_bone_global_pose` is stale outside the tree; compose the local poses yourself.
- **Hands:** check the thumb from the thumb side and the palm. The thumb roots low by the wrist, the nail faces sideways, and it curls across the palm.
- **Tape:** only where it holds something (notes, labels, the OUT OF ORDER caps). The user removed decorative tape.
- Godot's glTF import strips a `_loop` suffix from animation names (and loops them); `human_import.gd` renames them back to the json name.
- Measuring a pose in Blender while an action is assigned: the depsgraph re-applies the keyed action, so key first, `scene.frame_set(f)`, then measure (pose.py does this; NLA muted while baking).
- Interpolating joint rotations between pose keys drags planted hands/feet through the floor; bake in-betweens from blended targets (pose.between) and read the build log's `CLIP <name> sampled worst`.

## Contracts

- `../coordination/interfaces.md` holds the hooks agreed with gameplay: control hooks, note text slots, Hand art, Fly.
- Changing names, anchors or axes needs gameplay's agreement first; propose by SendMessage and record it there.
- Gameplay replies to a SYNC line in one report: commits, per-folder checksums, reimport errors, one seat-view contact sheet (16:9 / 4:3 / 21:9), smoke test counts, local changes to upstream.
- To see art in a live gameplay moment (a press, the swat, a reveal), ask game-mechanics for a probe scenario. Their `-- --probe` + `tools/probe.py` pauses on an exact condition and shoots crops; don't guess timings yourself.
