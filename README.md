# Brain Control Assets

Separate Godot assets laboratory for Brain Control Simulator. Gameplay remains in the sibling `brain-control-simulator` repository.

## Art style

All future assets follow **warm ceramic v1**: the user's selected calm A palette, simple chunky shapes, selective rounded edges, and restrained materials. [Style guide](docs/style-guide.md) defines the shared rules. The authoritative [palette and material recipes](materials/warm_ceramic_v1/palette.json) provide exact colour values; Godot starter materials live alongside that file and are generated with `python3 scripts/build_style_materials.py`.

## Local editor and MCP

Godot installed on this machine: **4.7.2**. MCP server/addon: **2026.10.12**.

| Session | Editor bridge | MCP client endpoint |
|---|---|---|
| Claude / gameplay | `ws://127.0.0.1:9080` | Existing stdio server; unchanged |
| Codex / assets | `ws://127.0.0.1:9081` | `http://127.0.0.1:9082/mcp` |

Start from this repository: `python3 scripts/start_assets.py`. It uses the already-cached MCP package offline, starts separate processes, and refuses occupied ports. Logs and process IDs are in ignored `.local/`.

The addon is a local snapshot of the gameplay project's addon with its default bridge URL changed to **9081**, so opening this project manually cannot take over the gameplay connection. The launcher sets the same URL explicitly.

`scripts/mcp_client.py` uses the MCP Python environment's `fastmcp` library to inspect/control this endpoint and refuses commands unless the connected project path matches this repository. Use `--list` to discover tool schemas. The assets project's `.codex/config.toml` provides a native MCP configuration for a Codex session opened here; newly configured MCP tools may require reloading the session.

The first finished prop is the [toothbrush v1](props/toothbrush/art/README.md), with editable Blender source, a self-contained Godot art scene, and first-person/mirror-distance/reveal previews. Run `previews/toothbrush/toothbrush_preview.tscn` to inspect it. Asset validation and a fresh-project import passed; main-game integration remains Claude's responsibility.

## Blender

Blender 5.2.2 LTS and MCP for Blender 2.1.9 are installed and verified. Blender's assets workspace listens on localhost:9876; Codex has a `blender_assets` stdio configuration. Start the workspace with `python3 scripts/start_blender.py`.

The complete modelling → `.blend` save → GLB export → Godot import pipeline and visual inspection were checked with a calibration fixture. Details, logs, and configuration notes: [docs/toolchain.md](docs/toolchain.md). Editable source belongs under `source/`; export game-ready models to their art folders.

## Coordination

Read `../coordination/README.md`, `plan.md`, and the other agent's status before work or handoffs. Codex owns asset production; Claude owns integration into the game. Do not automatically sync files or control the other editor.

## Third-party addon

`addons/godot_mcp` is from [hybridindie/godot-mcp](https://github.com/hybridindie/godot-mcp), version 2026.10.12, MIT licensed. Its license is preserved in that directory.
