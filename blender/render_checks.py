"""Render two honest source-model inspection angles for each independent landmark."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
out=ROOT/'docs/model-checks';out.mkdir(exist_ok=True)
objects={o.get('landmark'):o for o in scene.objects if o.get('landmark')}
requested=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if requested:objects={key:o for key,o in objects.items() if key in requested}
for o in scene.objects:
    if o.type=='MESH':o.hide_render=True
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
    o.hide_render=True
print('Saved',len(objects)*2,'model inspection views',flush=True)
