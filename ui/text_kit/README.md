# Text kit (2D)

Built by `scripts/text_kit/build.py` (Blender headless). Contract: `coordination/interfaces.md`, "Intercom, answering machine, text kit". Colours: paper `#F4ECDC`, graphite ink `#3A3532`, style `warm_ceramic_v1`. Review sheet: `preview_sheet.png`.

**NPC speech bubble** (drawn on the front-screen SubViewport):
- `bubble_9slice.png`: 128 px, 9-slice margins of 44 px on every side (NinePatchRect, stretch mode). The content inset is about 24 px.
- `bubble_tail.png`: 64 × 72, pointing down-left. Overlap the bubble's bottom edge by 10 px so the tail's paper covers that stretch of outline. Use `flip_h` for a tail pointing down-right.
- **Bernard's bubble:** `bubble_bernard_9slice.png` (honey `#E7B865`, same 44 px margins) plus `bubble_bernard_tail.png` (64 × 72, points straight down, tip at x 32). It rises from the bottom centre of the front screen. Overlap the tail by 10 px, the same as the NPC tail.
- `scribble_glyphs.png`: 12 cursive gibberish "words" in 56 × 72 cells, baseline at y 58, cap height about 44, matching the key-word caps at 64 px. Pick them at random, scale with the font size, and leave a gap of about 0.3 of a cell between words.
- Key words: **Patrick Hand** (OFL, `cockpit/art/notes/fonts/PatrickHand-Regular.ttf`), the same hand as the sticky notes and the TODAY list.
  - Upper case, with FontVariation `variation_embolden` 0.8 for the bold hand-letter look.
  - Graphite, at 40 px or larger.

**Reveal lower-third:**
- `lower_third_bar.png`: 512 × 112. As a NinePatchRect, use left margin 120, right 40, top and bottom 0, so it stretches horizontally only.
  - The portrait disc is centred at (58, 62), with room for an icon up to 88 px. Put the matching `icon_*` on it at about 84 px.
  - Text is the commentary LINE (≤40 chars), not a name; the portrait disc says who. Use Patrick Hand caps, font size 40 (cap ≈20 px at 1080p), cream `#F4ECDC`, in the teal area from x 130 to (width − 48), vertically centred at y 66.
  - Stretch the bar to fit. A 40-char line is about 475 px, so a bar of about 760 px wide works. See `preview_lower_third.png` (1:1, 1080p pixels).
- Icons are 128 px with straight alpha and read at 64 px. All four use the same shapes and lit colours as the intercom lamps (brain peach `#EAA78B`): `icon_heart.png`, `icon_stomach.png`, `icon_brain.png` and `icon_gary.png`. 

**Intercom display glyphs:** `cockpit/art/intercom/dotmatrix_5x7.json` (see the intercom section of the contract).

Palette: paper, graphite, honey, teal, clay, sage and peach only. There's no purple anywhere, because purple and lavender are reserved for the Lady (beret and scarf).
