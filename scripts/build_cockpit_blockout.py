"""Composition pass only. Run through the owned Blender MCP; no gameplay edits."""
import bpy
import math
from mathutils import Vector
ROOT = '/Users/nataliiamykytenko/Documents/Projects/gamedev/brain-control-assets'
assert bpy.context.scene.get('brain_control_assets_root') == ROOT
assert bpy.data.filepath.startswith(ROOT + '/source/')
COLORS = {'cream':'F1E4CF','sage':'BAC6B2','teal':'2D5C5B','peach':'EAA78B','honey':'D9A04C','clay':'C98778','porcelain':'F8F4EA','graphite':'454C48'}
collection_name = 'WC_Cockpit_Blockout'
old = bpy.data.collections.get(collection_name)
if old:
    for o in list(old.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(old)
coll = bpy.data.collections.new(collection_name)
bpy.context.scene.collection.children.link(coll)

def g(v): return (v[0], -v[2], v[1])
def linear(v): return v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4
mats = {}
for key, hexcode in COLORS.items():
    mat = bpy.data.materials.get('WC1_Blockout_'+key) or bpy.data.materials.new('WC1_Blockout_'+key)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    rgb = tuple(linear(int(hexcode[i:i+2],16)/255) for i in (0,2,4))
    bsdf.inputs['Base Color'].default_value = (*rgb,1)
    bsdf.inputs['Roughness'].default_value = .62
    bsdf.inputs['Metallic'].default_value = 0
    mat.diffuse_color = (*rgb,1)
    mat.use_backface_culling = True
    mat['style_id']='warm_ceramic_v1'; mat['palette_id']=key
    mats[key]=mat

def relocate(o, name, parent=None):
    o.name = name
    for c in list(o.users_collection): c.objects.unlink(o)
    coll.objects.link(o)
    o.parent = parent
    return o

def empty(name, pos=(0,0,0), parent=None, pitch=0, yaw=0):
    o = bpy.data.objects.new(name,None);coll.objects.link(o);o.parent=parent;o.location=g(pos)
    o.rotation_euler=(math.radians(pitch),0,math.radians(yaw))
    return o
root=empty('CockpitBlockout')
root['stage']='composition review; not integration-ready'
shell=empty('Shell',parent=root)
console=empty('ConsoleHousing',(0,.95,.1),root,pitch=18)
screens=empty('ScreenHousings',parent=root)
gauges=empty('GaugeHousing',(0,.955,-.59),root)
dress=empty('Dressing',parent=root)

def box(name,pos,size,color,parent=root,bevel=.008):
    bpy.ops.mesh.primitive_cube_add(size=1,location=g(pos))
    o=relocate(bpy.context.object,name,parent)
    o.scale=(size[0],size[2],size[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mats[color])
    if bevel:
        mod=o.modifiers.new('Selective bevel','BEVEL');mod.width=min(bevel,min(size)*.25);mod.segments=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in o.data.polygons:p.use_smooth=False
    return o

def sphere(name,pos,size,color,parent=root):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,location=g(pos))
    o=relocate(bpy.context.object,name,parent);o.scale=(size[0]/2,size[2]/2,size[1]/2)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mats[color])
    for p in o.data.polygons:p.use_smooth=True
    return o

def tube(name,points,radius,color,parent=root):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.resolution_u=5;data.bevel_depth=radius;data.bevel_resolution=1
    spl=data.splines.new('BEZIER');spl.bezier_points.add(len(points)-1)
    for p,xyz in zip(spl.bezier_points,points):
        p.co=g(xyz);p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,data);coll.objects.link(o);o.parent=parent;data.materials.append(mats[color])
    return o

# Large masses follow the current game dimensions; broad brain folds frame the view.
box('Desk',(0,.86,.12),(1.5,.06,.55),'sage',shell,.018)
box('LeftClutterLedge',(-.95,.86,.035),(.40,.06,.58),'sage',shell,.018)
box('RightClutterLedge',(.95,.86,.035),(.40,.06,.58),'sage',shell,.018)
box('DeskFront',(0,.43,.38),(1.5,.8,.06),'teal',shell,.018)
box('BrainBacking',(0,1.25,-.85),(3.0,2.7,.15),'clay',shell,.07)
box('BrainLeft',(-1.25,1.3,0),(.18,2.6,2.0),'clay',shell,.05)
box('BrainRight',(1.25,1.3,0),(.18,2.6,2.0),'clay',shell,.05)
box('BrainCeiling',(0,2.25,-.1),(2.5,.18,1.8),'clay',shell,.05)
for side in [-1,1]:
    for i in range(4):
        y=.62+i*.39
        tube('BrainFold_%s_%s'%(side,i),[(side*1.18,y-.13,-.72),(side*1.03,y,-.72),(side*1.17,y+.16,-.72),(side*1.37,y+.20,-.72),(side*1.44,y+.02,-.72)],.075,'peach',shell)
    for i in range(3):
        x=side*(.22+i*.37)
        tube('BrainCrown_%s_%s'%(side,i),[(x-.12,2.0,-.73),(x-.16,2.15,-.73),(x,2.25,-.73),(x+.12,2.09,-.73),(x+.08,1.98,-.73)],.073,'peach',shell)
box('ConsoleSlab',(0,-.03,.02),(1.05,.06,.42),'cream',console,.016)
box('LeftControlPlate',(-.27,.004,0),(.37,.014,.2),'teal',console)
slot_rim=empty('RightSlotRim',(.3,0,0),console)
box('SlotLeft',(-.14,.004,0),(.022,.012,.25),'teal',slot_rim)
box('SlotRight',(.14,.004,0),(.022,.012,.25),'teal',slot_rim)
box('SlotFront',(0,.004,.114),(.26,.012,.022),'teal',slot_rim)
box('SlotBack',(0,.004,-.114),(.26,.012,.022),'teal',slot_rim)
# The central slot aperture is not filled by art; actual modules are preview-only.

def housing(name,pos,size,yaw=0):
    group=empty(name,pos,screens,yaw=yaw);w,h=size
    box(name+'_Top',(0,h/2+.024,-.015),(w+.10,.048,.07),'teal',group,.012)
    box(name+'_Bottom',(0,-h/2-.024,-.015),(w+.10,.048,.07),'teal',group,.012)
    box(name+'_Left',(-w/2-.024,0,-.015),(.048,h,.07),'teal',group,.012)
    box(name+'_Right',(w/2+.024,0,-.015),(.048,h,.07),'teal',group,.012)
    box(name+'_Back',(0,0,-.060),(w+.09,h+.09,.045),'graphite',group)
    return group
housing('FrontScreen',(0,1.43,-.58),(1.28,.72))
housing('LeftPanel',(-.8,1.3,-.38),(.34,.46),32)
housing('RightPanel',(.8,1.3,-.38),(.34,.46),-32)
box('GaugeRail',(0,0,-.022),(1.24,.21,.045),'teal',gauges,.012)
for i,name in enumerate(['Coordination','Confidence','Balance','Focus','Embarrassment']):
    x=(i-2)*.24
    # Ring oriented to face +Z in Godot. Faces/needles are preview-only.
    bpy.ops.mesh.primitive_torus_add(major_segments=24,minor_segments=6,location=g((x,0,.010)),major_radius=.079,minor_radius=.009)
    o=relocate(bpy.context.object,name+'_Bezel',gauges);o.rotation_euler.x=math.pi/2;o.data.materials.append(mats['graphite'])
    paper=box(name+'_Paper',(x,-.122,.018),(.224,.036,.003),'cream',gauges,.001)
    paper['label']=name
    for sign in [-1,1]:box(name+'_Tape_'+str(sign),(x+sign*.075,-.103,.021),(.022,.023,.002),'honey',gauges,.001)

# Broad cable routes; no cables cross screen apertures or control targets.
tube('LeftCable',[(-1.0,.75,-.31),(-1.03,1.05,-.35),(-1.08,1.45,-.43),(-.99,1.84,-.54),(-.64,1.91,-.63)],.018,'teal',dress)
tube('RightCable',[(1.04,.83,-.35),(1.08,1.21,-.38),(1.09,1.63,-.43),(.90,1.93,-.59),(.62,2.0,-.67)],.016,'honey',dress)
tube('DeskCable',[(-.93,.90,.20),(-.82,.92,-.03),(-.88,.95,-.31),(-.95,1.02,-.36)],.012,'graphite',dress)
# Paper/clutter silhouettes remain separate so composition can be adjusted.
box('TaskPaper',(-.74,1.0,-.12),(.22,.13,.004),'honey',dress,.002)
box('Notebook',(-.09,.900,.35),(.30,.018,.16),'clay',dress)
box('NotebookPages',(-.09,.911,.35),(.277,.006,.146),'cream',dress,.002)
for i in range(4):
    paper=box('LoosePaper_'+str(i),(-.75-i*.018,.901+i*.003,.28+i*.01),(.13,.002,.09),'cream',dress,.0004)
    paper.rotation_euler.z=math.radians(-12+i*9)
for name,pos,size,color in [('KeepSake',(1.0,.98,-.22),(.13,.17,.11),'sage'),('KeepSakeHead',(1.0,1.085,-.22),(.13,.13,.11),'teal')]:sphere(name,pos,size,color,dress)
for sign in [-1,1]:sphere('KeepsakeEye_'+str(sign),(1+sign*.029,1.10,-.162),(.018,.022,.014),'graphite',dress)
for name,pos in [('LeftNote',(-1.00,1.77,-.39)),('RightNote',(.97,1.75,-.4)),('TopNote',(-.38,1.93,-.54))]:
    note=box(name,pos,(.20,.13,.003),'cream',dress,.001)
    note.rotation_euler.y=math.radians(-5 if name=='RightNote' else 6)
    box(name+'_Tape',(pos[0],pos[1]+.07,pos[2]+.004),(.035,.035,.002),'honey',dress,.001)

# Adapt CC0 props: rescale and replace colours with our palette, no runtime textures.
def import_prop(name,pack,filename,pos,width=None,height=None,yaw=0):
    path=ROOT+'/source/vendor/kenney/selected/'+pack+'/'+filename
    before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=path)
    objects=[o for o in bpy.data.objects if o not in before]
    meshes=[o for o in objects if o.type=='MESH']
    verts=[o.matrix_world@Vector(v) for o in meshes for v in o.bound_box]
    lo=Vector(tuple(min(v[i] for v in verts) for i in range(3)));hi=Vector(tuple(max(v[i] for v in verts) for i in range(3)))
    factor=(height/(hi.z-lo.z)) if height else (width/(hi.x-lo.x))
    group=empty(name,pos,dress,yaw=yaw)
    for j,o in enumerate(meshes):
        world=o.matrix_world.copy();o.data=o.data.copy()
        for v in o.data.vertices:v.co=(world@v.co-Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z)))*factor
        original=list(o.data.materials);uv=o.data.uv_layers.active
        pixels={}
        for m in original:
            if m and m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type=='TEX_IMAGE' and n.image and n.image.size[0]:pixels[m.name]=(n.image.size[:],list(n.image.pixels))
        palette_keys=list(COLORS)
        palette_linear={key:tuple(linear(int(COLORS[key][i:i+2],16)/255) for i in (0,2,4)) for key in palette_keys}
        assigned=[]
        for poly in o.data.polygons:
            oldmat=original[poly.material_index]
            bsdf=next(n for n in oldmat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            rgb=tuple(bsdf.inputs['Base Color'].default_value[:3])
            if oldmat.name in pixels and uv:
                (w,h),pix=pixels[oldmat.name]
                u=sum(uv.data[k].uv.x for k in poly.loop_indices)/len(poly.loop_indices)
                v=sum(uv.data[k].uv.y for k in poly.loop_indices)/len(poly.loop_indices)
                ix=min(w-1,max(0,int(u*w)));iy=min(h-1,max(0,int(v*h)));off=(iy*w+ix)*4
                rgb=tuple(linear(c) for c in pix[off:off+3])
            distances=[sum((rgb[i]-palette_linear[k][i])**2 for i in range(3)) for k in palette_keys]
            key=palette_keys[distances.index(min(distances))]
            assigned.append(palette_keys.index(key))
        o.data.materials.clear()
        for key in palette_keys:o.data.materials.append(mats[key])
        for poly,index in zip(o.data.polygons,assigned):poly.material_index=index
        relocate(o,name+'Mesh'+str(j),group);o.location=(0,0,0);o.rotation_euler=(0,0,0);o.scale=(1,1,1)
        o['source_author']='Kenney';o['source_license']='CC0-1.0';o['source_file']=pack+'/'+filename
    for o in objects:
        if o not in meshes:bpy.data.objects.remove(o,do_unlink=True)
    return group
import_prop('Books','furniture-kit','books.glb',(-.98,.895,-.23),width=.23,yaw=-8)
import_prop('Mug','food-kit','mug.glb',(.86,.895,-.05),height=.105,yaw=-35)
import_prop('BrainFuel','food-kit','soda-can.glb',(-.82,.895,.13),height=.12,yaw=8)
import_prop('Donut','food-kit','donut-sprinkles.glb',(-.67,.897,.25),width=.11,yaw=15)

for o in bpy.context.scene.objects:
    if o not in list(coll.objects):o.hide_set(True);o.hide_render=True
for o in coll.objects:o.hide_set(False);o.hide_render=False
bpy.ops.object.select_all(action='DESELECT')
for o in coll.objects:o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.context.scene.name='CockpitComposition'
bpy.ops.export_scene.gltf(filepath=ROOT+'/cockpit/art/cockpit_blockout.glb',export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_cameras=False,export_lights=False)
# Owned preview camera, deliberately not in exported art.
camdata=bpy.data.cameras.new('CockpitCompositionCamera');cam=bpy.data.objects.new('CockpitCompositionCamera',camdata);coll.objects.link(cam)
cam.location=g((0,1.36,.8));forward=Vector(g((0,-math.sin(math.radians(14)),-math.cos(math.radians(14)))))
assert 'VERTICAL' in [i.identifier for i in camdata.bl_rna.properties['sensor_fit'].enum_items]
cam.rotation_euler=forward.to_track_quat('-Z','Y').to_euler();camdata.sensor_fit='VERTICAL';camdata.lens=camdata.sensor_height/(2*math.tan(math.radians(34)));camdata.clip_start=.01
bpy.context.scene.camera=cam;bpy.context.scene.render.resolution_x=1280;bpy.context.scene.render.resolution_y=720
bpy.context.scene.name='CockpitComposition';bpy.context.scene.unit_settings.scale_length=1
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/source/cockpit/cockpit_blockout_v1.blend')
triangles=0
for o in coll.objects:
    if o.type=='MESH':o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
print('COCKPIT_BLOCKOUT_BUILT meshes=',len([o for o in coll.objects if o.type=='MESH']),'mesh_triangles=',triangles,'curves=',len([o for o in coll.objects if o.type=='CURVE']))
