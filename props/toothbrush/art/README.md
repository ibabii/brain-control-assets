# Toothbrush v1 handoff

Built 2026-10-14. Art baseline: `warm_ceramic_v1`. Muted clay handle, deep teal grip, twelve broad porcelain bristle tufts, and a sage paste ribbon. Rounded low-poly geometry; opaque materials; no textures.

## Copy and instance

Copy only `toothbrush_art.tscn`, `toothbrush_body.glb`, and `toothbrush_paste.glb` into the game's `props/toothbrush/art/`. Let Godot generate its own imports; do not copy `.godot/` or `.import` sidecars. Instance `toothbrush_art.tscn` inside the existing gameplay wrapper, with an identity local transform. Keep the existing gameplay script, grips, motion, and camera-layer logic in the wrapper.

The root is `ToothbrushArt`. Direct children are `Body`, `Paste` (starts hidden since 2026-10-15), `GripPoint` and `Grips/Left|Right` (Character rig v1 basis: +X toward the head, +Y away from the bristles). Hide/show `ToothbrushArt/Paste` to control both paste meshes. Update the wrapper's paste node reference explicitly; nesting this scene does not preserve a previous `$Paste` path. `GripPoint` is a reference marker; continue using the wrapper's `Grips/Right` for gameplay.

No scripts, collision, animation, particles, lights, or cameras are inside the art scene. Meshes use layer 1. Both GLBs embed their materials and have no external dependencies. The TSCN references them with relative paths, without project-specific UIDs.

## Coordinates and budget

Meters, Godot +Y up. Root pivot is at the head centre, handle extends +X, bristles +Y, width along Z. Grip is `(0.17, -0.01, 0)` in root-local coordinates. Bounds with paste: minimum `(-0.018, -0.011, -0.0105)`, size `(0.194, 0.0438, 0.021)` m.

| Part | Triangles |
| --- | ---: |
| Handle | 260 |
| Head | 124 |
| Grip | 92 |
| Bristles | 528 |
| PasteBody | 136 |
| PasteStripe | 56 |
| Total with paste | 1,196 |
| Body only | 1,004 |

Five materials, six mesh surfaces. Palette and roughness are listed in `manifest.json`. All materials are opaque, nonmetallic, nonemissive, with backface culling. No deviations from the shared art baseline.

## Source and preview

Editable Blender source: `source/toothbrush/toothbrush_v1.blend` in the assets repo. Rebuild script: `scripts/build_toothbrush.py`, executed through the owned Blender MCP session. The source and preview files are developer assets; they are not required in the game.

Run `previews/toothbrush/toothbrush_preview.tscn` in the assets project. Keys: 1 close-up, 2 first person, 3 mirror-distance projection, 4 reveal distance; P paste; arrows ±14° swing; R reset. The first-person sphere is the existing grip reference, not part of the delivered model.

Screenshots are under `previews/toothbrush/screenshots/`: close-up, first person, mirror projection at 666×540, reveal at 2 m, left/right swing, and no paste. Other frames are 1280×720. These are actual Godot renders. The mirror view uses the reflected eye position; it does not reproduce the bathroom's mirror implementation or background.

## Validation and remaining integration

Passed `validate_toothbrush.gd` both in the assets project and after copying only the three runtime files into an empty temporary Godot 4.7.2 project. Checks cover loadability, dependencies, hierarchy, units/axes, bounds, layers, palette/roughness, opaque materials, paste visibility, grip, and restoring the rest transform. Blender topology checks found no boundary edges, nonmanifold edges, or loose vertices. Seven Forward+ preview captures completed without runtime errors.

Claude's integration pass remains: actual first-person/mirror/reveal framing, wrapper node references and UIDs, timed slow-motion and 3× replay swing, fall pose, reset/replay, and `training_smoke` plus `training_fail_smoke`. Record results in `coordination/claude.md`.
