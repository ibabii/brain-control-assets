# Brain Control Assets — Claude (assets session)

Since 2026-10-14 a Claude session owns this repo (took over from Codex). Another Claude session ("game-mechanics") owns gameplay in `../brain-control-simulator/`. Talk to it by SendMessage; record agreed contracts in `../coordination/interfaces.md`; keep `../coordination/codex.md` to a short status. `AGENTS.md` still applies; "Codex" there means this session.

## Style
Read `docs/style-guide.md` and `materials/warm_ceramic_v1/palette.json` before any model or material. Use palette IDs; record deviations in the asset manifest.

## MCP (start this session from this folder so `.mcp.json` loads)
- `godot_assets`: HTTP `http://127.0.0.1:9082/mcp` → assets editor on bridge 9081. Check the project path is this repo before mutating.
- `blender_assets`: stdio, Blender on 127.0.0.1:9876, safe mode on. Check `scene['brain_control_assets_root']` equals this repo before modifying.
- Never use bridge 9080 (gameplay editor). The `godot` server from `../.mcp.json` points there.
- Start processes if down: `python3 scripts/start_assets.py`, `python3 scripts/start_blender.py`.
- Fallback without native tools: `scripts/mcp_client.py` and `scripts/blender_client.py`, run with the godot-editor-mcp uv Python (has fastmcp + mcp).

## Pipeline
Use the `asset-pipeline` skill (.claude/skills/asset-pipeline): build → scripts/tools/reimport.sh → scripts/tools/verify.sh → scripts/tools/capture.sh --shots (contact sheet) → commit → scripts/tools/handoff.sh (SYNC line). Headless only; MCP is for live editor inspection, not builds.
Blender source in `source/<asset>/*.blend` → GLB export to `<asset>/art/` → script-free Godot art scene + `manifest.json` → preview in `previews/<asset>/`. Gameplay wraps the art; never edit the gameplay repo.

## Status
- Toothbrush v1: done and integrated in game (`defee4e`).
- Cockpit v2: scripted build `scripts/cockpit_v2/` matched to the concept from the game camera; preview + overlay in `previews/cockpit_v2/` (README there). Middle-ground layout agreed and applied in game `eeb819c`; art controls sit on the game anchors. Cockpit art + controls (cockpit/art/controls/, hook contract in interfaces.md) integrated in game f4eb8f0. 2026-10-14: concept cut-outs removed (user rejected them); every prop is modelled (paper.py, props.py), note wording is live text (NoteText, agreed contract). Next: room pass (ceiling/floor, cable routing, wear). 2026-10-15: text/voice props (user-approved): intercom built into the front screen as a 10 cm chin (intercom.py, FrontScreen y 1.42, dials y 0.93), answering machine on the crate (answering_machine.py), 2D text kit ui/text_kit/ (scripts/text_kit/). Lamps (Brain/Heart/Stomach/Gary) left of the glass; gauge labels are short caps (COORD...). Preview the display with intercom_demo.tscn (--extra; --ic-dark, --ic-energy). TODAY notebook on a stand at the tray's left end (user pick B; paper.notebook, NB_* sizes), LeftKeys moved to x -0.29 so the A-press arm clears it. RightSlot x 0.39 (knob clear of EMBAR), HandRest_R 0.43, mug x 0.625; UNDO/DISTRACT plate removed (art_direction.md §1).
- Hands: style locked 2026-10-14 (scripts/hands/build.py → hands/art/hand_[rl].glb + .tscn via import script hands/art/hand_import.gd; check scripts/hands/check_hand_rig.gd; preview previews/hands/hand_pose_preview.tscn with the cockpit preview --extra). Blockout clips delivered; next polish clips, then prop pick-ups.
- Blender builds run headless (`Blender -b --factory-startup --python ...`); import by rescanning the assets editor via MCP, then capture with a separate Godot process.
- Bathroom v1: 2026-10-15 scripted set + props (scripts/bathroom/, bathroom/art/, contract in interfaces.md "Bathroom"), audit clean; handed to gameplay.
- Human: design approved 2026-10-15 (colourway A for now). Character rig v1 (interfaces.md): humanoid skeleton, RESET design pose, IK-ready, ragdoll (scripts/human/rig.py, human/art/human_import.gd, check scripts/human/check_human_rig.gd). Body clips are authored as poses in scripts/human/body_clips.py and baked by scripts/human/pose.py (hips + IK limbs + world hands/feet; in-betweens from blended targets; floor/tub penetration checked every 2nd frame in the build log). Preview: previews/human/human_rig_preview.tscn `--mode clip --clip NAME --times .. [--tub] [--prop scene]`. All agreed clips delivered; active ragdoll is a later experiment.
- Initial commit 8629283 pushed to origin/main.
