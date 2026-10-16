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
import intercom  # noqa: E402
import lib  # noqa: E402
import notes_scene  # noqa: E402
import paper  # noqa: E402

t0 = time.time()
lib.reset()
root = lib.empty('CockpitArt')
root['style_id'] = 'warm_ceramic_v1 / cockpit concept v1'
shell = lib.empty('Shell', (0, 1.5, -0.3), root)
brain.build(shell)
shelf_top = hardware.build(root)
bulbs = dressing.build(root, shelf_top)
ic, ic_layout = intercom.build(root)
lib.conform_tapes()                       # after everything exists: drape tape onto what it holds
# Contract names the machine's reel group `Tape`; if another tape strip took the name first, rename after the
# tape cache, which keys on names.
reels = next(o for o in dressing.MACHINE[0].children if o.name.split('.')[0] == 'Tape')
if reels.name != 'Tape':
    bpy.data.objects['Tape'].name = 'HwTape'
    reels.name = 'Tape'

os.makedirs(lib.ROOT + '/cockpit/art', exist_ok=True)
glb = lib.ROOT + '/cockpit/art/cockpit_art.glb'
# Modules with their own scene (instanced by cockpit_art.tscn) stay out of the main GLB.
modules = {ic: 'intercom/intercom.glb', dressing.MACHINE[0]: 'answering_machine/answering_machine.glb'}
own = {o for m in modules for o in [m, *m.children_recursive]}
for o in bpy.data.objects:
    o.select_set(o.name in lib.COLL.objects and o not in own)
lib.export_glb(filepath=glb, export_format='GLB', export_yup=True, export_apply=True, use_selection=True,
                          export_cameras=False, export_lights=False, export_extras=True,
                          export_image_format='AUTO')
for m, path in modules.items():
    os.makedirs(os.path.dirname(lib.ROOT + '/cockpit/art/' + path), exist_ok=True)
    mw = m.matrix_world.copy()
    m.matrix_world = mw.Identity(4)                # module origin = its local origin
    for o in bpy.data.objects:
        o.select_set(o in m.children_recursive)      # children only: they are the scene's top nodes
    lib.export_glb(filepath=lib.ROOT + '/cockpit/art/' + path, export_format='GLB', export_yup=True,
                   export_apply=True, use_selection=True, export_cameras=False, export_lights=False)
    m.matrix_world = mw
for o in bpy.data.objects:
    o.select_set(False)
screens = hardware.preview_screens()
for o in [screens, *screens.children_recursive]:
    o.select_set(True)
os.makedirs(lib.ROOT + '/previews/cockpit_v2', exist_ok=True)
lib.export_glb(filepath=lib.ROOT + '/previews/cockpit_v2/preview_screens.glb', export_format='GLB',
                          export_yup=True, use_selection=True, export_cameras=False, export_lights=False)
for o in [*screens.children_recursive, screens]:
    bpy.data.objects.remove(o)
layout = {
    'layout': hardware.LAYOUT_NAME,
    'camera': {'position': list(lib.CAM), 'pitch_deg': -14, 'fov_deg': 68},
    'screens': hardware.LAYOUT,
    'console': {'position': list(hardware.CONSOLE.o), 'rotation_deg': [18, 0, 0], 'anchors': hardware.ANCHORS},
    'dials': {'position': list(hardware.DIALS.o), 'x': hardware.DIAL_X, 'names': hardware.GAUGES},
    'pilot_lights': {'nodes': ['PilotLights/' + n for n, _ in hardware.PILOTS], 'lit': hardware.PILOT_LIT,
                     'unlit': hardware.PILOT_UNLIT, 'energy': 1.2},
    'bandwidth_fill': {'node': 'BandwidthFill', 'axis': 'local +X, scale.x 0..1', 'default': 0.15},
    'shelf_top_y': shelf_top,
    'fairy_bulbs': [list(p) for p in bulbs],
    'notes': paper.SLOTS,
    'intercom': ic_layout,
    'answering_machine': {'position': list(dressing.MACHINE[1]), 'yaw_deg': dressing.MACHINE[2]},
}
with open(lib.ROOT + '/cockpit/art/layout.json', 'w') as f:
    json.dump(layout, f, indent=2, default=float)
notes_scene.write(paper.SLOTS)
import hashlib  # noqa: E402
manifest_path = lib.ROOT + '/cockpit/art/manifest.json'
if os.path.exists(manifest_path):
    with open(manifest_path) as f:
        manifest = json.load(f)
    with open(glb, 'rb') as f:
        manifest['model_sha256'] = hashlib.sha256(f.read()).hexdigest()
    manifest['triangles'] = lib.count_tris()
    for c in [*manifest.get('controls', {}).values(), *manifest.get('modules', {}).values()]:           # controls export separately; keep their hashes current
        with open(lib.ROOT + '/' + c['file'], 'rb') as f:
            c['sha256'] = hashlib.sha256(f.read()).hexdigest()
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
bpy.ops.wm.save_as_mainfile(filepath=lib.ROOT + '/source/cockpit/cockpit_v2.blend')
print('COCKPIT_V2_BUILT tris=%d objects=%d seconds=%.1f' % (lib.count_tris(), len(lib.COLL.objects), time.time() - t0))
