"""Verify ordinary form in both generators, saved source and decoded shipping GLBs.

--generated-only checks generators before rebuilding. The default also checks
real source vertex groups and ray samples in base and every near chunk.
"""
import bpy
import json
import math
import sys
import re
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'blender'))
from generic_buildings import ordinary_building,compact_form_source
from geometry import MATERIALS


def ordinary(b):
    return (not b['landmark'] and not b.get('customModel') and b['id'] != 'way/948683815'
            and b['tags'].get('memorial') != 'column')


def mesh_tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                                [tuple(p.vertices) for p in obj.data.polygons])


def root_name(obj):
    while obj.parent:
        obj = obj.parent
    return obj.name


def samples(b):
    form = b['form']; z = b['elevation']; points = []
    def area(tri):
        a,c,d = tri
        return abs((c[0]-a[0])*(d[1]-a[1])-(c[1]-a[1])*(d[0]-a[0]))/2
    def edge_distance(x,y,polygons):
        distances=[]
        for poly in polygons:
            for ring in poly:
                for a,c in zip(ring,ring[1:]):
                    dx,dy=c[0]-a[0],c[1]-a[1];length2=dx*dx+dy*dy
                    t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/length2)) if length2 else 0
                    distances.append(math.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
        return min(distances)
    parts=form['parts'] or [{'id':'body','polygons':b['polygons'],'triangles':b['roofTriangles'],
                            'height':form['height'],'roof':form['roof']}]
    for part in parts:
        roof=part['roof'];triangles=[]
        if roof['type']!='flat':
            vertices=roof['geometry']['vertices'];indices=roof['geometry']['triangles']
            triangles=[[vertices[k] for k in indices[i:i+3]] for i in range(0,len(indices),3)]
        else:
            for poly,indices in zip(part['polygons'],part['triangles']):
                vertices=[list(p)+[0] for ring in poly for p in ring[:-1]]
                triangles += [[vertices[k] for k in indices[i:i+3]] for i in range(0,len(indices),3)]
        count=0
        for tri in sorted(triangles,key=area,reverse=True):
            x,y,h=[sum(p[k] for p in tri)/3 for k in range(3)]
            if area(tri)<.1 or edge_distance(x,y,part['polygons'])<.5:continue
            points.append({'kind':'roof','part':part['id'],'x':x,'y':y,
                           'top':z+part['height']+h+4,'expected':z+part['height']+h})
            count+=1
            if count>=3:break
        assert count>0,(b['id'],part['id'],'no usable roof samples')
    for e in form['entrances']:
        x,y=e['center'];a=math.radians(e['bearing']);nx,ny=math.sin(a),math.cos(a)
        if 'attachedPortico' in e:
            p=e['attachedPortico'];distance=p['depth']/2
            points.append({'kind':'entrance-platform','x':x+nx*distance,'y':y+ny*distance,
                           'top':z+p['platformHeight']+.5,'expected':z+p['platformHeight']})
            points.append({'kind':'entrance-canopy','x':x+nx*distance,'y':y+ny*distance,
                           'top':z+p['clearHeight']+p['slabThickness']+.5,
                           'expected':z+p['clearHeight']+p['slabThickness']})
            continue
        if 'stairFlight' in e:
            p=e['stairFlight'];rise=(e['landingHeight']-p['baseHeight'])/p['riserCount']
            for i in range(p['riserCount']):
                distance=p['landingDepth']/2 if i==0 else p['landingDepth']+(i-.5)*p['tread']
                expected=z+e['landingHeight']-i*rise
                for offset in (-p['width']/2+.2,0,p['width']/2-.2):
                    points.append({'kind':'entrance-stair','x':x+nx*distance+ny*offset,
                                   'y':y+ny*distance-nx*offset,'top':expected+.4,'expected':expected})
            continue
        platform=e['landingHeight']/2 if 'landingHeight' in e else e.get('platformHeight',.075)
        points.append({'kind':'entrance-platform','x':x+nx*1.6,'y':y+ny*1.6,
                       'top':z+platform+.5,'expected':z+platform})
    return points


def check_samples(b, trees, tolerance):
    result = []
    for p in samples(b):
        hits = [tree.ray_cast(Vector((p['x'],p['y'],p['top'])), Vector((0,0,-1))) for tree in trees]
        heights = [hit[0].z for hit in hits if hit[0] is not None]
        if not heights:
            raise AssertionError((b['id'],p,'missing surface'))
        actual = max(heights); error = abs(actual-p['expected'])
        if error > tolerance:
            raise AssertionError((b['id'],p,actual,error,tolerance))
        result.append({'kind':p['kind'],'errorMeters':round(error,6)})
    return result


def main():
    prefix=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'generic')
    if not re.fullmatch('[a-z0-9-]+',prefix):raise ValueError('Invalid report prefix')
    bs = [b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if ordinary(b)]
    colors = ['pink','livingWarm','livingCool','stone','stoneWarm','stoneCool','white','paleRoof','red','dark','path','shadeGlass','glass']
    C = {k:i for i,k in enumerate(colors)}
    MATERIALS[:]=[bpy.data.materials.new('generic-check-'+name) for name in colors]
    generated = []
    for b in bs:
        low = ordinary_building(b,b.get('elevation',0),C,False)
        high = ordinary_building(b,b.get('elevation',0),C,True)
        for (name,a,c),(other,x,y) in zip(low.parts[:3],high.parts[:3]):
            assert name == other and low.v[a:c] == high.v[x:y], (b['id'],name,'LOD form mismatch')
        assert all(math.isfinite(x) for v in high.v for x in v)
        if b['form']['roof']['type']!='flat':
            obj=high.object('source-weld-check',bpy.context.scene.collection)
            compact_form_source(obj)
            group=obj.vertex_groups['02_屋顶轮廓'].index
            actual=[v.co for v in obj.data.vertices if any(g.group==group for g in v.groups)]
            kd=KDTree(len(actual))
            for i,point in enumerate(actual):kd.insert(point,i)
            kd.balance()
            _,start,end=high.parts[1]
            assert all(kd.find(point)[2]<.0002 for point in high.v[start:end]),(b['id'],'welding lost shared eave group')
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
        # Dining facilities must not get the residential balcony extension.
        if b['form']['archetype'] == 'canteen':
            residential = {**b, 'form': {**b['form'], 'archetype':'dormitory'}}
            assert len(high.v) < len(ordinary_building(residential,b.get('elevation',0),C,True).v)
        generated.append({'id':b['id'],'roof':b['form']['roof']['type'],
                          'archetype':b['form']['archetype'],'sharedComponents':3})
    report = {'generatedBuildings':len(bs),'generated':generated,
              'scope':'ordinary buildings only; dedicated landmarks and monuments use their existing verifiers',
              'tolerancesMeters': {'source':.011,'baseDraco':.05,'nearDraco':.02}}
    target = ROOT/'docs/model-checks/refinement'
    target.mkdir(parents=True,exist_ok=True)
    if '--generated-only' in sys.argv:
        report['generatedPassed']=True
        (target/(prefix+'-generated.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(f'Generated form passed: {len(bs)} ordinary buildings',flush=True)
        return
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
    objects = {o.get('featureId'):o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('featureId')}
    C.clear();MATERIALS.clear()
    for mat in bpy.data.materials:
        C[mat.name]=len(MATERIALS);MATERIALS.append(mat)
    report['source']=[]
    for b in bs:
        o=objects[b['id']]
        expected=ordinary_building(b,b['elevation'],C,b['insideCampus'])
        for name,start,end in expected.parts[:3]:
            group=o.vertex_groups.get(name)
            assert group is not None,(b['id'],name,'missing editable component')
            actual=[v.co for v in o.data.vertices if any(g.group==group.index for g in v.groups)]
            # Source vertices are welded for file size; compare geometry in
            # both directions, independent of duplicate count or mesh ordering.
            predicted=expected.v[start:end]
            for left,right in ((actual,predicted),(predicted,actual)):
                if not left and not right:continue
                assert left and right,(b['id'],name,'empty source component')
                kd=KDTree(len(right))
                for i,point in enumerate(right):kd.insert(point,i)
                kd.balance()
                assert all(kd.find(point)[2]<.011 for point in left),(b['id'],name,'stale source form')
        report['source'].append({'id':b['id'],'samples':check_samples(b,[mesh_tree(o)],.011)})
    # Import shipping meshes, not a newly re-exported test substitute.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models/base.glb'))
    bpy.context.view_layer.update()
    trees={}
    for o in bpy.context.scene.objects:
        if o.type=='MESH': trees.setdefault(root_name(o),[]).append(mesh_tree(o))
    report['base']=[]
    for b in bs:
        key=b['chunk'] if b['insideCampus'] else 'context'
        report['base'].append({'id':b['id'],'samples':check_samples(b,trees[key],.05)})
    report['near']=[]
    for chunk in sorted({b['chunk'] for b in bs if b['insideCampus']}):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models'/f'{chunk}.glb'))
        bpy.context.view_layer.update()
        trees=[mesh_tree(o) for o in bpy.context.scene.objects if o.type=='MESH']
        for b in bs:
            if b.get('chunk')==chunk:
                report['near'].append({'id':b['id'],'samples':check_samples(b,trees,.02)})
    report['passed']=True
    (target/(prefix+'-geometry.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'Source/base/near form passed: {len(bs)} buildings',flush=True)


if __name__=='__main__':
    main()
