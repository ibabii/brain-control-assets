"""Writes cockpit/art/notes/cockpit_notes.tscn: the changeable text on the cockpit paper (script-free).

Sticky notes are Label3D nodes (set `.text`). The TODAY list is a SubViewport page shown on the notebook through a
ViewportTexture: Title (Label) and Item0..Item5 (HBox: Box/Tick TextureRect, Text RichTextLabel with BBCode).
Runs inside the Blender build, or standalone from layout.json: python3 scripts/cockpit_v2/notes_scene.py
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DIR = 'res://cockpit/art/notes/'
FONT_SIZE = 64
EM = 1.18                 # Patrick Hand line height / em
ITEMS = 6


def _color(h):
    h = h.lstrip('#')
    return 'Color(%.3f, %.3f, %.3f, 1)' % tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _xform(s):
    x, y, z = s['basis']
    o = s['position']
    rows = [x[0], y[0], z[0], x[1], y[1], z[1], x[2], y[2], z[2]]
    return 'Transform3D(%s)' % ', '.join('%.6g' % v for v in rows + list(o))


def _str(t):
    return json.dumps(t, ensure_ascii=False)


def write(slots):
    head = ['[gd_scene format=3]', '',
            '[ext_resource type="FontFile" path="%sfonts/PatrickHand-Regular.ttf" id="font"]' % DIR,
            '[ext_resource type="Texture2D" path="%scheck_box.png" id="box"]' % DIR,
            '[ext_resource type="Texture2D" path="%scheck_tick.png" id="tick"]' % DIR, '']
    subs, nodes = [], ['[node name="CockpitNotes" type="Node3D"]', '']
    for id, s in slots.items():
        if s['kind'] == 'label':
            px = s['line_height'] / EM / FONT_SIZE
            nodes += ['[node name="%s" type="Label3D" parent="."]' % id,
                      'transform = %s' % _xform(s),
                      'cast_shadow = 0',
                      'pixel_size = %.6g' % px,
                      'shaded = true',
                      'double_sided = false',
                      'modulate = %s' % _color(s['ink']),
                      'text = %s' % _str(s['default']),
                      'font = ExtResource("font")',
                      'font_size = %d' % FONT_SIZE,
                      'outline_size = 0',
                      'horizontal_alignment = %d' % (0 if s['align'] == 'left' else 1),
                      'line_spacing = -6.0',
                      'autowrap_mode = 3',
                      'width = %.1f' % (s['size'][0] / px), '']
        else:
            w, h = s['size']
            vw, vh = 512, int(round(512 * h / w))
            line = s['line_height'] / h * vh
            fs = int(line / EM)
            subs += ['[sub_resource type="Theme" id="theme_%s"]' % id,
                     'default_font = ExtResource("font")',
                     'default_font_size = %d' % fs,
                     'Label/colors/font_color = %s' % _color(s['ink']),
                     'RichTextLabel/colors/default_color = %s' % _color(s['ink']), '',
                     '[sub_resource type="ViewportTexture" id="vt_%s"]' % id,
                     'resource_local_to_scene = true',
                     'viewport_path = NodePath("%s/Page")' % id, '',
                     '[sub_resource type="StandardMaterial3D" id="ink_%s"]' % id,
                     'resource_local_to_scene = true',
                     'transparency = 1',
                     'albedo_texture = SubResource("vt_%s")' % id,
                     'roughness = 0.8',
                     'texture_filter = 1', '',
                     '[sub_resource type="QuadMesh" id="quad_%s"]' % id,
                     'size = Vector2(%.5g, %.5g)' % (w, h), '']
            d = s['default']
            nodes += ['[node name="%s" type="Node3D" parent="."]' % id, 'transform = %s' % _xform(s), '',
                      '[node name="Page" type="SubViewport" parent="%s"]' % id,
                      'disable_3d = true', 'transparent_bg = true', 'gui_disable_input = true',
                      'size = Vector2i(%d, %d)' % (vw, vh), 'render_target_update_mode = 4', '',
                      '[node name="List" type="VBoxContainer" parent="%s/Page"]' % id,
                      'anchors_preset = 15', 'anchor_right = 1.0', 'anchor_bottom = 1.0',
                      'offset_left = 10.0', 'offset_top = 4.0', 'offset_right = -6.0', 'offset_bottom = -4.0',
                      'theme = SubResource("theme_%s")' % id, 'theme_override_constants/separation = 0', '',
                      '[node name="Title" type="Label" parent="%s/Page/List"]' % id,
                      'text = %s' % _str(d['title']), '']
            for i in range(ITEMS):
                item = d['items'][i] if i < len(d['items']) else {'text': '', 'done': False}
                p = '%s/Page/List/Item%d' % (id, i)
                box = int(fs * 0.85)
                nodes += ['[node name="Item%d" type="HBoxContainer" parent="%s/Page/List"]' % (i, id)]
                if i >= len(d['items']):
                    nodes.append('visible = false')
                nodes += ['theme_override_constants/separation = %d' % int(fs * 0.25), '',
                          '[node name="Box" type="TextureRect" parent="%s"]' % p,
                          'custom_minimum_size = Vector2(%d, %d)' % (box, box),
                          'size_flags_vertical = 4', 'texture = ExtResource("box")',
                          'expand_mode = 1', 'stretch_mode = 5', '',
                          '[node name="Tick" type="TextureRect" parent="%s/Box"]' % p]
                if not item['done']:
                    nodes.append('visible = false')
                nodes += ['anchors_preset = 15', 'anchor_right = 1.0', 'anchor_bottom = 1.0',
                          'offset_left = 2.0', 'offset_top = -6.0', 'offset_right = 8.0', 'offset_bottom = 0.0',
                          'pivot_offset = Vector2(%g, %g)' % ((box + 6) / 2, (box + 6) / 2),  # centre: gameplay pops it on tick
                          'texture = ExtResource("tick")', 'expand_mode = 1', 'stretch_mode = 5', '',
                          '[node name="Text" type="RichTextLabel" parent="%s"]' % p,
                          'size_flags_horizontal = 3', 'bbcode_enabled = true', 'fit_content = true',
                          'scroll_active = false', 'autowrap_mode = 3',
                          'text = %s' % _str(item['text']), '']
            nodes += ['[node name="Ink" type="MeshInstance3D" parent="%s"]' % id,
                      'cast_shadow = 0', 'mesh = SubResource("quad_%s")' % id,
                      'material_override = SubResource("ink_%s")' % id, '']
    os.makedirs(ROOT + '/cockpit/art/notes', exist_ok=True)
    with open(ROOT + '/cockpit/art/notes/cockpit_notes.tscn', 'w') as f:
        f.write('\n'.join(head + subs + nodes))
    with open(ROOT + '/cockpit/art/notes/notes_text.json', 'w') as f:
        json.dump({id: s['default'] for id, s in slots.items()}, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    with open(ROOT + '/cockpit/art/layout.json') as f:
        write(json.load(f)['notes'])
