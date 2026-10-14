# Brain Control Assets — Claude (assets session)

Since 2026-10-14 a Claude session owns this repo (took over from Codex). Another Claude session owns gameplay in `../brain-control-simulator/`. `AGENTS.md` still applies; "Codex" there means this session.

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
- Cockpit: pass 1 blockout done (`docs/cockpit_plan.md`, `previews/cockpit/`). Waiting on CODEX-006 (cockpit art interfaces) from gameplay and user composition review.
- Initial commit 8629283 pushed to origin/main.
