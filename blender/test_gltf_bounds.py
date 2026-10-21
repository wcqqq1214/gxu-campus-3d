"""Typed bounds remain bit-identical, including subnormals and signed zero."""
import copy,json,random,struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from gltf_bounds import compact_float_bounds,compact_glb_float_bounds
from preserve_glb_geometry import unpack
class FloatBoundsTests(unittest.TestCase):
 def test_float32_roundtrip_and_integer_bounds(self):
  rng=random.Random(42)
  values=[-0.,0.,-1234.5677490234375,1.401298464324817e-45,3.4028234663852886e38]
  values += [struct.unpack('<f',struct.pack('<I',rng.randrange(0x7f800000)))[0] for _ in range(2000)]
  d={'accessors':[{'componentType':5126,'min':values.copy(),'max':[-v for v in values]}, {'componentType':5125,'min':[0],'max':[4294967295]}]};before=copy.deepcopy(d)
  compact_float_bounds(d)
  for key in ('min','max'):
   self.assertEqual([struct.pack('<f',v) for v in before['accessors'][0][key]],[struct.pack('<f',v) for v in d['accessors'][0][key]])
  self.assertEqual(before['accessors'][1],d['accessors'][1]);self.assertLess(len(json.dumps(d)),len(json.dumps(before)))
  again=copy.deepcopy(d);compact_float_bounds(again);self.assertEqual(again,d)
 def test_binary_payload_unchanged(self):
  d={'asset':{'version':'2.0'},'accessors':[{'componentType':5126,'min':[-1234.5677490234375],'max':[1234.5677490234375]}]}
  header=json.dumps(d).encode();header+=b' '*(-len(header)%4);binary=b'compressed-mesh\x00\x00'
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'model.glb';p.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(header)+len(binary))+struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
   self.assertGreater(compact_glb_float_bounds(p),0);self.assertEqual(unpack(p.read_bytes())[1],binary)
if __name__=='__main__':
 if not unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FloatBoundsTests)).wasSuccessful():raise SystemExit(1)
