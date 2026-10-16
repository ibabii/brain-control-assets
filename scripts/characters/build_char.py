"""Character system phase 2 (coordination/character_system_plan.md, contract: interfaces.md "Characters").
One base body per run, built with the Human build (scripts/human/build.py, spec in env HUMAN_SPEC) in T-pose and
exported as separate pieces on the same skeleton:
  characters/<base>/art/<base>.glb (+ <base>_rig.json, character.json): rig v1 body, skin mannequin split into
      Body_<Region> meshes, hands, clips, ragdoll, markers
  characters/parts/<id>/art/<id>.glb (+ part.json): head (skinned neck + rigid face parts), hair (rigid), hoodie,
      joggers, sneakers (skinned, hide the regions they cover)
Blend shapes on the body and every outfit layer: Build_Slim, Build_Heavy (shared displacement fields, so layers move
together) and, on the female base, Chest_Size. Run: scripts/characters/build_char.sh <male|female>.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

BASE = os.environ.get('CHAR_BASE', 'male')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'human'))
import build as hb  # noqa: E402  (reads HUMAN_SPEC / HUMAN_ARM_UP set by build_char.sh)
import lib  # noqa: E402
import rig as R  # noqa: E402
from lib import B, G  # noqa: E402
from sculpt import meta, ell, cap, ball, solid, adopt  # noqa: E402

FEMALE = hb.FEMALE
ROOT = lib.ROOT
PARTS = {  # part id -> (slot, mesh name prefixes, hides)
    'hoodie': ('top', ('Top', 'Hem', 'Collar', 'Cuff', 'Pocket', 'String', 'Aglet'),
               ['Body_Torso', 'Body_UpperArmL', 'Body_UpperArmR', 'Body_LowerArmL', 'Body_LowerArmR']),
    'joggers': ('bottom', ('Pants', 'PantCuff'),
                ['Body_Hips', 'Body_UpperLegL', 'Body_UpperLegR', 'Body_LowerLegL', 'Body_LowerLegR']),
    'sneakers': ('shoes', ('Sole', 'Upper', 'Lace', 'Stripe'), ['Body_FootL', 'Body_FootR']),
}
SFX = '_f' if FEMALE else '_m'
HEAD_ID, HAIR_ID = ('head_female', 'hair_bun') if FEMALE else ('head_bernard', 'hair_bernard')
LAYERS = ('Top', 'Hem', 'Collar', 'Cuff', 'Pocket', 'String', 'Aglet', 'Pants', 'PantCuff')   # get the build keys


# --- the skin mannequin ---------------------------------------------------------------------------------------

def mannequin(parent):
    """A plain clay body under the clothes (hidden where an outfit covers it): torso, arms, legs, socked feet."""
    v = hb.TOP_VOL
    m = lambda s, x: hb.mirror(x, s)
    torso = meta('BodyTorso', 0.008)
    c = v['chest']
    ell(torso, (0, 1.22, 0.0), (c[0] - 0.03, c[1] - 0.01, c[2] - 0.03))
    bl = v['belly']
    ell(torso, (0, 1.04, v['belly_z'] * 0.5), (bl[0] - 0.035, bl[1] - 0.01, bl[2] - 0.035))
    pe = v['pelvis']
    ell(torso, (0, 0.88, 0.004), (pe[0] - 0.02, pe[1] - 0.01, pe[2] - 0.02))
    cap(torso, (-0.15, 1.33, 0.004), (0.15, 1.33, 0.004), v['shoulder'] - 0.018)
    cap(torso, (0, 1.30, 0.008), (0, 1.43, 0.008), 0.048)                       # neck stub (into the head's neck)
    fams, R.PARTS['body'] = [torso], {}
    for s, side in ((-1, 'L'), (1, 'R')):
        arm = meta('BodyArm' + side, 0.007)
        sh, el, wr = m(s, hb.SHOULDER), m(s, hb.ELBOW), m(s, hb.WRIST)
        cap(arm, sh, el, 0.046 * v['limb'])
        cap(arm, el, wr - m(s, hb.FORE) * 0.02, 0.038 * v['limb'])
        leg = meta('BodyLeg' + side, 0.008)
        h, k, a = m(s, hb.HIP), m(s, hb.KNEE), m(s, hb.ANKLE_J)
        cap(leg, h, k, 0.072 * v['leg'])
        cap(leg, k, a + Vector((0, 0.03, 0)), 0.055 * v['leg'])
        foot = meta('BodyFoot' + side, 0.006)
        cap(foot, a + Vector((0, -0.01, 0.03)), Vector((a.x, 0.035, -0.15)), 0.04)
        R.PARTS['body'].update({side: R.meta_tree(arm), 'L' + side: R.meta_tree(leg), 'F' + side: R.meta_tree(foot)})
        fams += [arm, leg, foot]
    R.PARTS['body']['torso'] = R.meta_tree(torso)
    return adopt(solid('BodySkin', fams, 0.006, 9000, lib.mat('Skin', hb.SKIN, 0.55)), parent, (0, 0.9, 0))


def body_weights(p):
    """Mannequin weights: the nearest family decides torso / arm / leg / foot, soft seams between them."""
    share = R._part_blend(p, R.PARTS['body'])
    w = {}
    for part, f in share.items():
        if part == 'torso':
            pw = R.torso(p)
        elif part in ('L', 'R'):
            pw = R.arm_w(p, -1 if part == 'L' else 1, hb.LANDMARKS)
        elif part[0] == 'L':
            pw = R.leg_w(p, -1 if part[1] == 'L' else 1, hb.LANDMARKS)
        else:
            pw = {R.side_name(-1 if part[1] == 'L' else 1) + 'Foot': 1.0}
        w = R.mix(w, pw, f) if w else {k: x * f for k, x in pw.items()}
    return w


# --- build keys -----------------------------------------------------------------------------------------------

def _gauss(x):
    return math.exp(-x * x)


def build_offset(p, heavy):
    """Build key displacement (canonical space) at p: radial from the nearest body axis, a belly in front (heavy) or
    a flatter middle (slim). Soft-min blended between axes so shoulders and hips don't crease."""
    L, m = hb.LANDMARKS, hb.mirror
    segs = [('torso', Vector((0, 0.84, 0)), Vector((0, 1.42, 0)))]
    for s in (-1, 1):
        segs += [('uarm', m(L['SHOULDER'], s), m(L['ELBOW'], s)), ('larm', m(L['ELBOW'], s), m(L['WRIST'], s)),
                 ('uleg', m(L['HIP'], s), m(L['KNEE'], s)), ('lleg', m(L['KNEE'], s), m(L['ANKLE_J'], s))]
    acc, tot = Vector(), 0.0
    for kind, a, b in segs:
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
        c = a + ab * t
        r = p - c
        if kind == 'torso':
            r.y = 0.0
        d = r.length
        if d < 1e-6:
            continue
        n = r / d
        if kind == 'torso':
            if heavy:
                amt = 0.012 + 0.012 * _gauss((p.y - 1.22) / 0.08) + 0.024 * _gauss((p.y - 0.9) / 0.08)
                amt += 0.05 * _gauss((p.y - 1.03) / 0.1) * max(0.0, -n.z)              # belly in front
            else:
                amt = -0.008 - 0.014 * _gauss((p.y - 1.03) / 0.1) * max(0.0, -n.z)
        else:
            amt = {'uarm': (0.014, -0.006), 'larm': (0.009, -0.004), 'uleg': (0.022, -0.008),
                   'lleg': (0.012, -0.005)}[kind][0 if heavy else 1]
        w = math.exp(-d / 0.03)
        acc += n * amt * w
        tot += w
    return acc / tot if tot else Vector()


# --- weights by transfer ------------------------------------------------------------------------------------

def transfer(o, src_pts, src_ws, tree):
    """Weights for an attachment (rib band, pocket, strings) from the nearest points of its layer, so it deforms
    exactly with the surface it sits on (no rubber rings, no pocket poking out)."""
    out = []
    for v in o.data.vertices:
        p = G(o.matrix_world @ v.co)
        near = tree.find_n(p, 4)
        w, tw = {}, 0.0
        for _, i, d in near:
            k = 1.0 / max(d, 1e-4)
            tw += k
            for b, x in src_ws[i].items():
                w[b] = w.get(b, 0.0) + x * k
        out.append({b: x / tw for b, x in w.items()})
    return out


def top4(w):
    best = sorted(w.items(), key=lambda kv: -kv[1])[:4]
    t = sum(x for _, x in best) or 1.0
    return {b: x / t for b, x in best}


# --- regions --------------------------------------------------------------------------------------------------

def region_of(bone):
    side = 'L' if bone.startswith('Left') else 'R' if bone.startswith('Right') else ''
    for key, reg in (('UpperArm', 'UpperArm'), ('LowerArm', 'LowerArm'), ('UpperLeg', 'UpperLeg'),
                     ('LowerLeg', 'LowerLeg'), ('Foot', 'Foot'), ('Toes', 'Foot')):
        if key in bone:
            return reg + side
    return 'Hips' if bone == 'Hips' else 'Torso'


def split_regions(o):
    """BodySkin -> Body_<Region> objects by each face's dominant bone (groups and shape keys come along)."""
    gname = {g.index: g.name for g in o.vertex_groups}
    dom = []
    for v in o.data.vertices:
        g = max(v.groups, key=lambda x: x.weight) if v.groups else None
        dom.append(region_of(gname[g.group]) if g else 'Torso')
    face_reg = []
    for f in o.data.polygons:
        regs = [dom[i] for i in f.vertices]
        face_reg.append(max(set(regs), key=regs.count))
    out = []
    for reg in sorted(set(face_reg)):
        bpy.ops.object.mode_set(mode='OBJECT')
        for x in bpy.data.objects:
            x.select_set(x == o)
        bpy.context.view_layer.objects.active = o
        for f, r in zip(o.data.polygons, face_reg):
            f.select = r == reg
        if not any(f.select for f in o.data.polygons):
            continue
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        new = [x for x in bpy.context.selected_objects if x != o][0]
        new.name = 'Body_' + reg
        new.data.name = new.name
        face_reg = [r for r in face_reg if r != reg]
        out.append(new)
    bpy.data.objects.remove(o, do_unlink=True)
    return out


def ensure_uvs(o):
    """A simple cylindrical UV map (Godot needs UVs for tangents; the clay materials don't use them)."""
    if o.type != 'MESH' or o.data.uv_layers:
        return
    uv = o.data.uv_layers.new(name='UVMap')
    mw = o.matrix_world
    for loop in o.data.loops:
        p = G(mw @ o.data.vertices[loop.vertex_index].co)
        uv.data[loop.index].uv = (0.5 + math.atan2(p.x, -p.z) / (2 * math.pi), p.y / 2.0)


# --- build ----------------------------------------------------------------------------------------------------

def main():
    cw = hb.COLOURWAYS['A']
    lib.reset()
    root = lib.empty('Character', (0, 0, 0))
    body = lib.empty('Body', (0, 0, 0), root)
    head = hb.head_parts(root)
    hb.outfit(cw, 'A', body)
    img, nrm = hb.rib_texture('#FFFFFF')                    # neutral ribs: the 'rib' paint slot tints them
    rib = lib.mat('Rib', '#FFFFFF', 0.9, image=img, normal=nrm)
    for o in bpy.data.objects:
        if o.name.startswith(('Hem', 'Collar', 'Cuff')):
            o.data.materials[0] = rib
    hb.hands(body)
    mannequin(body)
    hb.matte()
    table = hb.rig_table()
    rig = R.armature(table, root)
    # weights from the canonical shape (layers first: the attachments copy them)
    canon, wts = {}, {}
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in meshes:
        canon[o.name] = [G(o.matrix_world @ v.co) for v in o.data.vertices]
    for o in meshes:
        if o.name.startswith(('Hand', 'Nails')):
            if o.name.startswith('Hand'):
                R.soften_knuckles(o, -1 if o.name.endswith('L') else 1)
            continue
        if o.name == 'BodySkin':
            wts[o.name] = R.smooth(o, [body_weights(p) for p in canon[o.name]], 4)
        elif o.name in ('Top', 'Pants'):
            kind = hb.SKIN_KIND[0 if o.name == 'Top' else 1]
            wts[o.name] = R.smooth(o, R.weights_for(o, kind[1], hb.LANDMARKS), kind[2])
        elif o.name == 'HeadSkin':
            wts[o.name] = R.smooth(o, R.weights_for(o, 'neck', hb.LANDMARKS), 3)
        elif o.name.startswith(('Sole', 'Upper', 'Lace', 'Stripe')):
            wts[o.name] = R.weights_for(o, 'foot', hb.LANDMARKS)
    if hb.SPEC['chest']:
        for n in ('Top', 'BodySkin'):
            wts[n] = [hb.chest_weights(p, w) for p, w in zip(canon[n], wts[n])]
    trees = {}
    for n in ('Top', 'Pants'):
        t = KDTree(len(canon[n]))
        for i, p in enumerate(canon[n]):
            t.insert(p, i)
        t.balance()
        trees[n] = t
    for o in meshes:
        if os.environ.get('CHAR_OLDBANDS') and o.name.startswith(('Hem', 'Collar', 'Pocket', 'String', 'Aglet', 'Cuff',
                                                                   'PantCuff')):
            kind = next((k, n) for pre, k, n in hb.SKIN_KIND if o.name.startswith(pre))  # the v1 band weights
            ws = R.weights_for(o, kind[0], hb.LANDMARKS)
            wts[o.name] = R.smooth(o, ws, kind[1]) if kind[1] else ws
        elif o.name.startswith(('Hem', 'Collar', 'Cuff', 'Pocket', 'String', 'Aglet')):
            wts[o.name] = [top4(w) for w in transfer(o, canon['Top'], wts['Top'], trees['Top'])]
        elif o.name.startswith('PantCuff'):
            wts[o.name] = [top4(w) for w in transfer(o, canon['Pants'], wts['Pants'], trees['Pants'])]
    # blend shapes: fields on the body and the layers; attachments copy their layer's offsets (they stay on it)
    fields = {'Build_Slim': lambda c: build_offset(c, False), 'Build_Heavy': lambda c: build_offset(c, True)}
    if hb.SPEC['chest']:
        fields['Chest_Size'] = lambda c: hb.bust(c)[1]
    own = {}
    for n in ('BodySkin', 'Top', 'Pants'):
        own[n] = {k: [f(c) for c in canon[n]] for k, f in fields.items()
                  if k != 'Chest_Size' or any(hb.bust(c)[0] > 0 for c in canon[n])}

    def keys_for(name):
        if name in own:
            return own[name]
        host = 'Pants' if name.startswith('PantCuff') else 'Top' if name.startswith(LAYERS) else None
        if host is None:
            return {}
        out = {}
        for k, offs in own[host].items():
            col = []
            for c in canon[name]:
                acc, tw = Vector(), 0.0
                for _, i, d in trees[host].find_n(c, 4):
                    acc += offs[i] / max(d, 1e-4)
                    tw += 1.0 / max(d, 1e-4)
                col.append(acc / tw)
            if any(v.length > 1e-5 for v in col):
                out[k] = col
        return out

    # warp to the spec, skin, blend shapes
    for o in meshes:
        mw = o.matrix_world.copy()
        inv = mw.inverted()
        if o.name.startswith(('Hand', 'Nails')):
            wr = hb.mirror(hb.WRIST, -1 if o.name.endswith('L') else 1)
            if not hb.IDENT:
                o.matrix_world = Matrix.Translation(B(hb.warp(wr) - wr)) @ mw
            R.skin(o, [], rig)
            continue
        if o.name not in wts:
            continue                                           # rigid head parts and hair
        for v, c in zip(o.data.vertices, canon[o.name]):
            v.co = inv @ B(hb.warp(c))
        R.skin(o, wts[o.name], rig)
        if keys_for(o.name):
            o.shape_key_add(name='Basis')
            for name, offs in keys_for(o.name).items():
                sk = o.shape_key_add(name=name)
                for i, c in enumerate(canon[o.name]):
                    sk.data[i].co = inv @ B(hb.warp(c + offs[i]))
    if not hb.IDENT:
        head.matrix_world = Matrix.Translation(B(hb.warp(hb.NECK) - hb.NECK)) @ head.matrix_world
        bpy.context.view_layer.update()
    regions = split_regions(bpy.data.objects['BodySkin'])
    for o in bpy.data.objects:
        ensure_uvs(o)
    # clips: the face rides the Head bone while baking (ground checks), then goes back to character space at rest
    face_mw = head.matrix_world.copy()
    R.attach(head, rig, 'Head')
    rig['clips'] = R.clips(rig, hb.ARM_UP, hb.LANDMARKS, full=hb.SPEC['clips'] == 'all', mock=hb.SPEC['mock'])
    if os.environ.get('CHAR_CHECK'):
        clearance(rig)
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    head.parent = None
    head.matrix_world = face_mw
    bpy.context.view_layer.update()                    # the hair's world matrix follows only after an update
    hair = bpy.data.objects['Hair']
    hmw = hair.matrix_world.copy()
    hair.parent = None
    hair.matrix_world = hmw
    bpy.context.view_layer.update()
    export_all(rig, head, hair, regions)


# --- clearance check (CHAR_CHECK=1) ---------------------------------------------------------------------------



BANDS = {'Top': ('Hem', 'Pocket', 'Collar', 'CuffL', 'CuffR', 'StringL', 'StringR'), 'Pants': ('PantCuffL', 'PantCuffR')}


def clearance(rig):
    """Bands and the pocket riding their layer: per vertex, the change of its distance to the Top/Pants surface from
    the base build at rest (to the same layer verts, paired at bind), for each build key (and chest size), at rest and through clip frames. A rubber ring or a
    pocket poking through shows as drift. Prints CLEAR <case> <band>: max drift mm (p99) per case."""
    from mathutils.bvhtree import BVHTree
    keyed = [o for o in bpy.data.objects if o.type == 'MESH' and o.data.shape_keys]
    cases = [('base', {}), ('slim', {'Build_Slim': 1}), ('heavy', {'Build_Heavy': 1})]
    if hb.SPEC['chest']:
        cases += [('chest1', {'Chest_Size': 1}), ('heavy_chest1', {'Build_Heavy': 1, 'Chest_Size': 1})]
    poses = [(None, 0)] + [(n, f) for n in ('squat', 'walk_loop', 'sit_tub', 'sit_floor', 'get_up_back', 'faceplant')
                           if n in bpy.data.actions for f in range(0, int(bpy.data.actions[n].frame_range[1]) + 1, 6)]
    ref, pairs = {}, {}
    for cname, vals in cases:
        for o in keyed:
            for kb in o.data.shape_keys.key_blocks[1:]:
                kb.value = vals.get(kb.name, 0.0)
        drift = {}
        for act, f in poses if os.environ.get('CHAR_CHECK') != '2' else poses[:1]:
            rig.animation_data.use_nla = act is None
            rig.animation_data.action = bpy.data.actions[act] if act else None
            if act is None:
                for pb in rig.pose.bones:
                    pb.rotation_quaternion, pb.location = (1, 0, 0, 0), (0, 0, 0)
            bpy.context.scene.frame_set(f)
            dg = bpy.context.evaluated_depsgraph_get()
            for host, bands in BANDS.items():
                co = bpy.data.objects[host].evaluated_get(dg)
                hv = [co.matrix_world @ v.co for v in co.to_mesh().vertices]
                co.to_mesh_clear()
                for bn in bands:
                    o = bpy.data.objects[bn]
                    ev = o.evaluated_get(dg)
                    pts = [o.matrix_world @ v.co for v in ev.to_mesh().vertices]
                    ev.to_mesh_clear()
                    if bn not in pairs:                  # fixed correspondences: the layer verts nearest at bind
                        h = bpy.data.objects[host]
                        t = KDTree(len(h.data.vertices))
                        for i, v in enumerate(h.data.vertices):
                            t.insert(h.matrix_world @ v.co, i)
                        t.balance()
                        pairs[bn] = [[i for _, i, _ in t.find_n(o.matrix_world @ v.co, 4)] for v in o.data.vertices]
                    d = [(x - sum((hv[i] for i in ids), Vector()) / len(ids)).length for x, ids in zip(pts, pairs[bn])]
                    if bn not in ref:
                        ref[bn] = d
                    if act is None and os.environ.get('CHAR_CHECK') == '2':
                        dd = [x - y for x, y in zip(d, ref[bn])]
                        i = max(range(len(dd)), key=lambda j: abs(dd[j]))
                        print('REST', cname, bn, '%.1fmm at y %.3f' % (dd[i] * 1000, G(pts[i]).y))
                    dd = sorted(abs(x - y) for x, y in zip(d, ref[bn]))
                    key = bn.rstrip('LR') if bn not in ('Hem', 'Pocket', 'Collar') else bn
                    m, p99 = dd[-1], dd[int(len(dd) * 0.99)]
                    old = drift.get(key, (0, 0, ''))
                    if m > old[0]:
                        drift[key] = (m, max(p99, old[1]), '%s@%d' % (act or 'rest', f))
                    else:
                        drift[key] = (old[0], max(p99, old[1]), old[2])
        print('CLEAR', cname, '  '.join('%s %.0fmm (p99 %.0f) %s' % (k, v[0] * 1000, v[1] * 1000, v[2])
                                       for k, v in sorted(drift.items())))
    for o in keyed:
        for kb in o.data.shape_keys.key_blocks[1:]:
            kb.value = 0.0
    rig.animation_data.use_nla = True


# --- export ---------------------------------------------------------------------------------------------------

def _export(path, objs, anims):
    bpy.context.scene.render.fps, bpy.context.scene.render.fps_base = R.FPS, 1.0
    for o in bpy.data.objects:
        o.select_set(o in objs)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kw = dict(export_animation_mode='NLA_TRACKS', export_force_sampling=True) if anims else dict(export_animations=False)
    lib.export_glb(filepath=path, export_format='GLB', export_yup=True, use_selection=True, export_cameras=False,
                   export_lights=False, export_extras=True, export_skins=True, export_morph=True,
                   export_morph_normal=True, **kw)


def _tscn(folder, name):
    path = os.path.join(folder, name + '.tscn')
    rel = os.path.relpath(os.path.join(folder, name + '.glb'), ROOT)
    with open(path, 'w') as f:
        f.write('[gd_scene format=3]\n\n[ext_resource type="PackedScene" path="res://%s" id="1"]\n\n'
                '[node name="%s" instance=ExtResource("1")]\n' % (rel, name))


def _json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=1)


def export_all(rig, head, hair, regions):
    base = BASE + '_base'
    out = os.path.join(ROOT, 'characters', base, 'art')
    bodies = regions + [o for o in bpy.data.objects if o.name.startswith(('HandL', 'HandR', 'NailsL', 'NailsR'))]
    _export(os.path.join(out, base + '.glb'), [rig] + bodies, True)
    _tscn(out, base)
    face = [o for o in head.children_recursive if o != hair and o not in hair.children_recursive]
    face.append(bpy.data.objects['HeadSkin'])
    hidden = [o.name for o in face if o.get('hidden')]
    hb.rig_json(os.path.join(out, base + '_rig.json'), hidden)    # hidden + expressions: the default head's face parts
    parts = {'head': HEAD_ID, 'hair': HAIR_ID, 'top': 'hoodie' + SFX, 'bottom': 'joggers' + SFX, 'shoes': 'sneakers' + SFX}
    cj = {'parts': parts, 'paint': PAINT, 'colors': COLORS, 'shapes': {'Build_Slim': 0.0, 'Build_Heavy': 0.0}}
    if hb.SPEC['chest']:
        cj['shapes']['Chest_Size'] = 0.5
        cj['chest'] = {'chains': [['LeftBreast', 'LeftBreast'], ['RightBreast', 'RightBreast']], 'radius': 0.05,
                       'tip_dir': [0, 0, -1], 'tip': 0.1}
    _json(os.path.join(out, 'character.json'), cj)
    pdir = lambda pid: os.path.join(ROOT, 'characters', 'parts', pid, 'art')
    # head: skinned neck (HeadSkin) + rigid face parts in character space at rest
    _export(os.path.join(pdir(HEAD_ID), HEAD_ID + '.glb'), [rig, head] + face, False)
    _tscn(pdir(HEAD_ID), HEAD_ID)
    _json(os.path.join(pdir(HEAD_ID), 'part.json'), {'slot': 'head', 'attach': 'Head', 'hidden': hidden,
                                                       'expressions': hb.EXPRESSIONS})
    _export(os.path.join(pdir(HAIR_ID), HAIR_ID + '.glb'), [hair], False)
    _tscn(pdir(HAIR_ID), HAIR_ID)
    _json(os.path.join(pdir(HAIR_ID), 'part.json'), {'slot': 'hair', 'attach': 'Head'})
    for pid, (slot, prefixes, hides) in PARTS.items():
        objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(prefixes)]
        _export(os.path.join(pdir(pid + SFX), pid + SFX + '.glb'), [rig] + objs, False)
        _tscn(pdir(pid + SFX), pid + SFX)
        _json(os.path.join(pdir(pid + SFX), 'part.json'), {'slot': slot, 'hides': hides})
    print('CHAR_BUILT', base, len(regions), 'regions:', ' '.join(sorted(o.name for o in regions)))


PAINT = {'CK2_Rib': 'rib', 'CK2_Skin': 'skin', 'CK2_Hair': 'hair', 'CK2_Brow': 'hair', 'CK2_Pupil': 'eyes', 'CK2_Blush': 'blush'}
COLORS = {'skin': hb.SKIN, 'hair': hb.HAIR, 'eyes': '#2E2624', 'blush': '#EE9488'}
for _m, _slot in (('Top', 'top'), ('Pants', 'bottom'), ('PantCuff', 'bottom'), ('Shoe', 'shoes')):
    _key = {'Top': 'top', 'Pants': 'pants', 'PantCuff': 'pants', 'Shoe': 'shoe'}[_m]
    PAINT['CK2_' + _m + hb.COLOURWAYS['A'][_key][1:]] = _slot
COLORS.update(rib=hb.COLOURWAYS['A']['rib'], top=hb.COLOURWAYS['A']['top'], bottom=hb.COLOURWAYS['A']['pants'], shoes=hb.COLOURWAYS['A']['shoe'])

main()
