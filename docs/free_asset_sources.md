# Free asset sourcing

Checked 2026-10-14 on the creators' own pages. Prefer CC0 candidates and adapt them to `warm_ceramic_v1` rather than retaining an unrelated palette or surface treatment.

| Source | Relevant packs | Status |
| --- | --- | --- |
| Kenney | [Furniture Kit](https://kenney.nl/assets/furniture-kit), [Food Kit](https://kenney.nl/assets/food-kit) | Downloaded from official free links. Both archive License.txt files confirm CC0. Books, mug, soda can, and doughnut used in the cockpit blockout. |
| Quaternius | [Ultimate House Interior](https://quaternius.com/packs/ultimatehomeinterior.html), [Ultimate Food](https://quaternius.com/packs/ultimatefood.html) | Official pack pages state CC0. Useful alternatives for future clutter; not downloaded or used yet. |
| Poly Haven | [Models](https://polyhaven.com/models), [asset licence](https://polyhaven.com/license) | Official asset licence is CC0. Potential source for unusual props; assess geometry and realistic texture complexity before using. Not downloaded or used. |

Original selected Kenney files, required source texture, and included licences are retained under `source/vendor/kenney/selected/`. Full downloaded packs remain in ignored `.local/downloads/kenney/` to avoid adding hundreds of unused files to the repository. Original/archive checksums, source URLs, selected node names, and adaptations are recorded in `source/vendor/kenney/sources.json` and the blockout manifest. Godot ignores the source directory.

The adapted blockout uses flat palette materials and embeds them in its GLB, so the original palette texture is not a runtime dependency. Credit Kenney voluntarily in the final credits. Reusable dressing is a good fit for sourced models; screen housings, the brain enclosure, and moving controls remain custom because composition and gameplay interfaces determine their shapes.
