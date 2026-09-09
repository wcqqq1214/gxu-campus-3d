"""Render two honest source-model inspection angles for each independent landmark."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
out=ROOT/'docs/model-checks';out.mkdir(exist_ok=True)
objects={o.get('landmark'):o for o in scene.objects if o.get('landmark')}
for o in scene.objects:
    if o.type=='MESH':o.hide_render=True
world=scene.world;world.node_tree.nodes['Background'].inputs[0].default_value=(.7,.75,.7,1);world.node_tree.nodes['Background'].inputs[1].default_value=.8
camera=scene.camera;camera.data.type='ORTHO';scene.view_settings.view_transform='AgX'
for key,o in objects.items():
    o.hide_render=False;points=[o.matrix_world@Vector(c) for c in o.bound_box];center=sum(points,Vector())/8
    w=max(p.x for p in points)-min(p.x for p in points);d=max(p.y for p in points)-min(p.y for p in points);h=max(p.z for p in points)-min(p.z for p in points);scale=max(w,d,h)*1.45
    camera.data.ortho_scale=scale
    for index,offset in enumerate([Vector((-.9,-1.5,.85)),Vector((1.35,.95,.95))]):
        camera.location=center+offset*scale;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(out/f'{key}-{index+1}.png');bpy.ops.render.render(write_still=True)
    o.hide_render=True
print('Saved',len(objects)*2,'model inspection views',flush=True)
