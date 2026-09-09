#!/usr/bin/env python3
"""Build editable campus source and spatially streamed Draco GLBs with Blender 5.2."""
import bpy,sys,json,math,time,random,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import Mesh,material,MATERIALS
from landmarks import landmark
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
for name,color,rough,metal in [('gateStone','#d7d0bf',.84,0),('gateTrim','#e4ddca',.8,0),('gateJoint','#a9a18f',.95,0),('gateRecess','#b7ae9b',.92,0),('gateRed','#872e35',.48,.12),('gateFlower','#c25283',.9,0)]:
    C[name]=material(name,rgb(color),rough,metal)
# Original deterministic JPEG textures; packed into both .blend and exported GLBs.
texture_dir=ROOT/'blender/textures';texture_dir.mkdir(exist_ok=True)
for name in ['stone','grass','green','road','path','paleRoof','slate','sport','pitch']:
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
cols=terrain['cols'];rows=terrain['rows'];xmin,ymin,xmax,ymax=terrain['bounds'];hh=terrain['heights']
def elevation(x,y):
    u=max(0,min(cols-1.001,(x-xmin)/(xmax-xmin)*(cols-1)));v=max(0,min(rows-1.001,(y-ymin)/(ymax-ymin)*(rows-1)));i=int(u);j=int(v);a=u-i;b=v-j
    return (hh[j*cols+i]*(1-a)+hh[j*cols+i+1]*a)*(1-b)+(hh[(j+1)*cols+i]*(1-a)+hh[(j+1)*cols+i+1]*a)*b

def generic(b,detail):
    m=Mesh();h=b['height'];cx,cy=b['center'];z=elevation(cx,cy);wall=C['pink'] if b['category']=='living' else C['stone'] if b['category']=='academic' else C['white']
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
                            m.box(x+nx*.13,y+ny*.13,zz,ww,.10,wh,C['glass'],theta)
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
    if detail and b['height']<14 and len(b['polygons'][0])==1 and len(b['polygons'][0][0])==5 and all(abs(a[0]-bb[0])<.1 or abs(a[1]-bb[1])<.1 for a,bb in zip(b['polygons'][0][0],b['polygons'][0][0][1:])):
        a,bb,c,d=b['bounds'];m.roof((a+c)/2,(bb+d)/2,z+h+.5,c-a,d-bb,2.3,C['red'])
    return m
base={k:Mesh() for k in ['terrain','roads','water','green','sports','context','west','east','north']}
for j in range(rows-1):
    for i in range(cols-1):
        pts=[]
        for ii,jj in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]:
            x=xmin+(xmax-xmin)*ii/(cols-1);y=ymin+(ymax-ymin)*jj/(rows-1);pts.append((x,y,hh[jj*cols+ii]))
        base['terrain'].face(pts,C['grass'])
for s in surfaces:
    kind=s['kind'];verts=s['vertices'];tri=s['triangles'];mat=C['water'] if kind=='water' else C['sport'] if kind=='sports' else C['green'] if kind=='green' else C['path'] if s['tags'].get('highway') in ('path','footway','steps','pedestrian') else C['road']
    if kind=='sports' and s['tags'].get('sport') in ('soccer','basketball','tennis'):mat=C['pitch']
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
    if kind=='sports' and s['tags'].get('sport') in ('soccer','basketball','tennis'):
        vx=[v[0] for v in verts];vy=[v[1] for v in verts];x0,x1=min(vx)+1,max(vx)-1;y0,y1=min(vy)+1,max(vy)-1
        if x1-x0>8 and y1-y0>12:
            for a,b in [((x0,y0),(x1,y0)),((x1,y0),(x1,y1)),((x1,y1),(x0,y1)),((x0,y1),(x0,y0)),((x0,(y0+y1)/2),(x1,(y0+y1)/2))]:base[layer].line((*a,elevation(*a)+.2),(*b,elevation(*b)+.2),.10,C['white'],4)
print('Ground assembled',flush=True)
near={k:Mesh() for k in ['west','east','north']};zoneids={k:[] for k in near};bylandmark={b['landmark']:b for b in buildings if b['landmark']}
for index,b in enumerate(buildings):
    z=elevation(*b['center']);b['elevation']=round(z,2);zone='context' if not b['insideCampus'] else 'north' if b['center'][1]>200 else 'west' if b['center'][0]<0 else 'east';b['zone']=zone
    if b['landmark']:
        l=next(l for l in landmarks if l['id']==b['landmark']);low=landmark(l,b,z,C,False);high=landmark(l,b,z,C,True)
        base[zone].extend(low);obj=high.object(l['name'],SOURCE,{'featureId':b['id'],'landmark':l['id'],'layer':'buildings','sourceUrl':b['sourceUrl']})
        l['elevation']=round(z,2);l['zone']=zone
    else:
        low=generic(b,False);base[zone].extend(low)
        if zone!='context':
            high=generic(b,True);near[zone].extend(high);zoneids[zone].append(b['id']);high.object(b['name'],SOURCE,{'featureId':b['id'],'layer':'buildings','sourceUrl':b['sourceUrl']})
        else:low.object(b['name'],SOURCE,{'featureId':b['id'],'layer':'context'})
    if index%100==0:print('Buildings',index,'/',len(buildings),flush=True)
# Landmarks are independent streamed objects; do not duplicate them in zone replacements.
# Base landmark geometry gets a separate export group for each landmark below.
for zone in near:
    base[zone]=Mesh()
    for b in buildings:
        if b['zone']==zone and not b['landmark']:base[zone].extend(generic(b,False))
for l in landmarks:
    z=elevation(*l['center']);l['elevation']=round(z,2)
    if l['id']=='south-gate' and not l.get('osmId'):
        l['zone']='west';landmark(l,None,z,C,True).object(l['name'],SOURCE,{'featureId':'south-gate','landmark':l['id'],'layer':'buildings'})
    base['landmark-'+l['id']]=landmark(l,bylandmark.get(l['id']),z,C,False)
# Reusable tree templates; linked copies keep the Blender source small.
templates=[]
for typ in range(3):
    m=Mesh();m.cylinder(0,0,2.5,.24,5,C['bark'],8,topr=.12)
    if typ<2:
        rng=random.Random(200+typ)
        for i in range(8 if typ==0 else 5):
            angle=i*math.tau/8;r=1.7 if i else 0
            m.ellipsoid(math.cos(angle)*r,math.sin(angle)*r,5+rng.uniform(-.8,1.6),2.0,1.8,2.0 if typ==0 else 3.2,C[['leaf','leaf2','leaf3'][i%3]],8,5)
    else:
        for i in range(10):
            a=i*math.tau/10
            for j in range(5):
                r=j*.8;r1=(j+1)*.8;z0=6+math.sin(j/5*math.pi)*1.3-j*.26;z1=6+math.sin((j+1)/5*math.pi)*1.3-(j+1)*.26
                m.face([(math.cos(a)*r-math.sin(a)*.5,math.sin(a)*r+math.cos(a)*.5,z0),(math.cos(a)*r1,math.sin(a)*r1,z1),(math.cos(a)*r+math.sin(a)*.5,math.sin(a)*r-math.cos(a)*.5,z0)],C['leaf2'])
    templates.append(m.object(f'Tree-template-{typ}',PLANTS,{'template':typ}))
for i,(x,y,h,t) in enumerate(trees):
    o=bpy.data.objects.new(f'树木示意-{i:04}',templates[t].data);PLANTS.objects.link(o);o.location=(x,y,elevation(x,y));o.scale=(h/9,h/9,h/9);o.rotation_euler.z=i*2.399
for t in templates:t.hide_render=True;t.hide_set(True)
for k,m in base.items():
    if not k.startswith('landmark') and k not in near and k!='context':m.object(k,GROUND,{'layer':k})
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
        layer='buildings' if key in near or key.startswith('landmark') else key
        o=mesh.object(key,EXPORT,{'layer':layer,'zone':key if key in near else '', 'landmark':key[9:] if key.startswith('landmark-') else ''});o.select_set(True);objs.append(o)
    path=MODELS/name
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,export_draco_position_quantization=16,export_materials='EXPORT',export_cameras=False,export_lights=False)
    for o in objs:mesh=o.data;bpy.data.objects.remove(o,do_unlink=True);bpy.data.meshes.remove(mesh)
    print('Export',name,round(path.stat().st_size/1e6,2),'MB',flush=True);return path.stat().st_size
sizes={};sizes['base.glb']=export('base.glb',base)
for zone,m in near.items():sizes[f'{zone}.glb']=export(f'{zone}.glb',{zone:m})
for l in landmarks:
    key='landmark-'+l['id'];sizes[l['id']+'.glb']=export(l['id']+'.glb',{key:landmark(l,bylandmark.get(l['id']),l['elevation'],C,True)})
# Export only tree templates; runtime uses InstancedMesh grouped by spatial sector.
bpy.ops.object.select_all(action='DESELECT')
for o in templates:o.hide_set(False);o.hide_render=False;o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(MODELS/'trees.glb'),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=True)
for o in templates:o.hide_set(True);o.hide_render=True
(DATA/'buildings.json').write_text(json.dumps(buildings,ensure_ascii=False,separators=(',',':')))
(DATA/'landmarks.json').write_text(json.dumps(landmarks,ensure_ascii=False,separators=(',',':')))
manifest={'version':1,'units':'meters','axes':{'x':'east','y':'up','z':'south'},'base':{'url':'models/base.glb','bytes':sizes['base.glb']},'trees':{'url':'models/trees.glb','bytes':(MODELS/'trees.glb').stat().st_size},'zones':[{'id':k,'url':f'models/{k}.glb','bytes':sizes[k+'.glb'],'featureIds':zoneids[k]} for k in near],'landmarks':[{'id':l['id'],'url':f"models/{l['id']}.glb",'bytes':sizes[l['id']+'.glb']} for l in landmarks]}
for entry in [manifest['base'],manifest['trees']]+manifest['zones']+manifest['landmarks']:
    entry['sha256']=hashlib.sha256((ROOT/'public'/entry['url']).read_bytes()).hexdigest()
(DATA/'models.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
bpy.data.collections.remove(EXPORT)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'),compress=True)
print('COMPLETE',len(buildings),'buildings;',len(trees),'trees; source',round((ROOT/'blender/gxu-campus.blend').stat().st_size/1e6,2),'MB',flush=True)
