# Installed asset toolchain

Verified 2026-10-14.

## Versions and connections

| Component | Version | Connection |
|---|---|---|
| Blender | 5.2.2 LTS, Apple Silicon | Addon socket on localhost:9876 |
| MCP for Blender | 2.1.9, addon protocol 13 | Codex `blender_assets`, stdio |
| Assets Godot | 4.7.2 | Bridge 9081, HTTP MCP 9082 |
| Gameplay Godot (Claude) | Existing editor | Bridge 9080, unchanged |

Community integration: https://github.com/ahujasid/mcp-for-blender. Installed through uv with Python 3.11. Server version is pinned and cached; configured launches use offline mode.

## Installed configuration

- Addon: `~/Library/Application Support/Blender/5.2/scripts/addons/blender_mcp.py`.
- Enabled in Blender's saved user preferences; addon auto-start is enabled for this workspace.
- Codex global configuration has `blender_assets`; the same entry is in this repository's `.codex/config.toml`.
- Host 127.0.0.1, port 9876. Telemetry disabled; Blender MCP safe mode enabled.
- Native Codex tools load after the app/session reloads its MCP configuration. Current work can already use `scripts/blender_client.py` through the installed MCP Python environment, so a restart is not needed to continue production.

## Assets Blender workspace

Start with `python3 scripts/start_blender.py` from this repository. It launches a new Blender process, enables the addon, saves preferences, tags the scene with this workspace's path, and opens/saves `.local/assets_workspace.blend`. It refuses to start while port 9876 is occupied; it never stops other Blender instances.

`.local/blender.log` contains editor/startup output; `.local/blender_session.json` records the PID. MCP command logs are in `.local/blender_mcp.log`.

The current-session client checks that Blender's scene has this repository's workspace marker and port before requested commands. It supports tool inspection with `--list`, JSON argument files for tools, and captures returned images into `.local/`.

Keep final editable `.blend` sources under `source/` (which has `.gdignore`) so Godot imports the exported GLBs rather than invoking Blender to auto-import source files.

## Verified capabilities

1. MCP connected to Blender 5.2.2 and read the workspace path, file path, and port.
2. Created a calibration mesh and assigned an opaque mint Principled material through `execute_blender_code`.
3. Saved the editable Blender workspace and exported `previews/toolchain_validation/pipeline_probe.glb` through MCP.
4. Rescanned the assets editor through its separate Godot MCP endpoint.
5. Godot imported the GLB with size `(0.19, 0.016, 0.022)` meters, verifying Z-up to Y-up conversion, and retained `ProbeMint` with roughness 0.65.
6. Blender's `look` tool returned front and three-quarter images, saved in `.local/blender-look-0.png`.
7. Socket inspection confirmed Blender 9876, assets Godot 9081/9082, and Claude's original Godot editor 9080 running together.

The calibration bar is a pipeline fixture, not toothbrush art. Recheck import after exporting it with `Godot --headless --path . --script res://previews/toolchain_validation/check_import.gd`; use the installed Godot executable path on this Mac.

## Ready for production

Model the toothbrush to `toothbrush_brief.md`, using the selected calm A palette, separate paste geometry, clean origins, and a script-free GLB. Preview in the assets Godot project, then hand off to Claude with a manifest.
