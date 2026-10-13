import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'blender'))
from terrain_precision_config import load_precision_regions


class TerrainPrecisionConfigTests(unittest.TestCase):
    def test_optional_config_and_valid_regions(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.assertEqual(load_precision_regions(root),[])
            (root/'data').mkdir();path=root/'data/terrain-export-regions.json'
            path.write_text(json.dumps({'schemaVersion':1,'regions':[{'id':'edge','bounds':[-2,0,4,8]}]}))
            self.assertEqual(load_precision_regions(root),[[-2,0,4,8]])

    def test_invalid_bounds_ids_and_schema_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data').mkdir();path=root/'data/terrain-export-regions.json'
            valid={'id':'edge','bounds':[-2,0,4,8]}
            invalid=[{'schemaVersion':2,'regions':[]}, {'schemaVersion':1,'regions':[valid,valid]},
                     {'schemaVersion':1,'regions':[{'id':'','bounds':[0,0,1,1]}]}]
            invalid += [{'schemaVersion':1,'regions':[{'id':'edge','bounds':b}]} for b in
                        [[0,0,0,1],[0,0,1],[0,0,True,1],[0,0,float('nan'),1]]]
            for value in invalid:
                path.write_text(json.dumps(value))
                with self.subTest(value=value),self.assertRaises(ValueError):load_precision_regions(root)
