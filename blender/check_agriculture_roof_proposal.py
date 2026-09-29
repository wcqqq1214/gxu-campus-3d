"""Probe and render the isolated west-roof candidate without saving production assets."""
import argparse,json,sys,hashlib
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import material
from generic_buildings import ordinary_building
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--proposal',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--images',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);r=json.loads(a.proposal.read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
C={name:material(name,color) for name,color in {'white':(.86,.85,.80),'stone':(.64,.60,.49),'pink':(.77,.68,.66),'paleRoof':(.48,.49,.46),'dark':(.075,.09,.10),'glass':(.12,.24,.29),'shadeGlass':(.085,.15,.19),'blueRoof':(.06,.33,.56),'red':(.48,.12,.08)}.items()}
checks=[]
# Independent coordinates inside each retained/changed region. Source ground
# is normalized to zero for this isolated comparison, not a terrain check.
probes=[('front-terrace',255.76,-350.94,9.9),('west-rear',252.67,-337.24,13.2),('west-north',244.5,-306.8,13.2),('main',280,-342,16.5),('east',349,-304,16.5),('central-rear',299,-316,16.5)]
for detail in [False,True]:
 meshes={k:ordinary_building(r[k],0,C,detail) for k in ['original','candidate']}
 trees={k:BVHTree.FromPolygons(m.v,m.f) for k,m in meshes.items()}
 for name,x,y,z in probes:
  origin=Vector((x,y,24));direction=Vector((0,0,-1));new=trees['candidate'].ray_cast(origin,direction,30);old=trees['original'].ray_cast(origin,direction,30)
  assert new[0] is not None and abs(new[0].z-z)<.001,(detail,name,new,z)
  assert old[0] is not None and abs(old[0].z-16.5)<.001,(detail,name,old)
  checks.append(dict(detail=detail,region=name,expected=z,candidate=new[0].z,original=old[0].z,oldFailsNewHeight=z!=16.5))
 # Two finite vertical rays check for retained upper surfaces at these sample
 # coordinates only; they do not prove that an entire volume is empty.
 for x,y,z in [(255.76,-350.94,11),(252.67,-337.24,15)]:
  length=24-z
  assert trees['candidate'].ray_cast(Vector((x,y,z)),Vector((0,0,1)),length)[0] is None
  assert trees['original'].ray_cast(Vector((x,y,z)),Vector((0,0,1)),length)[0] is not None
  checks.append(dict(detail=detail,upperSurfaceRayOrigin=[x,y,z],direction=[0,0,1],length=length,candidateClear=True,originalBlocked=True))
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('roof-proposal-world');scene.world.color=(.16,.19,.20);scene.view_settings.view_transform='Standard';scene.render.resolution_x=1400;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
cam=bpy.data.cameras.new('inspection');camera=bpy.data.objects.new('inspection',cam);scene.collection.objects.link(camera);scene.camera=camera;cam.type='ORTHO'
views=[('southwest',(195,-425,80),(300,-326,8),170),('south',(310,-460,50),(300,-326,8),155),('roof',(300,-326,180),(300,-325,0),165)]
a.images.mkdir(parents=True,exist_ok=True);images=[]
for variant in ['original','candidate']:
 mesh=ordinary_building(r[variant],0,C,True);obj=mesh.object(variant,scene.collection)
 for name,position,target,scale in views:
  camera.location=position;camera.rotation_euler=(Vector(target)-Vector(position)).to_track_quat('-Z','Y').to_euler();cam.ortho_scale=scale
  image=a.images/f'{variant}-{name}.png';scene.render.filepath=str(image.resolve());bpy.ops.render.render(write_still=True);images.append(str(image))
 bpy.data.objects.remove(obj,do_unlink=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for path,digest in r['productionFingerprints'].items():assert sha(ROOT/path)==digest,path
report=dict(passed=True,scope='Generated candidate geometry only, not real-world correctness, terrain, shipping GLB or production acceptance.',productionReady=False,checks=checks,images=images,proposalSha256=sha(a.proposal),productionUnchanged=True)
a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'checks':len(checks),'images':len(images)}))
