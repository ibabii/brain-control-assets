# Brain Control Simulator — art style v1

Style ID: `warm_ceramic_v1`
Established: 2026-10-14
Status: production baseline, locked from the user's selection of A's calmer colours and request for consistent future assets. Exact hex values and material defaults below are authored production values derived from that direction; they are not sampled colours from a lit concept image.

This guide applies to all future prop, environment, character, and cockpit art. The machine-readable source is `../materials/warm_ceramic_v1/palette.json`. New asset work reads this guide and the relevant technical brief first. Existing gameplay files remain owned by Claude.

## Identity

Warm, calm, tactile, and playful. Simple chunky objects with gently rounded edges, clean colour blocks, expressive silhouettes, and modest surface detail. Everyday spaces feel familiar and inviting. Comedy comes from motion, expressions, and accumulating messes.

The selected reference is `../concepts/bathroom/style-a-warm-ceramic.png`. It establishes mood and palette. Its fine fabric detail, reflections, object layout, and cinematic lighting are illustrative; the production rules here govern actual assets.

## Core world palette

All codes are sRGB base colours before lighting.

| ID | Name | Hex | Role |
|---|---|---|---|
| `cream` | Warm cream | `#F1E4CF` | Main neutral: walls, counters, furniture |
| `sage` | Soft sage | `#BAC6B2` | Main colour: tiles, cabinetry, painted props |
| `teal` | Deep teal | `#2D5C5B` | Contrast: handles, trim, larger dark structural pieces |
| `peach` | Muted peach | `#EAA78B` | Warm supporting colour: textiles, selected props |
| `honey` | Honey ochre | `#D9A04C` | Small accents: hardware and selected details |
| `clay` | Dusty coral | `#C98778` | Secondary accent: brain cues and selected prop details |
| `porcelain` | Porcelain white | `#F8F4EA` | Clean surfaces: bristles, paste/foam, ceramic highlights |
| `graphite` | Warm graphite | `#454C48` | Neutral dark: rubber, feet, recesses and small details |

Cream and sage normally dominate a room. Teal/peach provide supporting colour; honey/clay appear sparingly. A typical room can use roughly 65% light bases, 25% supporting colours, and 10% accents as a composition guide, not a measured quota. Avoid applying every colour to every object. Most small props use 2–3 palette colours plus a neutral.

Future rooms can change which core colours dominate, giving each set its own identity while retaining the family. Introduce new world colours through an explicit update to this guide and palette file, rather than per-model improvisation. Lighting may change the appearance of a base colour; verify important models in neutral light as well as episode light.

### Functional and character colours

- Existing gameplay action colours remain defined by the game's `src/core/palette.gd`. Physical controls and screen prompts must retain their matching colour identities. New cockpit shells use the calm world palette; functional illumination stays concentrated on controls and warnings.
- Colour cues are paired with symbols, labels, shape, or motion. Object identity and important messes must read in silhouette and value contrast too.
- Skin/hair are a separate character palette under the same warm, muted, matte treatment. Exact character colour sets, proportions, and costumes will be established with character design sheets. This baseline does not choose a Human identity or change the procedural rig.
- Brain visuals can use dusty coral as a starting family, with the same rounded forms and restrained highlights.

## Shape and modelling

- Keep recognizable real-world proportions, with mild thickening of handles, rims, buttons, bristle clusters, and silhouettes where readability needs it.
- Use large, clean forms with selective rounded edges. Bevels are typically 1–2 segments; spend extra geometry only when it visibly improves the silhouette at the actual gameplay distance.
- Use smooth shading for broad curves and deliberately flat shading for flat surfaces. Avoid making each face a random colour or making facets the dominant look.
- Small details are grouped: bristle tufts, folded towel volumes, and large foam blobs. Individual fibres, pores, hair strands, and micro-scratches are unnecessary for this style.
- Maintain a similar bevel language across related objects. A soft ceramic rim and a chunky plastic grip can have different radii but should feel part of the same world.
- Characters use rounded, readable forms, clear hands/feet, expressive faces, and exaggerated poses. Establish the first character sheet before locking specific anatomy or rig proportions.
- Record triangle counts in asset manifests. Counts are tuned against the gameplay and mirror views; v1 does not claim a measured scene performance budget.

## Materials

Use simple, exportable Principled BSDF / StandardMaterial3D materials. Broad colour blocks and roughness describe the surface. Defaults are starting recipes shared across assets:

| Profile | Roughness | Metallic | Typical use |
|---|---:|---:|---|
| `painted` | 0.62 | 0.00 | Painted furniture, opaque plastic |
| `ceramic` | 0.38 | 0.00 | Sink, tub, glazed tiles |
| `fabric` | 0.90 | 0.00 | Towels and clothing |
| `rubber` | 0.86 | 0.00 | Grips, feet, soft dark pieces |
| `paste` | 0.72 | 0.00 | Toothpaste and foam geometry |
| `metal` | 0.48 | 0.75 | Small brushed hardware |

Presets allow intentional adjustments for a surface; record adjustments in the manifest. Ordinary world surfaces are opaque, non-emissive, and gently highlighted. Mirror glass is owned by gameplay; the art supplies its frame. Existing water/mess effects follow Claude's technical interfaces and remain separately controlled pieces.

Textures are optional. Prefer plain materials for initial bathroom props; use sparse, broad texture information only when it materially improves an object's identity. Export material settings to GLB, rather than relying on a Blender-only shader graph.

### Colour consistency between tools

Palette codes and Godot albedo values are sRGB. Convert those RGB values to scene-linear RGB when assigning Blender Principled Base Color through Python; keep alpha at 1. GLB carries the material, and Godot performs its import conversion. Compare the imported result against the same palette rather than manually brightening each new model. [Godot colour encoding](https://docs.godotengine.org/en/stable/classes/class_color.html), [Blender colour spaces](https://docs.blender.org/manual/en/5.2/render/color_management/color_spaces.html).

The generated Godot starter materials use the palette's sRGB values and the profile defaults. A Blender export can embed the corresponding colours/profile values so a game asset remains self-contained.

## Lighting and presentation

- Warm-neutral key light with soft shadows, restrained cool/neutral fill, and clear separation between the prop and its background.
- Keep enough contrast to read mistakes, the Human's face, and moving parts in the mirror. Calm colours still need value separation.
- Lighting is scene-level. Imported props contain no cameras, lights, baked shadow colours, or dramatic grading.
- Neutral preview lighting is the colour reference; episode lighting creates mood. Strong bloom, heavy outlines, neon washes, and photographic surface detail are outside the baseline.
- Cockpit and human-world art share the same shape/material language. The cockpit may use more deep teal/graphite to frame bright functional controls.

### Cockpit composition

The user's early cockpit reference (`../concepts/cockpit/reference-early-cockpit.png`) establishes intentionally dense personal clutter: taped notes, cables, keepsakes, books, snacks, cups, and papers around the console. This expresses a busy inner brain even when the outside world looks calm. Preserve that density around the screen/control edges while keeping functional areas readable. The calm palette applies to the surfaces; the cockpit remains lively and lived-in. Brain-pilot hands should have rounded, articulated fingers and natural grips; the reference's block hands are placeholders.

The user approved the regenerated cockpit direction (`../concepts/cockpit/cockpit-warm-ceramic-v1.png`). For the eventual model, label the five gauges using separate taped paper strips **under** each dial, with the full names **Coordination**, **Confidence**, **Balance**, **Focus**, and **Embarrassment**. Gauge faces retain ticks/needles; full labels live on the paper rather than abbreviated text on the dial. Keep the longest name readable at the gameplay camera distance. This is a modelling note; the approved concept image is unchanged.

## Asset consistency and handoff

Before delivering an asset, verify its recognizable silhouette, palette IDs, material profiles, scale/origin, clean hierarchy, and technical brief. Include its style ID and any intentional deviations in the manifest. Review it at first-person, mirror, and reveal distances where relevant.

Moving parts and mess states remain separate nodes. Runtime motion, visibility, collision, and render-layer assignment stay in Claude's gameplay wrappers. Materials do not secretly encode replay state.

To change the visual baseline later, update this guide and `palette.json` together, regenerate the material references, and record the change in the shared coordination plan. Already delivered art is revised deliberately as part of that change.
