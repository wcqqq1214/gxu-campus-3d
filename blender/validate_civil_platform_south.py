"""Fixed-coordinate checks and views for the south/west platform candidate."""
import argparse
import json
import re
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from geometry import material, Mesh
from generic_buildings import ordinary_building

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--proposal',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--assets',type=Path,help='Check the saved candidate source, base and near under a repository-shaped root; skip rendering')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.output.mkdir(parents=True,exist_ok=True)
r=json.loads(a.proposal.read_text());bpy.ops.wm.read_factory_settings(use_empty=True)
C={name:material(name,color) for name,color in {'white':(.86,.85,.80),'stone':(.64,.60,.49),'pink':(.77,.68,.66),'paleRoof':(.48,.49,.46),'dark':(.075,.09,.10),'glass':(.12,.24,.29),'shadeGlass':(.085,.15,.19),'blueRoof':(.06,.33,.56),'red':(.48,.12,.08)}.items()}
names={v:k for k,v in C.items()};results=[]
def asset_cases():
    def root_name(o):
        while o.parent:o=o.parent
        return re.sub(r'\.\d{3,}$','',o.name)
    for label,filename in [('source','blender/gxu-campus.blend'),('base','public/models/base.glb'),('near','public/models/chunk-n2-n3.glb')]:
        if label=='source':bpy.ops.wm.open_mainfile(filepath=str(a.assets/filename))
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(a.assets/filename))
        bpy.context.view_layer.update();m=Mesh()
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and
                 (o.get('featureId')=='way/957404988' if label=='source' else root_name(o)=='chunk-n2-n3')]
        assert objects,label
        for o in objects:
            for face in o.data.polygons:
                mat=o.data.materials[face.material_index].name.split('.')[0]
                points=[o.matrix_world@o.data.vertices[i].co for i in face.vertices]
                m.face([(p.x,p.y,p.z-r['original']['elevation']) for p in points],C.get(mat,-1))
        yield label,label!='base',m

cases=asset_cases() if a.assets else [(detail,detail,ordinary_building(r['candidate'],0,C,detail)) for detail in (False,True)]
for label,detail,candidate_mesh in cases:
    tolerance=(.04 if label=='base' else .02) if a.assets else 0
    meshes=[ordinary_building(r['original'],0,C,detail),candidate_mesh]
    trees=[BVHTree.FromPolygons(m.v,m.f) for m in meshes]
    def hit(which,x,y,z,dx,dy):
        h=trees[which].ray_cast(Vector((x,y,z)),Vector((dx,dy,0)),3)
        return None if h[0] is None else (names[meshes[which].m[h[2]]],tuple(h[0]),tuple(h[1]))
    cells=[]
    for left,right,count in [(-734.5689996267181,-720.2684733304854,8),
                             (-720.2684733304854,-701.2909494339341,11),
                             (-701.2909494339341,-695.2908592664412,3)]:
        for row in range(5):
            for col in range(count):
                x=left+.62+(right-left-1.24)*(col+.5)/count
                z=15.125+3.3*row
                h=hit(1,x,-731,z,0,1)
                assert h and h[0]=='glass' and h[2][1]<-.99,(detail,x,z,h)
                cells.append(dict(x=x,z=z,material=h[0]))
    negative=hit(0,-710,-731,18.425,0,1)
    assert negative and negative[0]!='glass',negative
    retained=[]
    for x in [-732.1856+.3,-727.4187+.3,-722.6519+.3,-698.2909+.3]:
        # Level 2 crosses the retained coplanar stone portico fascia at z=8.448;
        # use unobstructed wall/window levels, not a BVH tie at the roof edge.
        for level in (0,1,3):
            z=(level+.56)*3.3
            before,after=(hit(i,x,-731,z,0,1) for i in (0,1))
            assert before[0]==after[0] and (Vector(before[1])-Vector(after[1])).length<=max(tolerance,1e-6),(label,x,z,before,after)
            assert Vector(before[2]).dot(Vector(after[2]))>.99,(label,before,after)
            retained.append(dict(x=x,z=z,material=before[0] if before else None))
    west=[]
    for level in range(9):
        for y in (-726.4378,-721.1538,-715.8698):
            z=(level+.56)*3.3
            before,after=(hit(i,-736,y,z,1,0) for i in (0,1))
            assert before and before[0] in ('glass','shadeGlass'),before
            if level>=5:assert after and after[0]=='white' and after[2][0]<-.99,after
            else:assert before[0]==after[0] and (Vector(before[1])-Vector(after[1])).length<=max(tolerance,1e-6),(before,after)
            west.append(dict(level=level,y=y,z=z,material=after[0]))
    results.append(dict(detail=label,southCells=cells,retainedLower=retained,westCells=west,originalFailsNewSouthProbe=True))

if a.assets:
    (a.output/'asset-geometry.json').write_text(json.dumps(dict(passed=True,assets=str(a.assets),checks=results),indent=2)+'\n')
    print('Saved source/base/near south-west facade checks passed.');sys.exit(0)

scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD'
scene.world=bpy.data.worlds.new('candidate-background');scene.world.color=(.16,.19,.20)
scene.view_settings.view_transform='Standard';scene.render.resolution_x=1100;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
camdata=bpy.data.cameras.new('inspection-camera');camera=bpy.data.objects.new('inspection-camera',camdata);scene.collection.objects.link(camera);scene.camera=camera
views=[('south',(-715,-825,24),(-715,-725,19),52),('southwest',(-790,-790,59),(-700,-751,13),113)]
for variant in ('original','candidate'):
    obj=ordinary_building(r[variant],0,C,True).object(variant,scene.collection)
    for name,position,target,scale in views:
        camera.location=Vector(position);camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
        camdata.type='ORTHO';camdata.ortho_scale=scale
        scene.render.filepath=str(a.output/f'{variant}-{name}.png');bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj,do_unlink=True)
(a.output/'geometry.json').write_text(json.dumps(dict(passed=True,candidateOnly=True,checks=results),indent=2)+'\n')
print('South 220, retained lower 24, west 54 probes passed in two detail modes; four views rendered.')
