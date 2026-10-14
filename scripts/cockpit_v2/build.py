"""Cockpit v2 art build. Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python scripts/cockpit_v2/build.py
Writes source/cockpit/cockpit_v2.blend, cockpit/art/cockpit_art.glb and cockpit/art/layout.json.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

import bpy  # noqa: E402

import brain  # noqa: E402
import dressing  # noqa: E402
import hardware  # noqa: E402
import lib  # noqa: E402

t0 = time.time()
lib.reset()
root = lib.empty('CockpitArt')
root['style_id'] = 'warm_ceramic_v1 / cockpit concept v1'
shell = lib.empty('Shell', (0, 1.5, -0.3), root)
brain.build(shell)
shelf_top = hardware.build(root)
bulbs = dressing.build(root, shelf_top)

os.makedirs(lib.ROOT + '/cockpit/art', exist_ok=True)
glb = lib.ROOT + '/cockpit/art/cockpit_art.glb'
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', export_yup=True, export_apply=True,
                          export_cameras=False, export_lights=False, export_extras=True,
                          export_image_format='AUTO')
for o in bpy.data.objects:
    o.select_set(False)
screens = hardware.preview_screens()
for o in [screens, *screens.children_recursive]:
    o.select_set(True)
os.makedirs(lib.ROOT + '/previews/cockpit_v2', exist_ok=True)
bpy.ops.export_scene.gltf(filepath=lib.ROOT + '/previews/cockpit_v2/preview_screens.glb', export_format='GLB',
                          export_yup=True, use_selection=True, export_cameras=False, export_lights=False)
for o in [*screens.children_recursive, screens]:
    bpy.data.objects.remove(o)
layout = {
    'layout': hardware.LAYOUT_NAME,
    'camera': {'position': list(lib.CAM), 'pitch_deg': -14, 'fov_deg': 68},
    'screens': hardware.LAYOUT,
    'console': {'position': list(hardware.CONSOLE.o), 'rotation_deg': [18, 0, 0]},
    'dials': {'position': list(hardware.DIALS.o), 'x': hardware.DIAL_X, 'names': hardware.GAUGES},
    'shelf_top_y': shelf_top,
    'fairy_bulbs': [list(p) for p in bulbs],
}
with open(lib.ROOT + '/cockpit/art/layout.json', 'w') as f:
    json.dump(layout, f, indent=2, default=float)
import hashlib  # noqa: E402
manifest_path = lib.ROOT + '/cockpit/art/manifest.json'
if os.path.exists(manifest_path):
    with open(manifest_path) as f:
        manifest = json.load(f)
    with open(glb, 'rb') as f:
        manifest['model_sha256'] = hashlib.sha256(f.read()).hexdigest()
    manifest['triangles'] = lib.count_tris()
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
bpy.ops.wm.save_as_mainfile(filepath=lib.ROOT + '/source/cockpit/cockpit_v2.blend')
print('COCKPIT_V2_BUILT tris=%d objects=%d seconds=%.1f' % (lib.count_tris(), len(lib.COLL.objects), time.time() - t0))
