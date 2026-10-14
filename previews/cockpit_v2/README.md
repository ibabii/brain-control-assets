# Cockpit v2 look-dev

Goal: match `concepts/cockpit/cockpit-warm-ceramic-v1.png` from the game camera.

- Build: `/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/cockpit_v2/build.py`
  → `cockpit/art/cockpit_art.glb`, `cockpit/art/layout.json`, `source/cockpit/cockpit_v2.blend`, `preview_screens.glb`.
- Preview: run `cockpit_v2_preview.tscn`. O cycles the concept overlay, S toggles preview screen content, T the task label.
- Capture: `Godot --path . res://previews/cockpit_v2/cockpit_v2_preview.tscn -- --capture <name>`.

Everything is modelled and textured in Blender: paper notes (`paper.py`, live wording in `cockpit/art/notes/cockpit_notes.tscn` written by `notes_scene.py`), props and trinkets (`props.py`), hand-painted textures and lettering (`ink.py`, Patrick Hand font). No concept pixels in the art. Inspect from another angle: `--eye x,y,z --look x,y,z`.
Screen content here is a preview stand-in; the game renders live screens at the anchors in `layout.json`.

Clipping: after every build run `Blender -b source/cockpit/cockpit_v2.blend --python scripts/cockpit_v2/audit.py`; it must report 0 pairs (it also flags flush surfaces that z-fight and screws that float or overhang).
