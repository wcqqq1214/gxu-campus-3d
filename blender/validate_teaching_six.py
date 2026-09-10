"""Ray-test real source/base/near geometry: four entrances and three courts stay open."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
l=next(l for l in json.loads((ROOT/'public/data/landmarks.json').read_text()) if l['id']=='teaching-six')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['landmark']==l['id']);e=b['architecture'];ca,sa=math.cos(e['angle']),math.sin(e['angle']);ox,oy=e['origin'];z=l['elevation']
def point(x,y,h):return Vector((ox+x*ca-y*sa,oy+x*sa+y*ca,z+h))
terrain=json.loads((ROOT/'public/data/terrain.json').read_text())
def terrain_height(p):
    cols,rows=terrain['cols'],terrain['rows'];x0,y0,x1,y1=terrain['bounds'];hh=terrain['heights']
    u=(p.x-x0)/(x1-x0)*(cols-1);v=(p.y-y0)/(y1-y0)*(rows-1);i,j=int(u),int(v);a,t=u-i,v-j
    return (hh[j*cols+i]*(1-a)+hh[j*cols+i+1]*a)*(1-t)+(hh[(j+1)*cols+i]*(1-a)+hh[(j+1)*cols+i+1]*a)*t
def check(objects,label):
    vs=[];fs=[]
    for o in objects:
        if o.type!='MESH':continue
        off=len(vs);vs.extend([tuple(o.matrix_world@v.co) for v in o.data.vertices]);fs.extend([tuple(off+i for i in p.vertices) for p in o.data.polygons])
    bv=BVHTree.FromPolygons(vs,fs);paths=[('south-north',(0,-36),(0,36)),('west',(-63,0),(-35,0)),('east',(63,0),(35,0))];rays=0
    for name,a,c in paths:
        for offset in [-2,0,2]:
            for h in [1.8,3.4]:
                dx,dy=(offset,0) if name=='south-north' else (0,offset)
                a1=point(a[0]+dx,a[1]+dy,h);c1=point(c[0]+dx,c[1]+dy,h)
                for start,end in [(a1,c1),(c1,a1)]:
                    d=end-start;hit=bv.ray_cast(start,d.normalized(),d.length)
                    assert hit[0] is None,(label,name,'blocked entrance',offset,h,tuple(hit[0]) if hit[0] else None);rays+=1
    for x,y in [(-34,0),(0,0),(35,0)]:
        hit=bv.ray_cast(point(x,y,40),Vector((0,0,-1)),38)
        assert hit[0] is None,(label,'courtyard roof sealed',x,y)
    floors=[]
    for x,y in [(0,-32),(0,32),(-59,0),(59,0)]:
        hit=bv.ray_cast(point(x,y,2),Vector((0,0,-1)),2.2)
        assert hit[0] is not None and .1<hit[0].z-z<.9,(label,'missing entrance stair',x,y)
        floors.append(round(hit[0].z-z,3))
    margins=[]
    for ent in e['entrances']:
        theta=ent['angle'];ex,ey=ent['center']
        for xx in [-ent['width']/2+.3,0,ent['width']/2-.3]:
            for yy in [-3.8,-2.8,-2.1,-1.4,-.5]:
                p=point(ex+xx*math.cos(theta)-yy*math.sin(theta),ey+xx*math.sin(theta)+yy*math.cos(theta),2)
                hit=bv.ray_cast(p,Vector((0,0,-1)),3)
                assert hit[0] is not None,(label,'missing tread')
                margin=hit[0].z-terrain_height(p)
                assert margin>.035,(label,'terrain covers entrance stair',ent['id'],xx,yy,margin)
                margins.append(margin)
    ceilings=[]
    for x,y in [(0,-20),(0,20),(-47,0),(47,0)]:
        hit=bv.ray_cast(point(x,y,1.8),Vector((0,0,1)),6)
        assert hit[0] is not None and 5.1<hit[0].z-z<5.3,(label,'missing passage ceiling',x,y)
        ceilings.append(round(hit[0].z-z,3))
    return dict(representation=label,faces=len(fs),unblockedPassageRays=rays,openCourtyards=3,entranceStairHeights=floors,passageCeilingHeights=ceilings,terrainStairSamples=len(margins),minimumTreadAboveDEM=round(min(margins),4))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
objects=[o for o in bpy.context.scene.objects if o.get('landmark')==l['id']]
assert len(objects)==1
results=[check(objects,'editable source')]
for name in ['base','teaching-six']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/f'public/models/{name}.glb'))
    objects=[]
    for o in bpy.context.scene.objects:
        root=o
        while root.parent:root=root.parent
        if o.get('landmark')==l['id'] or root.get('landmark')==l['id']:objects.append(o)
    results.append(check(objects,name+'.glb'))
p=ROOT/'docs/model-checks/teaching-six-geometry.json';p.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print(json.dumps(results),flush=True)
