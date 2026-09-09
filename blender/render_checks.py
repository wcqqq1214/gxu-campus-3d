"""Render two honest source-model inspection angles for each independent landmark."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
requested=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if requested:
    # Append only requested source objects, avoiding full-campus dependency
    # evaluation (especially thousands of linked tree instances) for each view.
    names={l['name'] for l in json.loads((ROOT/'public/data/landmarks.json').read_text()) if l['id'] in requested}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(ROOT/'blender/gxu-campus.blend'),link=False) as (src,dst):
        dst.objects=[n for n in src.objects if n in names or n in ('下午日光','校园鸟瞰')]
        dst.worlds=['南宁晴空']
    for o in dst.objects:bpy.context.scene.collection.objects.link(o)
    bpy.context.scene.camera=next(o for o in dst.objects if o.type=='CAMERA')
    bpy.context.scene.world=dst.worlds[0]
else:bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
if requested and set(requested)<= {'new-east-gate','east-gate','west-gate'}:
    # Material-colour studio inspection; final PBR appearance is checked in Three.js.
    scene.render.engine='BLENDER_WORKBENCH'
    scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
    scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD'
    scene.world.color=(.22,.26,.24)
out=ROOT/'docs/model-checks';out.mkdir(exist_ok=True)
objects={o.get('landmark'):o for o in scene.objects if o.get('landmark')}
if requested:objects={key:o for key,o in objects.items() if key in requested}
for o in scene.objects:
    if o.type=='MESH':o.hide_render=True
# Inspection is isolated to the requested landmarks. Remove unrelated meshes
# from this unsaved preview scene to avoid evaluating the entire campus per view.
for o in list(scene.objects):
    if o.type=='MESH' and o not in objects.values():bpy.data.objects.remove(o,do_unlink=True)
world=scene.world;world.node_tree.nodes['Background'].inputs[0].default_value=(.7,.75,.7,1);world.node_tree.nodes['Background'].inputs[1].default_value=.8
camera=scene.camera;camera.data.type='ORTHO';scene.view_settings.view_transform='AgX'
for key,o in objects.items():
    o.hide_render=False;points=[o.matrix_world@Vector(c) for c in o.bound_box];center=sum(points,Vector())/8
    w=max(p.x for p in points)-min(p.x for p in points);d=max(p.y for p in points)-min(p.y for p in points);h=max(p.z for p in points)-min(p.z for p in points);scale=max(w,d,h)*1.45
    camera.data.ortho_scale=scale
    offsets=[(-.9,-1.5,.85),(1.35,.95,.95)]
    if key=='huixue':offsets=[(1.5,-.9,.85),(-.95,1.35,.95)]
    if key=='south-gate':
        offsets=[(-.15,-1.8,.36),(1.1,.95,.60)]
        scene.render.resolution_x=1440;scene.render.resolution_y=900;scene.cycles.samples=24
        camera.data.ortho_scale=scale*.78
    elif key in ('east-gate','west-gate','new-east-gate'):
        bearing={'east-gate':90,'west-gate':270,'new-east-gate':180}[key]
        angle=math.radians(180-bearing)
        offsets=[(a*math.cos(angle)-b*math.sin(angle),a*math.sin(angle)+b*math.cos(angle),c)
                 for a,b,c in [(-.14,-1.7,.42),(1.0,.9,.70)]]
        scene.render.resolution_x=1440;scene.render.resolution_y=900;scene.cycles.samples=16
        camera.data.ortho_scale=scale*.82
    elif key in ('library','international-residence'):
        scene.render.resolution_x=1440;scene.render.resolution_y=1000;scene.cycles.samples=16
    else:scene.render.resolution_x=720;scene.render.resolution_y=540;scene.cycles.samples=8
    for index,offset in enumerate([Vector(v) for v in offsets]):
        camera.location=center+offset*scale;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        if key in ('library','international-residence'):
            inv=camera.rotation_euler.to_matrix().transposed();projected=[inv@(p-center) for p in points]
            width=max(p.x for p in projected)-min(p.x for p in projected);height=max(p.y for p in projected)-min(p.y for p in projected)
            camera.data.ortho_scale=max(width,height*scene.render.resolution_x/scene.render.resolution_y)*1.10
        scene.render.filepath=str(out/f'{key}-{index+1}.png');bpy.ops.render.render(write_still=True)
    if key=='library':
        b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['landmark']==key)
        e=b['architecture'];a=e['angle'];ox,oy=e['origin']
        def local(x,y,z):return Vector((ox+x*math.cos(a)-y*math.sin(a),oy+x*math.sin(a)+y*math.cos(a),b['elevation']+z))
        target=local(-.55,31.8,7);camera.location=local(-22,75,19)
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=37
        scene.render.filepath=str(out/'library-north-entry.png');bpy.ops.render.render(write_still=True)
    o.hide_render=True
print('Saved',len(objects)*2,'model inspection views',flush=True)
