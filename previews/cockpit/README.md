# Cockpit composition blockout v1

User approved the five-pass plan. This is pass 1 for layout review, not final art or a game integration package.

Run `cockpit_blockout.tscn` in the assets project. M switches menu/gameplay screen references, C shows clearance guides, V compares the current right slot with a proposed +8 cm outward offset, and F compares the current 68° field of view with a proposed 74°. All screen contents, controls and dial needles are static preview references. Hands are deferred; the game scripts remain Claude's.

Editable source: `source/cockpit/cockpit_blockout_v1.blend`. Export: `cockpit/art/cockpit_blockout.glb`. Rebuild: `scripts/build_cockpit_blockout.py` through the owned Blender MCP. Manifest: `cockpit/art/manifest.json`. The GLB is script-free and embeds eight materials, with no textures or external dependencies. The art export has 13,258 triangles; its primitive counts include the converted brain/cable curves.

Seven real Godot Forward+ screenshots are in `screenshots/`: current 16:9 menu/gameplay, current 4:3, clearance guide, proposed slot spacing, and proposed wider framing in both aspect ratios. Primary frames are 1280×720; narrow frames 960×720.

Findings:

- Main and side screen areas fit the primary view. Full gauge names are on paper below the dials.
- With the existing +0.30 m right-slot anchor, the joystick partially covers Embarrassment. A preview-only shift to +0.38 m clears it in the static pose. Full hand/control motion remains untested and requires Claude's interface reply.
- A 74° FOV reveals more edge dressing while keeping the camera position and gauge sightlines fixed. It is a proposal, not an applied game change. A tested 15 cm camera retreat hid the label row behind the console, so that alternative was discarded.
- A 4:3 view still clips the outer side-frame edges, even at 74°. It needs a framing policy or side-panel adjustment before claiming narrow-window support.
- Brain folds, books, notes, cables, a keepsake, mug, can, snack and notebook establish clutter masses. Density, surfaces, text and object detail are still provisional. Do not assess this as the completed cockpit.

Four props use adapted Kenney CC0 geometry. The original sources and licences are preserved in `source/vendor/kenney/selected/`; source records are in `sources.json`. See `docs/free_asset_sources.md` for verified alternatives. Desk/side ledges support the dressing, while the console and screen/control areas stay clear.

Next: user composition review and Claude CODEX-006 reply, then core cockpit modelling. Main game untouched.
