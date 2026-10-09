"""Update north-campus chunks, add the site, retain all other compressed assets."""
import copy
import hashlib
import json
import struct
import sys
import tempfile
from pathlib import Path

import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from geometry import MATERIALS,Mesh
from generic_buildings import ordinary_building,compact_form_source
from north_campus import building_model,site_models
from preserve_glb_geometry import unpack,mesh_nodes_by_name,compact_buffer_views
from update_south_gate import export,replace_node_geometry,compact_static_accessors,signatures
from north_campus_export import export_north_base


def write_glb(path,doc,binary):
    header=json.dumps(doc,separators=(',',':')).encode()
    header+=b' '*(-len(header)%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(header)+len(binary))+
                     struct.pack('<I4s',len(header),b'JSON')+header+
                     struct.pack('<I4s',len(binary),b'BIN\0')+binary)


def put_node(raw,path,name):
    src,_=unpack(raw);dst,binary=unpack(path.read_bytes())
    if name not in mesh_nodes_by_name(dst):
        node=copy.deepcopy(mesh_nodes_by_name(src)[name])
        node['mesh']=len(dst['meshes']);dst['meshes'].append({'name':name,'primitives':[]})
        dst['scenes'][dst.get('scene',0)]['nodes'].append(len(dst['nodes']))
        dst['nodes'].append(node)
        write_glb(path,dst,binary)
    replace_node_geometry(raw,path,name)


def main():
    models=ROOT/'public/models';data=ROOT/'public/data'
    original={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in models.glob('*.glb')}
    before=(models/'base.glb').read_bytes()
    buildings=json.loads((data/'buildings.json').read_text())
    records=[b for b in buildings if b.get('customModel')=='north-campus']
    assert records
    keys={b['chunk'] for b in records}
    terrain=json.loads((data/'terrain.json').read_text())
    def elevation(x,y):
        cols,rows=terrain['cols'],terrain['rows'];x0,y0,x1,y1=terrain['bounds'];hh=terrain['heights']
        u=max(0,min(cols-1.001,(x-x0)/(x1-x0)*(cols-1)));v=max(0,min(rows-1.001,(y-y0)/(y1-y0)*(rows-1)))
        i,j=int(u),int(v);a,b=u-i,v-j
        return (hh[j*cols+i]*(1-a)+hh[j*cols+i+1]*a)*(1-b)+(hh[(j+1)*cols+i]*(1-a)+hh[(j+1)*cols+i+1]*a)*b
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
    MATERIALS[:]=list(bpy.data.materials)
    colors={m.name:i for i,m in enumerate(MATERIALS)}
    site_data=json.loads((data/'north-campus.json').read_text())
    if site_data.get('underpass'):
        from north_underpass import clip_source,road_height_sampler,upper_road_model
        passage=site_data['underpass']
        upper_deck=upper_road_model(passage,colors,road_height_sampler(bpy.data.objects['roads'],elevation))
        for name,mask in [('terrain','terrainMasks'),('roads','roadMasks')]:
            clip_source(bpy.data.objects[name],passage[mask],passage['bounds'],colors)
    surfaces=json.loads((data/'surfaces.json').read_text())
    masks=[]
    for s in surfaces:
        if s['id'] in site_data['replacedSurfaceIds']:
            xs,ys=zip(*s['vertices']);masks.append((min(xs)-2,min(ys)-2,max(xs)+2,max(ys)+2))
    source_sports=bpy.data.objects['其他运动场地']
    old_mesh=source_sports.data
    trimmed=Mesh();trimmed.v=[tuple(v.co) for v in old_mesh.vertices]
    kept_uvs=[];removed_sport_faces=0
    for p in old_mesh.polygons:
        cx,cy=p.center.x,p.center.y
        if any(x0<=cx<=x1 and y0<=cy<=y1 for x0,y0,x1,y1 in masks):
            removed_sport_faces+=1;continue
        trimmed.f.append(tuple(p.vertices));trimmed.m.append(colors[old_mesh.materials[p.material_index].name])
        kept_uvs.append([tuple(old_mesh.uv_layers.active.data[i].uv) for i in p.loop_indices])
    if removed_sport_faces:
        replacement=trimmed.object('north-sports-retained',source_sports.users_collection[0],dict(source_sports.items()))
        for p,uvs in zip(replacement.data.polygons,kept_uvs):
            for i,uv in zip(p.loop_indices,uvs):replacement.data.uv_layers.active.data[i].uv=uv
        name=source_sports.name;bpy.data.objects.remove(source_sports,do_unlink=True)
        if old_mesh.users==0:bpy.data.meshes.remove(old_mesh)
        replacement.name=name;source_sports=replacement
    trees=json.loads((data/'vegetation.json').read_text())
    tree_positions={tuple(t[:2]) for t in trees}
    removed_trees=[o for o in bpy.context.scene.objects if o.name.startswith('树木示意-') and (round(o.location.x,1),round(o.location.y,1)) not in tree_positions]
    for obj in removed_trees:bpy.data.objects.remove(obj,do_unlink=True)
    old=[o for o in bpy.context.scene.objects if o.get('northCampus') or str(o.get('featureId','')).startswith('north-campus/')]
    retained={o.name:(o.as_pointer(),o.data.as_pointer() if o.data else None) for o in bpy.context.scene.objects if o not in old}
    for obj in old:
        mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if mesh and mesh.users==0:bpy.data.meshes.remove(mesh)
    collection=bpy.data.collections.get('北校园 · 基础布局')
    if collection is None:
        collection=bpy.data.collections.new('北校园 · 基础布局');bpy.context.scene.collection.children.link(collection)
    temp_collection=bpy.data.collections.new('north-campus-export');bpy.context.scene.collection.children.link(temp_collection)
    groups=site_models(site_data,colors,elevation)
    if site_data.get('underpass'):groups['north-campus-roads'].extend(upper_deck)
    for key,mesh in groups.items():
        mesh.object(key,collection,{'northCampus':True,'layer':'sports' if key.endswith('sports') else 'roads'})
    for b in records:
        obj=building_model(b,colors,True).object(b['name'],collection,
              {'featureId':b['id'],'chunk':b['chunk'],'layer':'buildings','northCampus':True,'sourceUrl':b['sourceUrl'],'precision':b['facadeBasis']})
        compact_form_source(obj)
    with tempfile.TemporaryDirectory(prefix='gxu-north-campus-') as directory:
        temp=Path(directory);candidate=temp/'base.glb';candidate.write_bytes(before)
        def render(mesh,name,path,base,layer='buildings'):
            # Source objects have descriptive names; exports need stable names.
            source=bpy.data.objects.get(name)
            old_name=source.name if source else None
            if source:source.name=name+'-source'
            obj=mesh.object(name,temp_collection,{'layer':layer,'zone':name if name in keys else '', 'landmark':''})
            if base:
                export_north_base(obj,path)
            else:export(obj,path,base=False)
            block=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(block)
            if source:source.name=old_name
        manifest=json.loads((data/'models.json').read_text())
        sys.path.insert(0,str(ROOT/'scripts'))
        from vegetation_priorities import priority_positions
        manifest['treePriorityPositions']=priority_positions(json.loads((data/'vegetation-zones.json').read_text()),trees)
        for key in sorted(keys):
            low,high=Mesh(),Mesh()
            members=[b for b in buildings if b.get('chunk')==key]
            for b in members:
                for detail,target in [(False,low),(True,high)]:
                    mesh=building_model(b,colors,detail) if b.get('customModel')=='north-campus' else ordinary_building(b,elevation(*b['center']),colors,detail)
                    target.extend(mesh)
            render(low,key,temp/'far.glb',True)
            put_node((temp/'far.glb').read_bytes(),candidate,key)
            render(high,key,temp/(key+'.glb'),False)
            entry={'id':key,'url':f'models/{key}.glb','featureIds':[b['id'] for b in members],
                   'bounds':[min(b['bounds'][0] for b in members)-2,min(b['bounds'][1] for b in members)-2,
                             max(b['bounds'][2] for b in members)+2,max(b['bounds'][3] for b in members)+2]}
            manifest['zones']=[z for z in manifest['zones'] if z['id']!=key]+[entry]
        for key,mesh in groups.items():
            render(mesh,key,temp/'site.glb',True,'sports' if key.endswith('sports') else 'roads')
            put_node((temp/'site.glb').read_bytes(),candidate,key)
        if site_data.get('underpass'):
            # Retain established high-precision ground/road export contracts.
            from export_attributes import omit_unused_uvs,omit_zero_area_terrain_faces
            from update_south_gate import export_roads
            obj=bpy.data.objects['terrain']
            bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
            with omit_zero_area_terrain_faces(obj,position_quantization_bits=18),omit_unused_uvs(deduplicate_vertices=True):
                bpy.ops.export_scene.gltf(filepath=str(temp/'terrain.glb'),export_format='GLB',use_selection=True,export_extras=True,
                    export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
                    export_draco_position_quantization=18,export_draco_texcoord_quantization=18,
                    export_draco_normal_quantization=6,export_materials='EXPORT',export_cameras=False,export_lights=False)
            put_node((temp/'terrain.glb').read_bytes(),candidate,'terrain')
            export_roads(bpy.data.objects['roads'],temp/'roads.glb')
            put_node((temp/'roads.glb').read_bytes(),candidate,'roads')
        if removed_sport_faces:
            # Export the retained source directly, keeping its original UVs.
            name=source_sports.name;source_sports.name='sports'
            export(source_sports,temp/'retained-sports.glb',base=True)
            source_sports.name=name
            put_node((temp/'retained-sports.glb').read_bytes(),candidate,'sports')
        compact_static_accessors(candidate);compact_buffer_views(candidate)
        allowed=keys|set(groups)|({'sports'} if removed_sport_faces else set())
        if site_data.get('underpass'):allowed|={'terrain','roads'}
        sig_before,sig_after=signatures(before),signatures(candidate.read_bytes())
        for name,sig in sig_before.items():
            if name not in allowed:assert sig_after[name]==sig,name
        initial_bytes=candidate.stat().st_size+(models/'trees.glb').stat().st_size
        print('North campus initial bytes:',initial_bytes,flush=True)
        if initial_bytes>6_000_000:
            import shutil
            shutil.copy2(candidate,ROOT/'work/north-campus/underpass/candidate.glb')
        assert initial_bytes<=6_000_000,f'Initial model budget: {initial_bytes}'
        for entry in [manifest['base']]+[z for z in manifest['zones'] if z['id'] in keys]:
            target=models/Path(entry['url']).name;raw=(temp/target.name).read_bytes()
            target.write_bytes(raw);entry.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        manifest['zones'].sort(key=lambda z:z['id'])
        (data/'models.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    bpy.data.collections.remove(temp_collection)
    for name,pointers in retained.items():
        obj=bpy.data.objects[name]
        assert (obj.as_pointer(),obj.data.as_pointer() if obj.data else None)==pointers,name
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'),compress=True)
    for name,sha in original.items():
        if name!='base.glb' and name not in {k+'.glb' for k in keys}:
            assert hashlib.sha256((models/name).read_bytes()).hexdigest()==sha,name
    report={'buildingBlocks':len(records),'updatedChunks':sorted(keys),'siteNodes':sorted(groups),
            'retainedSourceObjects':len(retained),'retainedBaseNodes':len(sig_before.keys()-allowed),
            'initialBytes':initial_bytes,'unchangedOtherModelFiles':True,'sourceObjectsPreserved':True,
            'removedSourceTrees':len(removed_trees),'remainingTrees':len(trees),
            'removedSupersededSportFaces':removed_sport_faces,
            'precision':'影像轮廓与照片约束精修；尺寸、未见面及当代外观变化仍待核实'}
    (ROOT/'docs/model-checks/north-campus-model.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
