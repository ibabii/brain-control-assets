# The Human: character brief (draft for approval)

The body the brain pilots. Same character in every episode. Seen in the mirror (about 1.1 m, face and chest) and in the
third-person reveal (1.5–2.2 m, whole body). First person shows only the hands.

## Style
- Same family as the cockpit and the brain's hands: chunky, rounded, toy-like, matte, `warm_ceramic_v1` palette.
- Same 4-finger cartoon hands as the brain (skin, no knit cuff), so the hands read as "the same hands" through the screen.
- An ordinary, slightly rumpled adult: comedy comes from poses and expressions, not from a funny costume.

## Proportions (Godot metres, faces -Z, feet at the origin)
- About 1.78 m to the top of the hair, 5.5 heads tall: big head, short legs, big hands and shoes.
- Eyes at 1.62 m (the first-person camera).
- Shoulders at about 1.40 m, crotch about 0.72 m.

## Face (moves by node transforms and visibility only, per the art contract)
- Big round eyes: white, pupil and highlight. Pupils move for gaze. Skin eyelids rotate for blinks and sleepy looks.
- Chunky brows, separate nodes.
- Mouth set, swapped by visibility: smile, open, grimace, tongue.
- Blush discs, hidden by default (embarrassment).

## Outfit
Cosy home clothes that work at home and at the office: sweatshirt with ribbed cuffs and hem, roomy trousers with rolled
cuffs, chunky sneakers. Three colourways on the sheet for the user to pick.

## Not yet
Rig, skinning and clips come after the look is approved (same order as the hands). Node names will be agreed with
gameplay first (`coordination/interfaces.md`); the current procedural avatar is `src/human/human_avatar.tscn` in game.

## Blockout v1 (2026-10-15, for review)
- Build: `scripts/human/build.py` → `human/art/human.glb` (colourway A) and `previews/human/human_[ABC].glb`. About 37k triangles.
- Look-dev: `scripts/tools/capture_human.sh NAME [--mode single|lineup|faces] --shots ...`. Review sheets are in
  `previews/human/screenshots/`: turnaround, mirror, lineup, faces.
- Colourways: A honey hoodie with teal trousers, B teal hoodie with cream trousers, C brick hoodie with graphite trousers.
- Open questions for the user: colourway, age read (it currently reads young), hair.
