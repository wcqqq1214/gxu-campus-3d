#!/usr/bin/env python3
"""Build editable campus source and spatially streamed Draco GLBs with Blender 5.2."""
import bpy,sys,json,math,time,random,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
BASE_ONLY='--base-only' in sys.argv
from geometry import Mesh,material,MATERIALS
from landmarks import landmark
from huicui import huicui,compact_source
from sports import athletics,west_stand
from infrastructure import road_chunk,bridge,approaches,lake_bridge
DATA=ROOT/'public/data';MODELS=ROOT/'public/models';MODELS.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if not c.objects:bpy.data.collections.remove(c)
def collection(name):
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);return c
SOURCE=collection('校园建筑 · 可编辑');GROUND=collection('道路水体与地形');PLANTS=collection('植被示意 · 固定随机种子');EXPORT=collection('网页导出 · 临时')
def rgb(h):
    v=[int(h[i:i+2],16)/255 for i in (1,3,5)];return tuple(((c+.055)/1.055)**2.4 if c>.04045 else c/12.92 for c in v)
C={}
for name,color,rough,metal in [('stone','#cebfaa',.83,0),('white','#eeeee4',.74,0),('glass','#527a83',.23,.35),('dark','#35494b',.72,0),('slate','#4d6c70',.6,.15),('paleRoof','#bdbfb7',.7,.12),('wood','#725246',.92,0),('red','#ad6c54',.8,0),('pink','#d1afa0',.9,0),('grass','#819668',1,0),('green','#64916b',1,0),('road','#a0a69e',.93,0),('path','#c7bda9',.98,0),('water','#488f8a',.2,.25),('sport','#b1785e',.93,0),('pitch','#659578',1,0),('metal','#8e9b9e',.45,.45),('bark','#6e6650',1,0),('leaf','#3f7049',1,0),('leaf2','#56824c',1,0),('leaf3','#67904f',1,0)]:C[name]=material(name,rgb(color),rough,metal)
terrain=json.loads((DATA/'terrain.json').read_text());buildings=json.loads((DATA/'buildings.json').read_text());landmarks=json.loads((DATA/'landmarks.json').read_text());surfaces=json.loads((DATA/'surfaces.json').read_text());trees=json.loads((DATA/'vegetation.json').read_text())
fields=json.loads((DATA/'sports.json').read_text())
infrastructure=json.loads((DATA/'infrastructure.json').read_text())
surroundings=json.loads((DATA/'surroundings.json').read_text())
basketball=json.loads((DATA/'basketball.json').read_text())
bridge_by_id={b['id']:b for b in infrastructure['bridges']}
lake_by_id={b['id']:b for b in infrastructure['lakeBridges']}
for name,color,rough,metal in [('asphalt','#626664',.97,0),('pavingRed','#b97865',.93,0),('tactile','#d6b663',.95,0),('curb','#c7c9bd',.86,0),('roadWhite','#f0ecda',.92,0),('roadYellow','#e5c266',.92,0),('wallStone','#d6c8aa',.9,0),('fenceIron','#343e3d',.63,.4),('lampMetal','#929f9e',.48,.5),('lampGlass','#e7e8cf',.25,.15),('bridgeConcrete','#afb2a6',.91,0),('bridgeEdge','#c7c9bd',.86,0),('bridgeJoint','#525b59',.95,0),('bridgePlaque','#665d4f',.82,0),('drainStone','#bfc0b3',.94,0)]:
    C[name]=material(name,rgb(color),rough,metal)
for name,color in [('track','#ba563f'),('trackAlt','#b7543e'),('trackApron','#a9513e'),('fieldGreen','#3d8650'),('fieldStripe','#458f57'),('sportWhite','#f5f3e7'),('goalNet','#c1cabb'),('seatYellow','#c9d92f'),('seatGreen','#6dbe33'),('seatBlue','#5cbdca')]:
    C[name]=material(name,rgb(color),.92,0)
for name,color,rough,metal in [('gateStone','#d7d0bf',.84,0),('gateTrim','#e4ddca',.8,0),('gateJoint','#a9a18f',.95,0),('gateRecess','#b7ae9b',.92,0),('gateRed','#872e35',.48,.12),('gateFlower','#c25283',.9,0)]:
    C[name]=material(name,rgb(color),rough,metal)
for name,color,rough,metal in [('libraryStone','#c6b9a7',.8,0),('libraryTrim','#e5e3d8',.7,0),('libraryGlass','#4b9ea9',.25,.32),('libraryMullion','#536d72',.5,.35),('libraryInk','#283d62',.6,.1),('residenceStone','#cbbbaf',.86,0),('residencePodium','#6f7a7a',.78,0),('residenceGlass','#7c9fae',.26,.32)]:
    C[name]=material(name,rgb(color),rough,metal)
for name,color,rough,metal in [('timeSilver','#e1e5e6',.19,.96),('timeLetter','#c6b582',.6,.5),('timeLight','#bcd8e6',.25,.2)]:
    C[name]=material(name,rgb(color),rough,metal)
for name,color,rough,metal in [('tenWall','#e1c7b3',.88,0),('tenTrim','#e8e7de',.8,0),('tenGlass','#527d88',.24,.28)]:
    C[name]=material(name,rgb(color),rough,metal)
for name,color,rough,metal in [('courtGreen','#347e69',.92,0),('courtKey','#bd6447',.92,0),('courtApron','#47746a',.95,0),('courtFrame','#246752',.57,.24),('courtMetal','#879593',.47,.55),('courtOrange','#e5762c',.56,.2),('courtGlass','#a7c7c6',.20,.05)]:
    C[name]=material(name,rgb(color),rough,metal)
for name,color,rough,metal in [('huicuiWall','#c7b49b',.86,0),('huicuiTrim','#e0d8c8',.78,0),('huicuiGlass','#54747d',.24,.3),('huicuiFrame','#555c5d',.50,.3)]:
    C[name]=material(name,rgb(color),rough,metal)
# Original deterministic JPEG textures; packed into both .blend and exported GLBs.
texture_dir=ROOT/'blender/textures';texture_dir.mkdir(exist_ok=True)
for name in ['stone','grass','green','road','path','paleRoof','slate','sport','pitch','asphalt']:
    mat=MATERIALS[C[name]];base=[1.055*(v**(1/2.4))-.055 if v>.0031308 else v*12.92 for v in mat.diffuse_color[:3]];image=bpy.data.images.new('自制-'+name,width=128,height=128)
    rng=random.Random(name);pixels=[]
    for j in range(128):
        for i in range(128):
            grain=rng.uniform(.83,1.06)
            if name in ['stone','path'] and (j%32==0 or i%64==0):grain*=.83
            if name=='slate' and j%8==0:grain*=.72
            pixels.extend([min(1,v*grain) for v in base]+[1])
    image.pixels.foreach_set(pixels);image.filepath_raw=str(texture_dir/(name+'.jpg'));image.file_format='JPEG';image.save();image.pack()
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image;node.extension='REPEAT';mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
# Modest near-view variation remains an explicitly estimated facade treatment.
for name,color in [('stoneWarm','#c6b69f'),('stoneCool','#c5c0b1'),('livingWarm','#d0b39f'),('livingCool','#c3b0a4'),('shadeGlass','#3b6573')]:
    C[name]=material(name,rgb(color),.28 if name.endswith('Glass') else .84,.28 if name.endswith('Glass') else 0)
cols=terrain['cols'];rows=terrain['rows'];xmin,ymin,xmax,ymax=terrain['bounds'];hh=terrain['heights']
def elevation(x,y):
    u=max(0,min(cols-1.001,(x-xmin)/(xmax-xmin)*(cols-1)));v=max(0,min(rows-1.001,(y-ymin)/(ymax-ymin)*(rows-1)));i=int(u);j=int(v);a=u-i;b=v-j
    return (hh[j*cols+i]*(1-a)+hh[j*cols+i+1]*a)*(1-b)+(hh[(j+1)*cols+i]*(1-a)+hh[(j+1)*cols+i+1]*a)*b

def generic(b,detail):
    if b.get('customModel')=='huicui':return huicui(b,elevation(*b['center']),C,detail)
    m=Mesh();h=b['height'];cx,cy=b['center'];z=elevation(cx,cy);wall=C['pink'] if b['category']=='living' else C['stone'] if b['category']=='academic' else C['white']
    seed=int(hashlib.sha256(b['id'].encode()).hexdigest()[:8],16)
    if detail and b['category'] in ('academic','living'):
        choices=['pink','livingWarm','livingCool'] if b['category']=='living' else ['stone','stoneWarm','stoneCool']
        wall=C[choices[seed%3]]
    if b['id']=='way/948683815':return west_stand(b,z,C,detail)
    if b['tags'].get('memorial')=='column':
        # The four mapped historic inner-gate piers are monuments, not windowed houses.
        x0,y0,x1,y1=b['bounds'];w=x1-x0;d=y1-y0;stone=C['gateStone'];trim=C['gateTrim']
        m.box(cx,cy,z+.25,w+.35,d+.35,.5,trim)
        m.box(cx,cy,z+h*.43,w*.80,d*.80,h*.74,stone)
        for zz,scale,hh in [(h*.10,1,.22),(h*.76,1.04,.18),(h*.87,1.15,h*.20),(h*.99,1.3,.18)]:
            m.box(cx,cy,z+zz,w*scale,d*scale,hh,trim)
        for sy in [-1,1]:
            for i in range(9):m.box(cx+(i-4)*w*.072,cy+sy*d*.408,z+h*.42,.035,.045,h*.61,trim)
            if detail:
                for i in range(5):m.ellipsoid(cx+(i-2)*w*.19,cy+sy*d*.59,z+h*.86,w*.085,.10,h*.072,stone,8,5)
        for sx in [-1,1]:
            for i in range(9):m.box(cx+sx*w*.408,cy+(i-4)*d*.072,z+h*.42,.045,.035,h*.61,trim)
        m.roof(cx,cy,z+h+0.08,w*1.4,d*1.4,.35,stone)
        return m
    if b['tags'].get('building:colour'):
        # Keep the shared palette bounded for batching; common OSM pink / yellow families map to it.
        wall=C['pink'] if b['tags']['building:colour'].lower()=='#f0a0a0' else wall
    m.extrude(b['polygons'],b['roofTriangles'],z-.5,h+.5,wall,C['paleRoof'])
    for poly in b['polygons']:
        for ring in poly:
            area=sum(a[0]*bb[1]-bb[0]*a[1] for a,bb in zip(ring,ring[1:]));sign=1 if area>0 else -1
            for a,bb in zip(ring,ring[1:]):
                dx=bb[0]-a[0];dy=bb[1]-a[1];length=math.hypot(dx,dy)
                if length<2:continue
                nx=dy/length*sign;ny=-dx/length*sign;theta=math.atan2(dy,dx);num=max(1,int(length/4));levels=max(1,round(h/3.3))
                for level in range(levels):
                    for i in range(num):
                        f=(i+.5)/num;x=a[0]+dx*f+nx*.07;y=a[1]+dy*f+ny*.07;zz=z+(level+.56)*h/levels;ww=min(2.1,length/num*.60);wh=min(1.9,h/levels*.55)
                        # Flat panes remain present in the lightweight model; near LOD adds relief and mullions.
                        if detail:
                            m.box(x,y,zz,ww+.30,.22,wh+.30,C['white'],theta)
                            m.box(x+nx*.13,y+ny*.13,zz,ww,.10,wh,C['shadeGlass'] if (seed+i*7+level*13)%7<2 else C['glass'],theta)
                            m.box(x+nx*.2,y+ny*.2,zz,.055,.10,wh,C['white'],theta)
                            if b['category']=='living' and i%2==0:
                                m.box(x+nx*.65,y+ny*.65,zz-wh*.52,ww+.5,1.3,.14,C['white'],theta)
                                m.box(x+nx*1.15,y+ny*1.15,zz-wh*.25,ww+.5,.1,.65,wall,theta)
                        else:
                            ux=dx/length*ww/2;uy=dy/length*ww/2
                            m.face([(x-ux,y-uy,zz-wh/2),(x+ux,y+uy,zz-wh/2),(x+ux,y+uy,zz+wh/2),(x-ux,y-uy,zz+wh/2)],C['glass'])
                if detail:m.box((a[0]+bb[0])/2,(a[1]+bb[1])/2,z+h+.4,length,.25,.8,C['white'],theta)
        if detail:
            ring=poly[0];a,bb=max(zip(ring,ring[1:]),key=lambda p:math.dist(*p));dx=bb[0]-a[0];dy=bb[1]-a[1];theta=math.atan2(dy,dx);x=(a[0]+bb[0])/2;y=(a[1]+bb[1])/2
            m.box(x,y,z+1.3,2.2,.35,2.6,C['dark'],theta);m.box(x,y,z+2.9,3.5,2.5,.25,C['white'],theta)
            area=sum(a[0]*bb[1]-bb[0]*a[1] for a,bb in zip(ring,ring[1:]));sign=1 if area>0 else -1
            length=math.hypot(dx,dy);nx=dy/length*sign;ny=-dx/length*sign
            m.box(x+nx*.65,y+ny*.65,z+.12,3.4,1.6,.20,C['path'],theta)
            m.box(x+nx*.9,y+ny*.9,z+.035,3.8,2,.08,C['stone'],theta)
    if detail and b['height']<14 and len(b['polygons'][0])==1 and len(b['polygons'][0][0])==5 and all(abs(a[0]-bb[0])<.1 or abs(a[1]-bb[1])<.1 for a,bb in zip(b['polygons'][0][0],b['polygons'][0][0][1:])):
        a,bb,c,d=b['bounds'];m.roof((a+c)/2,(bb+d)/2,z+h+.5,c-a,d-bb,2.3,C['red'])
    return m
base={k:Mesh() for k in ['terrain','roads','water','green','sports','context']}
cut_cells=set(infrastructure['terrainCells'])|set(basketball['terrainCells'])
for j in range(rows-1):
    for i in range(cols-1):
        if j*(cols-1)+i in cut_cells:continue
        pts=[]
        for ii,jj in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]:
            x=xmin+(xmax-xmin)*ii/(cols-1);y=ymin+(ymax-ymin)*jj/(rows-1);pts.append((x,y,hh[jj*cols+ii]))
        base['terrain'].face(pts,C['grass'])
for patch in infrastructure['terrainPatch']+basketball['terrainPatch']:
    for i in range(0,len(patch['triangles']),3):base['terrain'].face([patch['vertices'][k] for k in patch['triangles'][i:i+3]],C['grass'])
for si,original in enumerate(surfaces):
    s=original
    if s['id'] in infrastructure['replaceSurfaceIds']:continue
    if str(si) in infrastructure['surfaceOverrides']:s={**s,**infrastructure['surfaceOverrides'][str(si)]}
    if str(si) in surroundings['surfaceOverrides']:s={**s,**surroundings['surfaceOverrides'][str(si)]}
    if not s['vertices']:continue
    if s['id'] in [field['osmId'] for field in fields] or s['id'] in [court['osmId'] for court in basketball['courts']]:continue
    kind=s['kind'];verts=s['vertices'];tri=s['triangles'];mat=C['water'] if kind=='water' else C['sport'] if kind=='sports' else C['green'] if kind=='green' else C['path'] if s['tags'].get('highway') in ('path','footway','steps','pedestrian') else C['road']
    if kind=='sports' and s['tags'].get('sport') in ('soccer','tennis'):mat=C['pitch']
    layer='sports' if kind=='sports' else kind
    if layer not in base:continue
    zwater=s.get('waterLevel',sum(elevation(x,y) for x,y in verts)/len(verts)+.12)
    def drape(points,depth=0):
        # Long OSM edges must be tessellated to follow the DEM, especially roads and shores.
        if kind!='water' and depth<7 and max(math.dist(a,b) for a,b in zip(points,points[1:]+points[:1]))>28:
            a,b,c=points;ab=tuple((a[k]+b[k])/2 for k in range(2));bc=tuple((b[k]+c[k])/2 for k in range(2));ca=tuple((c[k]+a[k])/2 for k in range(2))
            for piece in [[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]]:drape(piece,depth+1)
        else:base[layer].face([(p[0],p[1],zwater if kind=='water' else elevation(*p)+(.40 if kind=='roads' else .26)) for p in points],mat)
    for i in range(0,len(tri),3):
        drape([verts[k] for k in tri[i:i+3]])
    if kind=='sports' and s['tags'].get('sport') in ('soccer','tennis'):
        vx=[v[0] for v in verts];vy=[v[1] for v in verts];x0,x1=min(vx)+1,max(vx)-1;y0,y1=min(vy)+1,max(vy)-1
        if x1-x0>8 and y1-y0>12:
            for a,b in [((x0,y0),(x1,y0)),((x1,y0),(x1,y1)),((x1,y1),(x0,y1)),((x0,y1),(x0,y0)),((x0,(y0+y1)/2),(x1,(y0+y1)/2))]:base[layer].line((*a,elevation(*a)+.2),(*b,elevation(*b)+.2),.10,C['white'],4)
from surroundings import surroundings_mesh
base['roads'].extend(surroundings_mesh(surroundings,C,elevation,base['terrain']))
print('Ground assembled',flush=True)
infra_near={}
for chunk in infrastructure['chunks']:
    key=chunk['id'];build=lambda detail:road_chunk(chunk,C,detail) if chunk['kind']=='corridor' else lake_bridge(lake_by_id[chunk['bridgeId']],C,detail)
    base[key]=build(False)
    if not BASE_ONLY:
        high=build(True);infra_near[key]=high
        high.object(('农院路 · 路段 ' if chunk['kind']=='corridor' else '跨水桥 · ')+key,GROUND,{'layer':'roads','infrastructureId':key,'precision':'OSM 位置；路幅、细部及配置按参考资料估算'})
for b in infrastructure['bridges']:
    base['infra-approach-'+b['id']]=approaches(b,C)
if not BASE_ONLY:base['sports'].object('其他运动场地',GROUND,{'layer':'sports'})
for field in fields:
    mesh=athletics(field,C)
    if not BASE_ONLY:mesh.object(field['name'],GROUND,{'layer':'sports','featureId':field['osmId'],'sportsId':field['id'],'precision':field['precision']})
    # Separate nodes bound Draco quantization to ~180 meters instead of the
    # campus-wide sports extent; paint stays distinct at 16 bits without bloat.
    base['sports-'+field['id']]=mesh
from basketball import bank_model,court_model,bank_paving
for bank in basketball['banks']:
    base[bank['id']]=bank_model(bank,basketball['courts'],C)
    if not BASE_ONLY:
        bank_paving(bank,C).object(bank['id']+'-paving',GROUND,{'layer':'sports','basketballBank':bank['id']})
if not BASE_ONLY:
    for court in basketball['courts']:court_model(court,C).object(court['id'],GROUND,{'layer':'sports','featureId':court['osmId'],'precision':court['precision'],'basketballCourt':court['id']})
# Whole buildings belong to one 360 m cell, including their courtyard rings.
# Base nodes use the same key, so each near chunk replaces exactly its own low LOD.
CHUNK_METERS=360
near={};zoneids={};chunkbounds={};bylandmark={b['landmark']:b for b in buildings if b['landmark']}
def chunk_key(b):
    ix=math.floor(b['center'][0]/CHUNK_METERS);iy=math.floor(b['center'][1]/CHUNK_METERS)
    def label(v):return ('p' if v>=0 else 'n')+str(abs(v))
    return 'chunk-'+label(ix)+'-'+label(iy)
for index,b in enumerate(buildings):
    z=elevation(*b['center']);b['elevation']=round(z,2)
    zone='context' if not b['insideCampus'] else 'north' if b['center'][1]>200 else 'west' if b['center'][0]<0 else 'east';b['zone']=zone
    if b['landmark']:
        l=next(l for l in landmarks if l['id']==b['landmark'])
        if not BASE_ONLY:
            obj=landmark(l,b,z,C,True).object(l['name'],SOURCE,{'featureId':b['id'],'landmark':l['id'],'layer':'buildings','sourceUrl':b['sourceUrl']})
            if l['id']=='huicui':obj['customModel']='huicui';obj['precision']=b['architecture']['precision'];compact_source(obj)
        l['elevation']=round(z,2);l['zone']=zone
    elif zone=='context':
        low=generic(b,False);base['context'].extend(low)
        if not BASE_ONLY:low.object(b['name'],SOURCE,{'featureId':b['id'],'layer':'context'})
    else:
        key=chunk_key(b);b['chunk']=key
        if key not in near:near[key]=Mesh();base[key]=Mesh();zoneids[key]=[];chunkbounds[key]=[math.inf,math.inf,-math.inf,-math.inf]
        base[key].extend(generic(b,False));zoneids[key].append(b['id'])
        bounds=chunkbounds[key]
        for k in range(2):bounds[k]=min(bounds[k],b['bounds'][k]-2);bounds[k+2]=max(bounds[k+2],b['bounds'][k+2]+2)
        if not BASE_ONLY:
            high=generic(b,True);near[key].extend(high)
            obj=high.object('荟萃楼 · 新闻传播学院共用楼体' if b.get('customModel')=='huicui' else b['name'],SOURCE,{'featureId':b['id'],'chunk':key,'layer':'buildings','sourceUrl':b['sourceUrl']})
            if b.get('customModel')=='huicui':
                obj['customModel']='huicui';obj['precision']=b['architecture']['precision'];compact_source(obj)
    if index%100==0:print('Buildings',index,'/',len(buildings),flush=True)
for l in landmarks:
    if l.get('placeKind')=='bridge':
        b=bridge_by_id[l['id']]
        l['elevation']=b['floorElevation'];l['zone']='roads'
        base['landmark-'+l['id']]=bridge(b,C,False)
        if not BASE_ONLY:bridge(b,C,True).object(l['name'],GROUND,{'featureId':b['osmId'],'landmark':l['id'],'layer':'roads','sourceUrl':b['sourceUrl']})
        continue
    z=elevation(*l['center']);l['elevation']=round(z,2)
    if l['id'] not in bylandmark:
        l['zone']='west' if l['center'][0]<0 else 'east'
        if not BASE_ONLY:landmark(l,None,z,C,True).object(l['name'],SOURCE,{'featureId':l.get('osmId',l['id']),'landmark':l['id'],'layer':'buildings','sourceUrl':l['sourceUrl']})
    base['landmark-'+l['id']]=landmark(l,bylandmark.get(l['id']),z,C,False)
# Reusable tree templates; linked copies keep the Blender source small.
from vegetation import tree_templates
templates=tree_templates(C,PLANTS,True)
for i,(x,y,h,t) in enumerate([] if BASE_ONLY else trees):
    o=bpy.data.objects.new(f'树木示意-{i:04}',templates[t].data);PLANTS.objects.link(o);o.location=(x,y,elevation(x,y));o.scale=(h/9,h/9,h/9);o.rotation_euler.z=i*2.399
for t in templates:t.hide_render=True;t.hide_set(True)
for k,m in base.items():
    if not BASE_ONLY and not k.startswith(('landmark','sports-','basketball-')) and k not in near and k not in infra_near and k not in ('context','sports'):m.object(k,GROUND,{'layer':'roads' if k.startswith('infra-') else k})
# A neutral studio sky and solar lighting for editable source preview.
world=bpy.data.worlds.new('南宁晴空');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.58,.73,.88,1);world.node_tree.nodes['Background'].inputs[1].default_value=.7;bpy.context.scene.world=world
light=bpy.data.lights.new('下午日光','SUN');light.energy=2.5;light.angle=.08;sun=bpy.data.objects.new('下午日光',light);GROUND.objects.link(sun);sun.rotation_euler=(.4,-.6,-.6)
camdata=bpy.data.cameras.new('校园鸟瞰');cam=bpy.data.objects.new('校园鸟瞰',camdata);GROUND.objects.link(cam)
from mathutils import Vector
cam.location=(1800,-2400,2600);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=3700;bpy.context.scene.camera=cam
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
# Export aggregated geometry for low draw-call counts, retain individual editable source objects above.
def export(name,groups):
    bpy.ops.object.select_all(action='DESELECT');objs=[]
    for key,mesh in groups.items():
        if not mesh.v:continue
        layer='roads' if key.startswith('infra-') or key.removeprefix('landmark-') in bridge_by_id else 'buildings' if key in near or key.startswith('landmark') else 'sports' if key.startswith(('sports-','basketball-')) else key
        o=mesh.object(key,EXPORT,{'layer':layer,'zone':key if key in near else '', 'landmark':key[9:] if key.startswith('landmark-') else '', 'sportsId':key[7:] if key.startswith('sports-') else ''});o.select_set(True);objs.append(o)
    path=MODELS/name
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,export_draco_position_quantization=15 if name=='base.glb' else 16,export_draco_normal_quantization=6 if name=='base.glb' else 10,export_materials='EXPORT',export_cameras=False,export_lights=False)
    for o in objs:mesh=o.data;bpy.data.objects.remove(o,do_unlink=True);bpy.data.meshes.remove(mesh)
    print('Export',name,round(path.stat().st_size/1e6,2),'MB',flush=True);return path.stat().st_size
sizes={};sizes['base.glb']=export('base.glb',base)
if BASE_ONLY:
    manifest=json.loads((DATA/'models.json').read_text())
    if {z['id'] for z in manifest['zones']}!=set(near):raise RuntimeError('Chunk layout changed; run a full build before --base-only')
    manifest['base'].update(bytes=sizes['base.glb'],sha256=hashlib.sha256((MODELS/'base.glb').read_bytes()).hexdigest())
    (DATA/'models.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('Base-only export complete; retained editable source and near models',flush=True)
    sys.exit(0)
for zone,m in near.items():sizes[f'{zone}.glb']=export(f'{zone}.glb',{zone:m})
for key,m in infra_near.items():sizes[f'{key}.glb']=export(f'{key}.glb',{key:m})
for l in landmarks:
    key='landmark-'+l['id'];mesh=bridge(bridge_by_id[l['id']],C,True) if l.get('placeKind')=='bridge' else landmark(l,bylandmark.get(l['id']),l['elevation'],C,True)
    sizes[l['id']+'.glb']=export(l['id']+'.glb',{key:mesh})
# Export only tree templates; runtime uses InstancedMesh grouped by spatial sector.
bpy.ops.object.select_all(action='DESELECT')
for o in templates:o.hide_set(False);o.hide_render=False;o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(MODELS/'trees-near.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=True)
for o in templates:o.hide_set(True);o.hide_render=True
# Far templates keep the initial scene light; high templates stream only for close views.
low_templates=tree_templates(C,PLANTS,False)
bpy.ops.object.select_all(action='DESELECT')
for o in low_templates:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(MODELS/'trees.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=True)
for o in low_templates:
    mesh=o.data;bpy.data.objects.remove(o,do_unlink=True);bpy.data.meshes.remove(mesh)
(DATA/'buildings.json').write_text(json.dumps(buildings,ensure_ascii=False,separators=(',',':')))
(DATA/'landmarks.json').write_text(json.dumps(landmarks,ensure_ascii=False,separators=(',',':')))
manifest={'version':2,'chunkSizeMeters':CHUNK_METERS,'units':'meters','axes':{'x':'east','y':'up','z':'south'},'base':{'url':'models/base.glb','bytes':sizes['base.glb']},'trees':{'url':'models/trees.glb','bytes':(MODELS/'trees.glb').stat().st_size},'treesNear':{'url':'models/trees-near.glb','bytes':(MODELS/'trees-near.glb').stat().st_size},'zones':[{'id':k,'url':f'models/{k}.glb','bytes':sizes[k+'.glb'],'featureIds':zoneids[k],'bounds':chunkbounds[k]} for k in sorted(near)],'landmarks':[{'id':l['id'],'url':f"models/{l['id']}.glb",'bytes':sizes[l['id']+'.glb']} for l in landmarks]}
manifest['infrastructure']=[{'id':c['id'],'url':f"models/{c['id']}.glb",'bytes':sizes[c['id']+'.glb'],'bounds':c['bounds'],'layer':'roads'} for c in infrastructure['chunks']]
for entry in [manifest['base'],manifest['trees'],manifest['treesNear']]+manifest['zones']+manifest['landmarks']+manifest['infrastructure']:
    entry['sha256']=hashlib.sha256((ROOT/'public'/entry['url']).read_bytes()).hexdigest()
(DATA/'models.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
# Remove only obsolete generated near models after the new manifest is complete.
for old in [MODELS/'west.glb',MODELS/'east.glb',MODELS/'north.glb']:
    old.unlink(missing_ok=True)
bpy.data.collections.remove(EXPORT)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'),compress=True)
print('COMPLETE',len(buildings),'buildings;',len(trees),'trees; source',round((ROOT/'blender/gxu-campus.blend').stat().st_size/1e6,2),'MB',flush=True)
