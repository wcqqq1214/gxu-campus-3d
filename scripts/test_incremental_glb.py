"""Full-source and base-only exports must preserve the same logical GLB node."""
import copy,json,struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'blender'))
from preserve_glb_geometry import mesh_nodes_by_name,preserve_geometry,unpack,compact_buffer_views

class IncrementalGLBTests(unittest.TestCase):
    def encode(self,name,payload,count):
        doc={'asset':{'version':'2.0'},'nodes':[{'name':name,'mesh':0}],
             'meshes':[{'primitives':[{'material':0,'attributes':{'POSITION':0},'indices':1,
                'extensions':{'KHR_draco_mesh_compression':{'bufferView':0,'attributes':{'POSITION':0}}}}]}],
             'materials':[{'name':'stone'}],'accessors':[{'componentType':5126,'count':count,'type':'VEC3','min':[0,0,0],'max':[1,1,1]},
                {'componentType':5123,'count':count,'type':'SCALAR'}],
             'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(payload)}],'buffers':[{'byteLength':len(payload)}]}
        b=json.dumps(doc).encode();b+=b' '*(-len(b)%4);payload+=b'\0'*(-len(payload)%4)
        return struct.pack('<4sII',b'glTF',2,28+len(b)+len(payload))+struct.pack('<I4s',len(b),b'JSON')+b+struct.pack('<I4s',len(payload),b'BIN\0')+payload

    def test_preserve_geometry_from_suffixed_full_export_to_base_only(self):
        old=self.encode('shore-jinghu.001',b'old-payload!',6)
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'base.glb';p.write_bytes(self.encode('shore-jinghu',b'new-payload!',9))
            preserve_geometry(old,p,['shore-jinghu'])
            doc,buf=unpack(p.read_bytes());primitive=doc['meshes'][0]['primitives'][0]
            view=doc['bufferViews'][primitive['extensions']['KHR_draco_mesh_compression']['bufferView']]
            self.assertEqual(buf[view['byteOffset']:view['byteOffset']+view['byteLength']],b'old-payload!')
            self.assertEqual(doc['accessors'][0]['count'],6)
            self.assertEqual(doc['accessors'][1]['count'],6)
            self.assertEqual(doc['nodes'][0]['name'],'shore-jinghu')

    def test_ambiguous_suffixes_rejected_without_changing_real_names(self):
        self.assertEqual(list(mesh_nodes_by_name({'nodes':[{'name':'bank.v2','mesh':0},{'name':'bank.001'}]})),['bank.v2'])
        with self.assertRaisesRegex(ValueError,'Ambiguous'):
            mesh_nodes_by_name({'nodes':[{'name':'terrain','mesh':0},{'name':'terrain.001','mesh':1}]})

    def test_preserved_payload_restores_its_original_attribute_set(self):
        # A plain-material export can omit UVs; restoring an older Draco node
        # must restore that payload's accessor map as well as its bytes.
        old_doc,buf=unpack(self.encode('sculpture',b'original-payload',6))
        old_doc['accessors'].append({'componentType':5126,'count':6,'type':'VEC2'})
        prim=old_doc['meshes'][0]['primitives'][0]
        prim['attributes']['TEXCOORD_0']=2
        prim['extensions']['KHR_draco_mesh_compression']['attributes']['TEXCOORD_0']=1
        header=json.dumps(old_doc).encode();header+=b' '*(-len(header)%4)
        old=struct.pack('<4sII',b'glTF',2,28+len(header)+len(buf))+struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(buf),b'BIN\0')+buf
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'base.glb'
            path.write_bytes(self.encode('sculpture',b'new-no-uv-payload',9))
            preserve_geometry(old,path,['sculpture'])
            doc,_=unpack(path.read_bytes());p=doc['meshes'][0]['primitives'][0]
            self.assertEqual(set(p['attributes']),{'POSITION','TEXCOORD_0'})
            self.assertEqual(doc['accessors'][p['attributes']['TEXCOORD_0']],old_doc['accessors'][2])
            self.assertEqual(p['extensions']['KHR_draco_mesh_compression']['attributes'],prim['extensions']['KHR_draco_mesh_compression']['attributes'])

    def test_compaction_retains_geometry_and_embedded_image_after_swap(self):
        old=self.encode('terrain',b'precise-geometry',6)
        doc,buf=unpack(self.encode('terrain',b'obsolete-payload',9))
        offset=len(buf);buf+=b'image-content'
        doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':13})
        doc['images']=[{'mimeType':'image/png','bufferView':1}]
        header=json.dumps(doc).encode();header+=b' '*(-len(header)%4);buf+=b'\0'*(-len(buf)%4)
        raw=struct.pack('<4sII',b'glTF',2,28+len(header)+len(buf))+struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(buf),b'BIN\0')+buf
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'base.glb';p.write_bytes(raw);preserve_geometry(old,p,['terrain'])
            compact_buffer_views(p);result,binary=unpack(p.read_bytes())
            def payload(index):
                view=result['bufferViews'][index];at=view['byteOffset'];return binary[at:at+view['byteLength']]
            primitive=result['meshes'][0]['primitives'][0]
            self.assertEqual(payload(primitive['extensions']['KHR_draco_mesh_compression']['bufferView']),b'precise-geometry')
            self.assertEqual(payload(result['images'][0]['bufferView']),b'image-content')
            self.assertNotIn(b'obsolete-payload',binary)
            self.assertEqual(len(result['bufferViews']),2)
            self.assertEqual(result['accessors'][0]['count'],6)

if __name__=='__main__':unittest.main()
