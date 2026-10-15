# Text kit (2D)

Built by `scripts/text_kit/build.py` (Blender headless). Contract: `coordination/interfaces.md`, "Intercom, answering machine, text kit". Colours: paper `#F4ECDC`, graphite ink `#3A3532`, style `warm_ceramic_v1`. Review sheet: `preview_sheet.png`.

**NPC speech bubble** (drawn on the front-screen SubViewport):
- `bubble_9slice.png`: 128 px, 9-slice margins of 44 px on every side (NinePatchRect, stretch mode). The content inset is about 24 px.
- `bubble_tail.png`: 64 × 72, pointing down-left. Overlap the bubble's bottom edge by 10 px so the tail's paper covers that stretch of outline. Use `flip_h` for a tail pointing down-right.
- `scribble_glyphs.png`: 12 cursive gibberish "words" in 56 × 72 cells, baseline at y 58, cap height about 44, matching the key-word caps at 64 px. Pick them at random, scale with the font size, and leave a gap of about 0.3 of a cell between words.
- Key words: **Patrick Hand** (OFL, `cockpit/art/notes/fonts/PatrickHand-Regular.ttf`), the same hand as the sticky notes and the TODAY list.
  - Upper case, with FontVariation `variation_embolden` 0.8 for the bold hand-letter look.
  - Graphite, at 40 px or larger.

**Reveal lower-third:**
- `lower_third_bar.png`: 512 × 112. As a NinePatchRect, use left margin 120, right 40, top and bottom 0, so it stretches horizontally only.
  - The portrait disc is centred at (58, 62), with room for an icon up to 88 px. Put the matching `icon_*` on it at about 84 px.
  - Name text: Patrick Hand caps, cream `#F4ECDC`, in the teal area at x 130 to (width − 48), vertically centred at y 66.
- Icons are 128 px with straight alpha and read at 64 px: `icon_heart.png`, `icon_stomach.png`, `icon_brain.png` and `icon_gary.png`. Heart, stomach and Gary use the same shapes and colours as the intercom lamps.

**Intercom display glyphs:** `cockpit/art/intercom/dotmatrix_5x7.json` (see the intercom section of the contract).
