"""Inspect actual forestry windows, solid backing walls and shared ledges."""
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
TARGET = next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX = next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-forestry-facades')
b = next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='relation/11564703')
f = next(f for f in b['form']['facades'] if f['ring']==0 and f['edge']==5)
band = f['rule']['windowBands']
assert len(band['windows'])==7 and band['firstLevel']==1 and f['levels']==6


def root_name(o):
    while o.parent:o=o.parent
    return o.name


def bvhs(objects, materials):
    result=[]
    for o in objects:
        if o.type!='MESH':continue
        faces=[tuple(p.vertices) for p in o.data.polygons
               if o.data.materials[p.material_index].name.split('.')[0] in materials]
        if faces:result.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],faces))
    return result


def check(objects, tolerance, detail):
    glass=bvhs(objects,{'glass','shadeGlass'});white=bvhs(objects,{'white'})
    backing=bvhs(objects,{'stone'})
    a=Vector((*f['start'],b['elevation']));n=Vector((*f['normal'],0))
    edge=Vector((*f['end'],b['elevation']))-a;length=edge.length;u=edge/length
    fh=f['height']/f['levels'];samples=[]
    def ray(trees,p,d,maximum=1):
        hits=[tree.ray_cast(p,d,maximum) for tree in trees]
        return min((h[3] for h in hits if h[0] is not None),default=None)
    def require(label,trees,p,d,distance):
        actual=ray(trees,p,d)
        assert actual is not None and abs(actual-distance)<=tolerance,(label,actual,distance)
        samples.append({'kind':label,'errorMeters':abs(actual-distance)})
    for level in range(1,6):
        z=(level+.56)*fh
        for index,window in enumerate(band['windows']):
            center=a+u*((window['from']+window['to'])/2*length)+Vector((0,0,z))
            front=.25 if detail else .07
            for t in [window['from']+.002,(window['from']+window['to'])/2,window['to']-.002]:
                p=a+u*t*length+Vector((0,0,z))+n*.8
                require('window-span',glass,p,-n,.8-front)
            require('solid-wall-behind-window',backing,center-n*.4,n,.4)
            for pane in range(1,window['panes']):
                t=window['from']+(window['to']-window['from'])*pane/window['panes']
                p=a+u*t*length+Vector((0,0,z))+n*.8
                if detail:require('pane-bar',white,p,-n,.51)
                else:assert ray(white,p,-n) is None,('fine bar in base',level,index,pane)
        # Gaps between groups must not contain leftover generic glass.
        for left,right in zip(band['windows'],band['windows'][1:]):
            p=a+u*((left['to']+right['from'])/2*length)+Vector((0,0,z))+n*.8
            assert ray(glass,p,-n) is None,('generic window in calibrated gap',level)
            require('solid-gap',backing,p,-n,.8)
        ledge_top=(level+.56+band['heightRatio']/2)*fh+.12+band['thickness']
        for fraction in [band['from']+.01,(band['from']+band['to'])/2,band['to']-.01]:
            p=a+u*fraction*length+n*(band['depth']*.75)+Vector((0,0,ledge_top+.4))
            require('projecting-ledge-top',white,p,Vector((0,0,-1)),.4)
    return {'passed':True,'upperFloors':5,'windowGroupsPerFloor':7,'samples':samples,
            'actualWindowSpanSamples':105,'solidBackingSamples':35,'gapChecks':30,'ledgeSamples':15}


report={'passed':False,'buildingId':b['id'],'scope':'Only south central upper-storey window groups and ledges; source/base/near. No whole-building or field-dimension claim.',
        'checkedRoot':str(TARGET),'tolerancesMeters':{'source':.011,'base':.05,'near':.02}}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    objects=[o for o in bpy.context.scene.objects if o.get('featureId')==b['id']];assert len(objects)==1
    report['source']=check(objects,.011,True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==b['chunk']],.05,False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{b["chunk"]}.glb'));bpy.context.view_layer.update()
    report['near']=check(bpy.context.scene.objects,.02,True)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in
                           ['blender/gxu-campus.blend','public/data/models.json','public/data/buildings.json',
                            'public/models/base.glb',f'public/models/{b["chunk"]}.glb']}
    report['passed']=True
except Exception as error:
    report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Forestry facade checks',report['passed'],flush=True)
