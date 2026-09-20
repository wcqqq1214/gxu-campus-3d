import copy
import math
import unittest

from explicit_roof_data import resolve_roof_mesh
from building_overrides import resolve_parts


class ExplicitRoofTests(unittest.TestCase):
    def fixture(self):
        poly = [[[[0, 0], [12, 0], [12, 8], [0, 8], [0, 0]]]]
        mesh = {'vertices': [[0,0,0],[12,0,0],[12,8,0],[0,8,0],[4,4,2],[8,4,2]],
                'triangles': [0,1,5,0,5,4,1,2,5,2,3,4,2,4,5,3,0,4]}
        return poly, mesh

    def test_continuous_roof_rotation_winding_and_input_preservation(self):
        poly, mesh = self.fixture()
        before = copy.deepcopy(mesh)
        for angle in (0, .67):
            transform = lambda p: [p[0]*math.cos(angle)-p[1]*math.sin(angle), p[0]*math.sin(angle)+p[1]*math.cos(angle)]
            rotated = {'vertices':[transform(v)+v[2:] for v in mesh['vertices']],
                       'triangles':list(reversed(mesh['triangles']))}
            result = resolve_roof_mesh([[list(map(transform,poly[0][0]))]], rotated, 2)
            self.assertEqual(len(result['triangles']),18)
        self.assertEqual(mesh,before)

    def test_rejects_gap_overlap_bad_index_and_elevated_eave(self):
        poly, mesh = self.fixture()
        variants=[]
        gap=copy.deepcopy(mesh);gap['triangles']=gap['triangles'][:-3];variants.append(gap)
        overlap=copy.deepcopy(mesh);overlap['triangles']+=overlap['triangles'][:3];variants.append(overlap)
        invalid=copy.deepcopy(mesh);invalid['triangles'][0]=True;variants.append(invalid)
        high=copy.deepcopy(mesh);high['vertices'][0][2]=.2;variants.append(high)
        for candidate in variants:
            with self.subTest(candidate=candidate),self.assertRaises(ValueError):
                resolve_roof_mesh(poly,candidate,2)

    def test_rejects_courtyard_fill_and_discontinuous_duplicate_vertex(self):
        poly, mesh = self.fixture()
        poly[0].append([[5,3],[7,3],[7,5],[5,5],[5,3]])
        with self.assertRaisesRegex(ValueError,'tile'):resolve_roof_mesh(poly,mesh,2)
        poly,mesh=self.fixture();mesh['vertices'].append([4,4,1]);mesh['triangles'][5]=6
        with self.assertRaisesRegex(ValueError,'duplicate'):resolve_roof_mesh(poly,mesh,2)

    def test_part_resolution_uses_mesh_and_rejects_flat_mesh(self):
        poly, mesh = self.fixture()
        part=dict(id='roof',polygons=poly,height=10,levels=3,roof=dict(type='hipped',rise=2,mesh=mesh))
        b={'polygons':poly,'height':10}
        result=resolve_parts(b,[part],dict(type='flat',rise=0))
        self.assertEqual(result[0]['roof']['geometry'],mesh)
        self.assertNotIn('mesh',result[0]['roof'])
        part['roof'].update(type='flat',rise=0)
        with self.assertRaisesRegex(ValueError,'pitched'):resolve_parts(b,[part],dict(type='flat',rise=0))

    def test_rejects_unjoined_ridge_edge_despite_complete_projection(self):
        poly,mesh=self.fixture()
        mesh['vertices'].append([6,4,2])
        mesh['triangles'][3:6]=[0,5,6,0,6,4]
        with self.assertRaisesRegex(ValueError,'unjoined interior edge'):
            resolve_roof_mesh(poly,mesh,2)
