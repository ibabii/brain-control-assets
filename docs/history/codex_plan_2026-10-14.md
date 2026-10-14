# Joint gameplay and assets plan

Updated: 2026-10-14
Status: Claude reviewed the plan; Codex incorporated the agreed workflow below. The user prefers A's calmer colours. Geometry will be simplified for low-poly production; a finished asset still needs visual review. The user assigned assets to Codex and game mechanics to Claude.

Art baseline now locked for future production: **warm ceramic v1**. The user asked to formalize the overall style before modelling. Shared guide: `../brain-control-assets/docs/style-guide.md`; exact palette/profile recipes: `../brain-control-assets/materials/warm_ceramic_v1/palette.json`. Preserve functional input-colour identities; specific character designs follow the same style and get their own design sheets.

Cockpit concept direction approved: `../brain-control-assets/concepts/cockpit/cockpit-warm-ceramic-v1.png`. Retain dense personal clutter and articulated hands. Model gauge labels as separate taped paper strips under the dials with full names: Coordination, Confidence, Balance, Focus, Embarrassment. No image regeneration. The first 3D asset handoff remains the toothbrush.

Assets repository: `../brain-control-assets/`, cloned from `git@github.com:ibabii/brain-control-assets.git`. Initial Godot project, calibration stage, isolated addon, launcher, and MCP client are present locally; no commits or pushes yet.

Setup completed: Godot 4.7.2 assets editor is running on a separate MCP bridge (9081) with HTTP MCP at 9082. Claude's game editor remains on 9080. Preview-stage lighting and final asset requirements remain provisional.

Modelling toolchain completed: Blender 5.2.2 LTS plus MCP for Blender 2.1.9, owned by Codex, on localhost:9876. Modelling, saving, GLB export, visual inspection, and import into Godot were verified with a calibration fixture. Claude continues using only the game editor on 9080.

## Shared outcome

Develop E00 "Rise and Brush" into a convincing short episode: understandable controls, readable consequences, a funny reveal, and a coherent visual direction.

## Work in parallel

Claude: continue mechanics, episode pacing, contextual failure reactions, and reveal tuning in the main project. Identify asset needs without waiting for finished art.

Codex: explore a simple, chunky visual direction with 1–2 bathroom style frames, then produce script-free art scenes. Claude retains the gameplay wrappers, scripts, exports, grips, node IDs, and render-layer assignment. Human body and hands are a later milestone because their rig is still changing.

## Milestones

1. DONE: Claude answered `CODEX-001` through `CODEX-003`; Codex incorporated those replies. Isolated Godot/MCP setup is also done.
2. STYLE PREFERENCE RECEIVED: Codex delivered two bathroom style frames in `../brain-control-assets/concepts/bathroom/`. The user prefers A's calmer palette and asked about B's easier low-poly geometry. Production direction: A colours with simple chunky forms, selective rounded edges, and economical geometry. The concept's surface detail is not an asset requirement. Continue gameplay playtesting independently.
3. HANDOFF READY: toothbrush v1 art at `../brain-control-assets/props/toothbrush/art/`, with direct `Paste` child, `GripPoint`, manifest, editable source, and seven Godot previews. 19.4 cm; 1,196 triangles with paste. Asset checks and a fresh-project import passed. Claude integrates the art inside the existing toothbrush wrapper; user visual review is pending.
4. VALIDATION DONE: Claude integrated the toothbrush (`defee4e`) and passed actual view/swing/fall checks and both training smoke runs. No interface changes; findings in `claude.md`.
5. COCKPIT PLAN APPROVED / PASS 1 READY: user approved the five-pass plan and starting the blockout. Source/export, seven Godot previews and manifests are ready in the assets repo; see `docs/cockpit_plan.md` and `previews/cockpit/README.md`. Four adapted Kenney CC0 props used, with source/licence records. Review composition and resolve CODEX-006 interfaces before core/control detailing. Proposed slot spacing/FOV and 4:3 clipping are recorded for Claude. Bathroom expansion is not next.

## First asset requirements

- Installed Godot: 4.7.2, Forward+. Meters, +Y up, Human facing -Z.
- Game destination: `props/toothbrush/art/`, self-contained dependencies. Script-free `Node3D` root `ToothbrushArt`; no collision or AnimationPlayer. Default render layer 1; Claude controls wrapper layers.
- Origin: centre of bristle head. Handle along +X; bristles +Y; bristle width along Z. About 0.19 m overall. Separate child `Paste`; provide a grip note or empty at approximately `(0.17, -0.01, 0)`.
- Wrapping/rest-pose values are current references, not frozen: wrapper `(0.03, 1.47, -0.24)`, view pitch -12°, rhythm swing ±14° about Y.
- Views: first person at 0.25–0.3 m, FOV 70; mirror around 1.0–1.1 m; reveal around 1.5–2.2 m.
- Full compatibility brief: `../brain-control-assets/docs/toothbrush_brief.md`; source of gameplay constraints: `claude.md`.

## Shared visual constraints

- Simple, chunky silhouettes, low-poly geometry, mostly opaque materials. The bathroom is rendered twice because of the mirror.
- Keep the centre/mirror area clear and accumulated mess states readable. Mirror art is frame only; gameplay creates the glass.
- Moving/visible parts remain separate nodes. No autoplay, independent clocks, shader-only state, or uncoordinated particles; reset and replay must restore the scene.
- Future moving-part node names must be agreed with Claude before model production. No assumption that nesting an art scene automatically preserves gameplay node paths.

## Integration ownership

Claude owns changes inside the main game. Codex supplies assets and previews from its project. Integrate in small batches at stable checkpoints; retain recoverable greybox versions through normal version control.
