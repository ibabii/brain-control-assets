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
Blender source in `source/<asset>/*.blend` → GLB export to `<asset>/art/` → script-free Godot art scene + `manifest.json` → preview in `previews/<asset>/`. Gameplay wraps the art; never edit the gameplay repo.

## Status
- Toothbrush v1: done and integrated in game (`defee4e`).
- Cockpit v2: scripted build `scripts/cockpit_v2/` matched to the concept from the game camera; preview + overlay in `previews/cockpit_v2/` (README there). Middle-ground layout agreed and applied in game `eeb819c`; art controls sit on the game anchors. Next: agree hooks (controls, needles, hands), then hand off.
- Blender builds run headless (`Blender -b --factory-startup --python ...`); import by rescanning the assets editor via MCP, then capture with a separate Godot process.
- Initial commit 8629283 pushed to origin/main.
