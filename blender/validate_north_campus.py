"""Check delivered source and both generated LODs for actual open passages."""
import json,sys,math
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from geometry import MATERIALS
from north_campus_architecture import building_model,Frame

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
MATERIALS[:]=list(bpy.data.materials)
colors={m.name:i for i,m in enumerate(MATERIALS)}
records=[b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b.get('customModel')=='north-campus']
report=[]
def object_tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                               [tuple(p.vertices) for p in obj.data.polygons])

def check_passages(b,trees):
    f=Frame(b)
    if f.form.get('portalWidth') or f.form['kind']=='gallery':
        u=f.w*.22 if f.form['kind']=='gallery' else 0
        # Gallery ends abut neighboring teaching wings; test the undercroft
        # within its own footprint rather than those neighboring walls.
        inset=.5 if f.form['kind']=='gallery' else -1
        origin=Vector(f.point(u,f.v0+inset,2));end=Vector(f.point(u,f.v1-inset,2))
        for tree in trees:
            hit=tree.ray_cast(origin,(end-origin).normalized(),(end-origin).length)
            assert hit[0] is None,(b['id'],'sealed delivered passage',hit[0])
    if f.form['kind']=='library':
        # Below the portico ceiling: the landing must reach the doorway.
        for v in (f.v0+.3,f.v0+2.5,f.v0+4.6):
            origin=Vector(f.point(0,v,8))
            hits=[tree.ray_cast(origin,Vector((0,0,-1)),8)[0] for tree in trees]
            hits=[h for h in hits if h is not None]
            assert hits and abs(max(h.z for h in hits)-(f.z+4))<.06,(b['id'],'landing gap',v)
    if f.form['kind']=='gym':
        for fraction in (.2,.4,.5,.6,.8):
            u=f.u0+f.w*fraction
            expected=f.z+f.form['bodyHeight']+(b['height']-f.form['bodyHeight'])*(1-(2*fraction-1)**2)
            origin=Vector(f.point(u,(f.v0+f.v1)/2,35))
            hits=[tree.ray_cast(origin,Vector((0,0,-1)),35)[0] for tree in trees]
            hits=[h for h in hits if h is not None]
            assert hits and abs(max(h.z for h in hits)-expected)<.16,(b['id'],'roof profile',fraction)

for b in records:
    source=[o for o in bpy.context.scene.objects if o.get('featureId')==b['id']]
    assert len(source)==1,(b['id'],len(source))
    assert len(source[0].vertex_groups)>=4,b['id']
    check_passages(b,[object_tree(source[0])])
    f=Frame(b);ranges=[]
    for detail in (False,True):
        mesh=building_model(b,colors,detail)
        assert all(math.isfinite(x) for v in mesh.v for x in v)
        ranges.append([[min(v[i] for v in mesh.v),max(v[i] for v in mesh.v)] for i in range(3)])
        tree=BVHTree.FromPolygons(mesh.v,mesh.f)
        if f.form.get('portalWidth'):
            origin=Vector(f.point(0,f.v0-1,2.0));end=Vector(f.point(0,f.v1+1,2.0))
            hit=tree.ray_cast(origin,(end-origin).normalized(),(end-origin).length)
            assert hit[0] is None,(b['id'],'sealed portal',detail,hit[0])
        if f.form['kind']=='gallery':
            origin=Vector(f.point(f.w*.22,f.v0-1,2));end=Vector(f.point(f.w*.22,f.v1+1,2))
            assert tree.ray_cast(origin,(end-origin).normalized(),(end-origin).length)[0] is None,b['id']
    delta=max(abs(a-c) for pair,pair2 in zip(*ranges) for a,c in zip(pair,pair2))
    # Fine facade bars and a different glazing subdivision on skewed traced
    # edges may extend the mesh bounds; the structural envelope is shared.
    assert delta<.5,(b['id'],'LOD envelope changed',delta)
    report.append({'id':b['id'],'sourceObjects':len(source),'lodEnvelopeDeltaMeters':round(delta,4),
                   'openPassage':bool(f.form.get('portalWidth')),'openGallery':f.form['kind']=='gallery'})
assert {'roads','sports'}<={o.get('layer') for o in bpy.context.scene.objects if o.get('northCampus')}
delivered=[]
keys={b['chunk'] for b in records}
for filename in ['base.glb',*[key+'.glb' for key in sorted(keys)]]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models'/filename))
    bpy.context.view_layer.update()
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.split('.')[0] in keys]
    assert objects,filename
    trees=[object_tree(o) for o in objects]
    members=[b for b in records if filename=='base.glb' or b['chunk']+'.glb'==filename]
    for b in members:check_passages(b,trees)
    delivered.append({'file':filename,'checkedBuildings':len(members),'passed':True})
result={'passed':True,'buildings':report,'deliveredAssets':delivered,'scope':'Editable source and decoded delivered GLBs: through-passages, library landing continuity and gym roof profile. Generated LOD envelopes also checked. Photographic likeness is reviewed separately.'}
(ROOT/'docs/model-checks/north-campus-refinement-geometry.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False),flush=True)
