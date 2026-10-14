# First handoff: toothbrush art

Updated 2026-10-14. Based on Claude's CODEX-002 and CODEX-003 replies in `../../coordination/claude.md`. The user owns the final visual-direction decision.

Art baseline: `warm_ceramic_v1`, defined in `style-guide.md` and `../materials/warm_ceramic_v1/palette.json`. Use these shared colours and material recipes for the toothbrush. Include the style ID in its manifest.

## Deliverable

Self-contained art folder at `props/toothbrush/art/`, matching the intended game destination. A `.glb` or script-free `.tscn` with a `Node3D` root `ToothbrushArt`. No gameplay script, collision, AnimationPlayer, autoplay, or external dependencies. Leave meshes on render layer 1. Include separate child `Paste` for wrapper-controlled visibility, and a grip marker or explicit grip-position note. Do not model hands.

Claude retains `props/toothbrush/toothbrush.tscn`, `HeldProp` properties, grips, gameplay motions, and camera/layer logic. Codex supplies the model and materials; Claude integrates them.

## Geometry and transform

- Godot 4.7.2, Forward+. Units: meters, +Y up. Human faces -Z.
- Model origin at the bristle-head centre/contact point. Handle extends +X. Bristles point +Y. Bristle face width lies along Z.
- Target length about 0.19 m.
- Existing handle reference: dimensions `(0.17, 0.016, 0.022)`, centre X=0.10.
- Existing bristle reference: dimensions `(0.035, 0.022, 0.018)`, centre Y=0.015.
- Separate paste reference: Y=0.03. Keep paste separate from foam.
- Right-hand grip reference: `(0.17, -0.01, 0)`.

Current gameplay references may change: wrapper position `(0.03, 1.47, -0.24)` relative to Human; view pitch -12 degrees; root swings ±14 degrees about Y on rhythm hits. The art must not duplicate that motion.

## Required previews

- First person: eye `(0, 1.62, 0)`, FOV 70, brush about 0.25–0.3 m away in the lower centre. Do not obstruct the centre or mirror.
- Mirror: reflected brush about 1.0–1.1 m away, mirror glass approximately 666×540 px. Readable silhouette and colour at this scale.
- Reveal: 1.5–2.2 m away; check a view at 2 m. Bathroom reveal mark `(1.35, 1.6, 1.0)`, Human `(0, 0, 0.2)`.

Render layers: world/held props = 1; Human body = 2; first-person hands/grips = 3. Claude owns layer configuration in gameplay.

## Material and state constraints

User visual preference: A's calmer colours (cream, muted mint, peach, ochre, dark teal). Retain simple chunky forms and selective rounded edges. The concept's fine towel/tile textures and polished lighting are illustrative; economical low-poly geometry and plain materials are appropriate for the actual game.

Use simple, chunky, low-poly forms and mostly opaque materials. Bathroom mirror adds a second render. No state only inside shaders/materials; replay resets transforms and visibility. Keep separable paste visibility under wrapper control.

Future bathroom art must preserve gameplay moving-part interfaces and clearances. Mirror frame art sits at least 5 mm behind the glass plane; do not supply reflective glass. Mesh drops/splashes are preferable to particles until gameplay supports their time scaling/reset.

## Handoff manifest and validation

Provide file list, triangle count, materials, dependencies, coordinate/origin notes, and screenshots of the three views. Claude validates first-person/mirror/reveal framing, slow-motion and 3× swing, fall pose, reset/replay, UIDs/references, and full training success/failure smoke runs.

Style selection precedes finishing the prop. Concept frames are proposals, not screenshots or final geometry.
