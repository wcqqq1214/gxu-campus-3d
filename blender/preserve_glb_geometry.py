"""Retain a published procedural node during an unrelated bounded base rebuild.

Only compressed geometry and accessor metadata are copied. Materials, layers and
scene structure stay in the new export; no decode/re-encode loses precision.
"""
import json,struct,copy,re,shutil,subprocess

def mesh_nodes_by_name(doc):
    """Full exports coexist with source objects and acquire Blender suffixes.

    Base-only exports do not. Resolve that naming difference without silently
    accepting two meshes for the same logical object.
    """
    result={}
    for node in doc['nodes']:
        if 'mesh' not in node:continue
        name=re.sub(r'\.\d{3,}$','',node['name'])
        if name in result:raise ValueError(f'Ambiguous logical GLB node: {name}')
        result[name]=node
    return result

def unpack(raw):
    size=struct.unpack_from('<I',raw,12)[0]
    return json.loads(raw[20:20+size]),raw[28+size:]

def compact_buffer_views(path, *, optimize_jpegs=False):
    """Pack live views, sharing exact duplicates without decoding geometry.

    Optional jpegtran Huffman optimization preserves DCT coefficients and all
    metadata markers. Only views exclusively referenced by JPEG images qualify.
    All processing finishes before the original file is overwritten.
    """
    doc,binary=unpack(path.read_bytes())
    if len(doc['buffers'])!=1 or doc['buffers'][0].get('uri'):
        raise ValueError('Expected one internal GLB buffer')
    references=[]
    def collect(value):
        if isinstance(value,dict):
            for key,child in value.items():
                if key=='bufferView' and type(child) is int:references.append((value,key,child))
                else:collect(child)
        elif isinstance(value,list):
            for child in value:collect(child)
    collect(doc);used=sorted({index for _,_,index in references})
    if any(index<0 or index>=len(doc['bufferViews']) for index in used):raise ValueError('Invalid buffer view reference')
    jpeg_images={id(item) for item in doc.get('images',[]) if item.get('mimeType')=='image/jpeg'}
    jpeg_views={index for index in used if all(id(parent) in jpeg_images for parent,_,ref in references if ref==index)} if optimize_jpegs else set()
    encoder=shutil.which('jpegtran') if jpeg_views else None
    if jpeg_views and not encoder:raise RuntimeError('JPEG optimization requires jpegtran (libjpeg-turbo) on PATH')
    packed=bytearray();views=[];remap={};shared={}
    for index in used:
        view=copy.deepcopy(doc['bufferViews'][index])
        if view['buffer']!=0:raise ValueError('Unexpected external buffer view')
        start=view.get('byteOffset',0);end=start+view['byteLength']
        if start<0 or end<start or end>len(binary):raise ValueError('Buffer view exceeds binary payload')
        payload=binary[start:end]
        if index in jpeg_views:
            candidate=subprocess.run([encoder,'-copy','all','-optimize','-strict'],input=payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
            if len(candidate)<len(payload):payload=candidate
        view['byteLength']=len(payload)
        metadata={key:value for key,value in view.items() if key!='byteOffset'}
        signature=(json.dumps(metadata,sort_keys=True,separators=(',',':')),payload)
        if signature in shared:
            remap[index]=shared[signature];continue
        packed.extend(b'\0'*(-len(packed)%4));view['byteOffset']=len(packed)
        packed.extend(payload);remap[index]=len(views);shared[signature]=len(views);views.append(view)
    for parent,key,index in references:parent[key]=remap[index]
    doc['bufferViews']=views;packed.extend(b'\0'*(-len(packed)%4));doc['buffers'][0]['byteLength']=len(packed)
    header=json.dumps(doc,separators=(',',':')).encode();header+=b' '*(-len(header)%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(header)+len(packed))+struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(packed),b'BIN\0')+packed)

def preserve_geometry(previous,path,names,materials=None):
    old,oldbin=unpack(previous);new,newbin=unpack(path.read_bytes());binary=bytearray(newbin)
    old_nodes=mesh_nodes_by_name(old);new_nodes=mesh_nodes_by_name(new)
    for name in names:
        a=old_nodes[name];b=new_nodes[name]
        before=old['meshes'][a['mesh']]['primitives'];after=new['meshes'][b['mesh']]['primitives']
        assert len(before)==len(after)
        for p,q in zip(before,after):
            assert old['materials'][p['material']]['name']==new['materials'][q['material']]['name']
            if materials is not None and old['materials'][p['material']]['name'] not in materials:continue
            ext=copy.deepcopy(p['extensions']['KHR_draco_mesh_compression']);view=old['bufferViews'][ext['bufferView']];offset=view.get('byteOffset',0);blob=oldbin[offset:offset+view['byteLength']]
            current=new['bufferViews'][q['extensions']['KHR_draco_mesh_compression']['bufferView']];start=current.get('byteOffset',0)
            if blob==binary[start:start+current['byteLength']]:continue
            binary.extend(b'\0'*((-len(binary))%4));ext['bufferView']=len(new['bufferViews'])
            new['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':len(blob)})
            binary.extend(blob);q['extensions']['KHR_draco_mesh_compression']=ext
            restored_attributes={}
            for attr,index in p['attributes'].items():
                metadata=copy.deepcopy(old['accessors'][index]);assert 'bufferView' not in metadata
                target=q['attributes'].get(attr)
                if target is None:
                    target=len(new['accessors']);new['accessors'].append(metadata)
                else:new['accessors'][target]=metadata
                restored_attributes[attr]=target
            q['attributes']=restored_attributes
            if 'indices' in p:
                metadata=copy.deepcopy(old['accessors'][p['indices']]);assert 'bufferView' not in metadata
                new['accessors'][q['indices']]=metadata
    binary.extend(b'\0'*((-len(binary))%4));new['buffers'][0]['byteLength']=len(binary)
    header=json.dumps(new,separators=(',',':')).encode();header+=b' '*((-len(header))%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(header)+len(binary))+struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
