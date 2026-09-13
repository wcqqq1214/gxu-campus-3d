"""Inspect Math mass heights, relocated doors and solid enclosed window bands.

This verifies shipped geometry against the attributed partial calibration;
it does not certify the remaining eastern end or detailed portico as surveyed.
"""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-mathematics')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759129516')

def root_name(o):
    while o.parent:o=o.parent
    return o.name

def trees(objects,materials=None):
    out=[]
    for o in objects:
        if o.type!='MESH':continue
        faces=[tuple(p.vertices) for p in o.data.polygons if materials is None or o.data.materials[p.material_index].name.split('.')[0] in materials]
        if faces:out.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],faces))
    return out

def check(objects,tolerance,detail,ground):
    objects=list(objects);all_mesh=trees(objects);glass=trees(objects,{'glass','shadeGlass'});wall=trees(objects,{'stone'});white=trees(objects,{'white'});dark=trees(objects,{'dark'});samples=[]
    def ray(mesh,p,d,limit=1):
        return min((hit[3] for t in mesh if (hit:=t.ray_cast(Vector(p),Vector(d),limit))[0] is not None),default=None)
    def require(kind,mesh,p,d,expected,limit=1):
        actual=ray(mesh,p,d,limit)
        assert actual is not None and abs(actual-expected)<=tolerance,(kind,actual,expected,list(p))
        samples.append({'kind':kind,'errorMeters':abs(actual-expected)})
    # Interior roof samples, separate from roof/parapet generator output.
    for x,y,h in [(-276,-872,16.5),(-274,-881,16.5),(-254,-873,13.2),(-227,-873,13.2),(-201,-874,13.2)]:
        p=(x,y,b['elevation']+h+1)
        require('body-roof-height',all_mesh,p,(0,0,-1),1,2)
    panel_count=0
    for f in b['form']['facades']:
        a=Vector((*f['start'],b['elevation']));edge=Vector((*f['end'],b['elevation']))-a
        u=edge.normalized();n=Vector((*f['normal'],0))
        for panel in f['rule'].get('panels',[]):
            panel_count+=1
            width=edge.length*(panel['to']-panel['from']);height=panel['top']-panel['bottom'];fw=panel['frameWidth']
            cw=(width-2*fw)/panel['columns'];ch=(height-2*fw)/panel['rows']
            origin=a+edge*panel['from']+Vector((0,0,panel['bottom']))
            for col in range(panel['columns']):
                for row in range(panel['rows']):
                    center=origin+u*(fw+(col+.5)*cw)+Vector((0,0,fw+(row+.5)*ch))+n*.8
                    backing=dark if panel['type']=='lattice' else glass
                    require('panel-'+panel['type']+'-clear-cell',backing,center,-n,.76)
                    assert ray(white,center,-n) is None,('panel clear cell blocked',panel['id'],col,row)
                    if panel['type']=='lattice':
                        assert ray(glass,center,-n) is None,('generic glass behind screen',panel['id'],col,row)
                        require('octagonal-screen-bar',white,center-u*cw/2,-n,.75-panel['depth'])
            for s,up in [(fw/2,height*.5),(width-fw/2,height*.5),(width*.5,fw/2),(width*.5,height-fw/2)]:
                require('panel-outer-frame',white,origin+u*s+Vector((0,0,up))+n*.8,-n,.75-panel['depth'])
            # The solid wall remains behind the facade approximation.
            require('panel-solid-wall-retained',wall,origin+u*width/2+Vector((0,0,height/2))-n*.4,n,.4)
    assert panel_count==10,('missing panels from prepared data',panel_count)
    for f in b['form']['facades']:
        band=f['rule'].get('windowBands')
        if not band:continue
        assert f['part']=='lower-east' and f['levels']==4
        a=Vector((*f['start'],b['elevation']));edge=Vector((*f['end'],b['elevation']))-a;length=edge.length;u=edge/length;n=Vector((*f['normal'],0));fh=f['height']/f['levels']
        for level in range(1,4):
            for w in band['windows']:
                z=Vector((0,0,(level+.56)*fh))
                for t in [w['from']+.004,(w['from']+w['to'])/2,w['to']-.004]:
                    p=a+u*t*length+z+n*.8
                    require('enclosed-window-width',glass,p,-n,.55 if detail else .73)
                center=a+u*((w['from']+w['to'])/2)*length+z
                require('solid-backing',wall,center-n*.4,n,.4)
            for l,r in zip(band['windows'],band['windows'][1:]):
                p=a+u*((l['to']+r['from'])/2)*length+Vector((0,0,(level+.56)*fh))+n*.8
                assert ray(glass,p,-n) is None,('leftover generic window',f['edge'],level)
            # No fifth storey remains in the lower band.
            p=a+u*.5*length+Vector((0,0,14.8))+n*.8
            assert ray(all_mesh,p,-n) is None,('unexpected fifth storey',f['edge'])
    # The five-storey north end has four columns across two mapped edge
    # intervals. Check glass widths on both, not merely the configured count.
    north=[f for f in b['form']['facades'] if f['part']=='west-five' and f['edge'] in (1,11)]
    assert len(north)==2 and sum(f['rule']['windowGrid']['columns'] for f in north)==4
    for f in north:
        g=f['rule']['windowGrid'];a=Vector((*f['start'],b['elevation']))
        edge=Vector((*f['end'],b['elevation']))-a;u=edge/edge.length;n=Vector((*f['normal'],0))
        bay=(edge.length-2*g['edgeInset'])/g['columns'];width=bay*g['widthRatio']
        for level in range(5):
            for col in range(g['columns']):
                center=a+u*(g['edgeInset']+(col+.5)*bay)+Vector((0,0,(level+.56)*3.3))
                for offset in [-width*.45,0,width*.45]:
                    require('north-four-column-glazing',glass,center+u*offset+n*.8,-n,.55 if detail else .73)
                require('north-window-backing',wall,center-n*.4,n,.4)
    # West blank wall: several columns and all five storeys contain backing,
    # but none contains the old generic window material.
    f=next(f for f in b['form']['facades'] if f['edge']==10)
    a=Vector((*f['start'],b['elevation']));edge=Vector((*f['end'],b['elevation']))-a;n=Vector((*f['normal'],0))
    for level in range(5):
        for t in [.2,.5,.8]:
            p=a+edge*t+Vector((0,0,(level+.56)*3.3))+n*.8
            require('west-blank-wall',wall,p,-n,.8)
            assert ray(glass,p,-n) is None,('window on blank west wall',level,t)
    for e in b['form']['entrances']:
        n=Vector((math.sin(math.radians(e['bearing'])),math.cos(math.radians(e['bearing'])),0));a=Vector((*e['center'],b['elevation']))
        if 'attachedPortico' in e:
            p=e['attachedPortico'];tangent=Vector((n.y,-n.x,0));floor=p['platformHeight']
            assert len(p['columns'])==4 and p['parapetHeight']==0 and p['steps']==3
            for i,(x,y) in enumerate(p['columns']):
                center=Vector((x,y,b['elevation']+floor+1))
                require('north-portico-column',white,center+n*p['columnWidth'],-n,p['columnWidth']/2,p['columnWidth']*1.5)
            for distance in [.8,p['depth']/2,p['depth']-.25]:
                start=a+n*distance+Vector((0,0,floor+.3))
                require('north-portico-open-soffit',all_mesh,start,(0,0,1),p['clearHeight']-floor-.3,5)
            roof=p['clearHeight']+p['slabThickness']
            for u,v in [(0,p['depth']-.1),(-p['width']/2+.1,p['depth']/2),(p['width']/2-.1,p['depth']/2)]:
                require('north-portico-flat-roof-no-rail',white,a+tangent*u+n*v+Vector((0,0,roof+.7)),(0,0,-1),.7,1)
            require('north-portico-door',glass,a+n*.8+Vector((0,0,floor+1.4)),-n,.71)
            # Platform and every tread must span the specified width and
            # connect to actual terrain, not merely a data-level elevation.
            levels=[(p['depth']/2,floor)]+[(p['depth']+(i+.5)*p['tread'],p['stepBaseHeight']+(floor-p['stepBaseHeight'])*(p['steps']-i)/p['steps']) for i in range(p['steps'])]
            for distance,top in levels:
                for u in [-p['width']/2+.2,0,p['width']/2-.2]:
                    center=a+n*distance+tangent*u
                    require('north-portico-platform-width',wall,center+Vector((0,0,top+.4)),(0,0,-1),.4,1)
                    ground_distance=ray(ground,center+Vector((0,0,3)),(0,0,-1),10)
                    assert ground_distance is not None,('north portico ground absent',distance,u)
                    ground_relative=3-ground_distance
                    assert -.03<=top-ground_relative<=.65,('north portico step buried or high',distance,u,top-ground_relative)
                    assert ground_relative>=-.15-tolerance,('north portico bottom floats',distance,u,ground_relative)
                    samples.append({'kind':'north-portico-ground','localWidthOffset':u,'distance':distance,'topAboveGroundMeters':top-ground_relative})
            continue
        landing=e.get('landingHeight',0)
        require('relocated-door',glass,a+Vector((0,0,landing+1.3))+n*.8,-n,.625)
        require('relocated-canopy',white,a+n*.8+Vector((0,0,landing+3.5)),(0,0,-1),.475)
        tangent=Vector((n.y,-n.x,0))
        if 'doorFrame' in e:
            frame=e['doorFrame'];assert frame['bays']==3
            bay=e['width']/3;pw=frame['pierWidth'];pd=frame['pierDepth']
            for col in range(3):
                center=a+tangent*(-e['width']/2+(col+.5)*bay)+Vector((0,0,landing+1.3))
                for offset in [-(bay-pw)*.45,0,(bay-pw)*.45]:
                    require('three-door-openings',glass,center+tangent*offset+n*1.5,-n,1.325,2)
            for col in range(4):
                center=a+tangent*(-e['width']/2+col*bay)+Vector((0,0,landing+1.3))
                require('four-door-piers',wall,center+n*(pd+.3),-n,.5,2)
                assert ray(glass,center+n*1.5,-n,2) is None,('glass behind door pier',col)
            require('door-header',wall,a+n*(pd+.3)+Vector((0,0,landing+2.68)),-n,.5,2)
        if 'stairFlight' in e:
            flight=e['stairFlight'];assert flight['riserCount']==3
            stair_checks=[(flight['landingDepth']/2,flight['width'],landing,flight['baseHeight']-.15)]
            for i in range(1,flight['riserCount']):
                stair_checks.append((flight['landingDepth']+(i-.5)*flight['tread'],flight['width'],
                                     landing-(landing-flight['baseHeight'])*i/flight['riserCount'],flight['baseHeight']-.15))
        else:
            stair_checks=[(1.6,e['width']+1.6,landing/2 if landing else .075,-.15 if landing else -.005),
                          (.65,e['width']+1.2,landing if landing else .22,-.15 if landing else -.005)]
        for distance,width,top,bottom in stair_checks:
            for offset in [-width/2+.2,0,width/2-.2]:
                p=a+n*distance+tangent*offset
                require('landing-width-surface',all_mesh,p+Vector((0,0,top+.4)),(0,0,-1),.4)
                hit=ray(ground,p+Vector((0,0,3)),(0,0,-1),10)
                assert hit is not None,'missing actual ground'
                local_ground=3-hit
                assert top-local_ground>=.02-tolerance,('buried landing',e['id'],offset,top-local_ground)
                assert local_ground>=bottom-tolerance,('floating landing bottom',e['id'],offset,local_ground,bottom)
                samples.append({'kind':'actual-ground','entrance':e['id'],'topAboveGroundMeters':top-local_ground})
    # The old south midpoint must no longer have an exterior entry canopy.
    old=Vector((-233.10678553918217,-878.747067999861,b['elevation']+3.5))
    assert ray(white,old,(0,0,-1),1) is None,'Old midpoint canopy retained'
    return {'passed':True,'samples':samples,'panelsChecked':panel_count,'scope':'2 heights, 2 doors, 2 enclosed bands, west blank wall, continuous glass return and 3 lattice screens with 6 flank windows; source/base/near'}

report={'passed':False,'buildingId':b['id'],'wholeBuildingAccepted':False,'checkedRoot':str(TARGET),'tolerancesMeters':{'source':.011,'base':.05,'near':.02}}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    objs=[o for o in bpy.context.scene.objects if o.get('featureId')==b['id']];assert len(objs)==1
    ground=trees([o for o in bpy.context.scene.objects if o.get('layer')=='terrain'])
    report['source']=check(objs,.011,True,ground)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    ground=trees([o for o in bpy.context.scene.objects if o.get('layer')=='terrain'])
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==b['chunk']],.05,False,ground)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{b["chunk"]}.glb'));bpy.context.view_layer.update()
    report['near']=check(bpy.context.scene.objects,.02,True,ground)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/data/models.json','public/data/buildings.json','public/models/base.glb',f'public/models/{b["chunk"]}.glb']}
    report['passed']=True
except Exception as error:report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Mathematics actual geometry',report['passed'],flush=True)
