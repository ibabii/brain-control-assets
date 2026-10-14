# Assets workspace

- Art baseline is `warm_ceramic_v1`. Read `docs/style-guide.md` and `materials/warm_ceramic_v1/palette.json` before creating any model or material. Use their colour IDs/profile defaults; record deliberate deviations in asset manifests. Update the shared guide for style changes.

- Codex owns this repository. Claude owns the sibling gameplay repository.
- Read the sibling `../coordination/` plan and status files before work and handoffs.
- Assets MCP is HTTP `http://127.0.0.1:9082/mcp`, with editor bridge `ws://127.0.0.1:9081`. Port 9080 belongs to Claude; never connect this editor there.
- Verify the connected editor's project path before mutations. `scripts/mcp_client.py` enforces that check.
- Blender MCP: `blender_assets`, stdio server using pinned `mcp-for-blender==2.1.9`, socket 127.0.0.1:9876. Check this workspace's scene marker and file path before modifying Blender; `scripts/blender_client.py` enforces that check. Do not connect Claude to this Blender session.
- Blender MCP safe mode is enabled. Keep modelling scripts within its permitted Blender/Python API scope. Keep editable `.blend` files under `source/` (ignored by Godot) and export GLB files for engine use.
- Do not modify gameplay files or operate Claude's Godot session. Provide asset packages with dependency manifests for Claude to integrate.
- This is an asset preview project, not a second implementation of gameplay. Keep scenes independent of gameplay autoloads.
