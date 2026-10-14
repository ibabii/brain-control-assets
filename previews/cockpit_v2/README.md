# Cockpit v2 look-dev

Goal: match `concepts/cockpit/cockpit-warm-ceramic-v1.png` from the game camera.

- Build: `/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/cockpit_v2/build.py`
  → `cockpit/art/cockpit_art.glb`, `cockpit/art/layout.json`, `source/cockpit/cockpit_v2.blend`, `preview_screens.glb`.
- Preview: run `cockpit_v2_preview.tscn`. O cycles the concept overlay, S toggles preview screen content, T the task label.
- Capture: `Godot --path . res://previews/cockpit_v2/cockpit_v2_preview.tscn -- --capture <name>`.

Paper notes are real sheets with generated paper textures (`scripts/cockpit_v2/paper.py`, `ink.py`); their wording is live text in `cockpit/art/notes/cockpit_notes.tscn` (written by `notes_scene.py`). Book spines, can, mug, donut, lever box, trinkets and crumpled paper are still concept-projected placeholders, to be replaced by CC0/modelled props. Inspect from another angle: `--eye x,y,z --look x,y,z`.
Screen content here is a preview stand-in; the game renders live screens at the anchors in `layout.json`.
