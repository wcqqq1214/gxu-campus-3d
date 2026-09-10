"""Retain a published procedural node during an unrelated bounded base rebuild.

Only compressed geometry and accessor metadata are copied. Materials, layers and
scene structure stay in the new export; no decode/re-encode loses precision.
"""
import json,struct,copy

def unpack(raw):
    size=struct.unpack_from('<I',raw,12)[0]
    return json.loads(raw[20:20+size]),raw[28+size:]

def preserve_geometry(previous,path,names):
    old,oldbin=unpack(previous);new,newbin=unpack(path.read_bytes());binary=bytearray(newbin)
    for name in names:
        a=next(n for n in old['nodes'] if n.get('name')==name);b=next(n for n in new['nodes'] if n.get('name')==name)
        before=old['meshes'][a['mesh']]['primitives'];after=new['meshes'][b['mesh']]['primitives']
        assert len(before)==len(after)
        for p,q in zip(before,after):
            assert old['materials'][p['material']]['name']==new['materials'][q['material']]['name']
            ext=copy.deepcopy(p['extensions']['KHR_draco_mesh_compression']);view=old['bufferViews'][ext['bufferView']];offset=view.get('byteOffset',0);blob=oldbin[offset:offset+view['byteLength']]
            current=new['bufferViews'][q['extensions']['KHR_draco_mesh_compression']['bufferView']];start=current.get('byteOffset',0)
            if blob==binary[start:start+current['byteLength']]:continue
            binary.extend(b'\0'*((-len(binary))%4));ext['bufferView']=len(new['bufferViews'])
            new['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':len(blob)})
            binary.extend(blob);q['extensions']['KHR_draco_mesh_compression']=ext
            for attr,index in p['attributes'].items():
                metadata=copy.deepcopy(old['accessors'][index]);assert 'bufferView' not in metadata
                new['accessors'][q['attributes'][attr]]=metadata
            if 'indices' in p:
                metadata=copy.deepcopy(old['accessors'][p['indices']]);assert 'bufferView' not in metadata
                new['accessors'][q['indices']]=metadata
    binary.extend(b'\0'*((-len(binary))%4));new['buffers'][0]['byteLength']=len(binary)
    header=json.dumps(new,separators=(',',':')).encode();header+=b' '*((-len(header))%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(header)+len(binary))+struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
