"""Isolated before/candidate comparison; never writes the campus source file."""
import argparse,json,sys,math
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import material
from generic_buildings import ordinary_building
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--proposal',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--eye-level',action='store_true',help='Add a provisional perspective view; not a fitted photo camera')
parser.add_argument('--camera-report',type=Path,help='Add the bounded-fit camera and verify its pixel projection')
a=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);a.output.mkdir(parents=True,exist_ok=True)
r=json.loads(a.proposal.read_text());bpy.ops.wm.read_factory_settings(use_empty=True)
C={name:material(name,color) for name,color in {'white':(.86,.85,.80),'stone':(.64,.60,.49),'pink':(.77,.68,.66),'paleRoof':(.48,.49,.46),'dark':(.075,.09,.10),'glass':(.12,.24,.29),'shadeGlass':(.085,.15,.19),'blueRoof':(.06,.33,.56),'red':(.48,.12,.08)}.items()}
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD'
scene.world=bpy.data.worlds.new('proposal-background');scene.world.color=(.16,.19,.20)
scene.view_settings.view_transform='Standard';scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
camdata=bpy.data.cameras.new('inspection-camera');camera=bpy.data.objects.new('inspection-camera',camdata);scene.collection.objects.link(camera);scene.camera=camera
entry=next(e for e in r['original']['form']['entrances'] if e.get('porticoId')=='link-portico');front=entry['outerCenter'];bearing=math.radians(entry['bearing']);n=(math.sin(bearing),math.cos(bearing));t=(n[1],-n[0])
def loc(out,along,z):return Vector((front[0]+n[0]*out+t[0]*along,front[1]+n[1]*out+t[1]*along,z))
views=[('entry',loc(23,0,4),loc(-3.6,0,4),29),('oblique',loc(23,-17,17),loc(-2,0,5),38),('roof',loc(2,0,48),loc(-2,0,0),40)]
if a.eye_level:views.append(('eye',loc(8.7,0,2.75),loc(-6,0,6.3),29))
if a.camera_report:views.append(('photo',loc(0,0,0),loc(-1,0,0),29))
projection_checks=[]
for variant in ('original','candidate'):
    mesh=ordinary_building(r[variant],0,C,True);obj=mesh.object(variant,scene.collection)
    for name,position,target,scale in views:
        camdata.type='ORTHO';camdata.ortho_scale=scale;camera.location=position
        camdata.shift_x=0;camdata.shift_y=0
        scene.render.resolution_x=1200;scene.render.resolution_y=800
        if name=='eye':
            camdata.type='PERSP';camdata.sensor_width=36;camdata.lens=22.5
        camera.rotation_euler=(target-position).to_track_quat('-Z','Y').to_euler()
        if name=='photo':
            from bpy_extras.object_utils import world_to_camera_view
            fitted=json.loads(a.camera_report.read_text())['roundedCandidate'];c=fitted['camera']
            width,height=c['imageSize'];scene.render.resolution_x=width;scene.render.resolution_y=height
            camdata.type='PERSP';camdata.sensor_fit='HORIZONTAL';camdata.sensor_width=36
            camdata.lens=c['focalPixels']*36/width
            camdata.shift_x=(width/2-c['principalPoint'][0])/width
            camdata.shift_y=(c['principalPoint'][1]-height/2)/width
            yaw,pitch,roll=c['yaw'],c['pitch'],c['roll']
            forward=Vector((math.sin(yaw)*math.cos(pitch),math.cos(yaw)*math.cos(pitch),math.sin(pitch)))
            right=Vector((math.cos(yaw),-math.sin(yaw),0));up=right.cross(forward)
            rr=right*math.cos(roll)+up*math.sin(roll);uu=up*math.cos(roll)-right*math.sin(roll)
            def direction(v):return Vector((-t[0]*v.x-n[0]*v.y,-t[1]*v.x-n[1]*v.y,v.z))
            camera.location=loc(c['outwardDistance'],-c['rightOffset'],c['height'])
            axes=[direction(rr),direction(uu),-direction(forward)]
            camera.rotation_euler=Matrix(tuple(tuple(v[k] for v in axes) for k in range(3))).to_euler()
            bpy.context.view_layer.update()
            for point,pixel in zip([(-2.425,5.85,7.45),(2.425,5.85,7.45),(2.425,5.85,4.25),(-2.425,5.85,4.25)],fitted['predictions'][:4]):
                screen=world_to_camera_view(scene,camera,loc(-point[1],-point[0],point[2]))
                actual=[screen.x*width,(1-screen.y)*height]
                error=math.dist(actual,pixel)
                assert error<.05,(variant,actual,pixel,error)
                projection_checks.append(dict(variant=variant,expected=pixel,actual=actual,errorPixels=error))
        scene.render.filepath=str(a.output/f'{variant}-{name}.png');bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj,do_unlink=True)
if projection_checks:(a.output/'camera-projection.json').write_text(json.dumps(projection_checks,indent=2)+'\n')
print(f'Rendered {2*len(views)} isolated comparison images; no production source or GLB saved')
