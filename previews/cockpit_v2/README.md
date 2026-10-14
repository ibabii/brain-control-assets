# Cockpit v2 look-dev

Goal: match `concepts/cockpit/cockpit-warm-ceramic-v1.png` from the game camera.

- Build: `/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/cockpit_v2/build.py`
  → `cockpit/art/cockpit_art.glb`, `cockpit/art/layout.json`, `source/cockpit/cockpit_v2.blend`, `preview_screens.glb`.
- Preview: run `cockpit_v2_preview.tscn`. O cycles the concept overlay, S toggles preview screen content, T the task label.
- Capture: `Godot --path . res://previews/cockpit_v2/cockpit_v2_preview.tscn -- --capture <name>`.

Printed items (notes, labels, book spines, can, mug, trinkets) are textured from the concept, projected from the game camera; their geometry is real. Walls, housings, gauges, console, controls and cables are modelled.
Screen content here is a preview stand-in; the game renders live screens at the anchors in `layout.json`.
