"""Independent fixtures for bounded export-only terrain retriangulation."""
import sys
from pathlib import Path
import unittest

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from terrain_planar import planar_terrain_candidate, read_mesh, simplify_mesh_arrays


def grid(*, hole=False, bump=False, seam=False, materials=False):
    xyz = [(x, y, .02*x + .01*y + (.25 if bump and x == 2 and y == 2 else 0))
           for y in range(5) for x in range(5)]
    faces = []
    for y in range(4):
        for x in range(4):
            if hole and x == 1 and y == 1:
                continue
            a = y*5+x
            faces.extend([(a, a+1, a+6), (a, a+6, a+5)])
    mesh = bpy.data.meshes.new('fixture')
    mesh.from_pydata(xyz, [], faces)
    uv = mesh.uv_layers.new()
    for poly in mesh.polygons:
        if materials:
            poly.material_index = int(poly.center.x > 2)
        for loop in poly.loop_indices:
            p = mesh.vertices[mesh.loops[loop].vertex_index].co
            uv.data[loop].uv = (p.x/4 + (1 if seam and poly.index < 2 else 0), p.y/4)
    obj = bpy.data.objects.new('terrain', mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj['layer'] = 'terrain'
    return obj


def projected_area(data):
    p = data['vertices'][data['triangles']]
    return np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0])[:, 2].sum()/2


def faces_with_attributes(data):
    result = []
    for ids, uv, normal, material in zip(data['triangles'], data['uvs'], data['normals'], data['materials']):
        corners = [(tuple(data['vertices'][i]), tuple(u), tuple(n)) for i, u, n in zip(ids, uv, normal)]
        result.append((int(material), min(tuple(corners[k:]+corners[:k]) for k in range(3))))
    return result


class TerrainPlanarTest(unittest.TestCase):
    def test_plane_area_boundary_and_subset(self):
        obj = grid()
        old = read_mesh(obj.data)
        new, report = simplify_mesh_arrays(old)
        self.assertGreater(report['removedFaces'], 0)
        self.assertAlmostEqual(projected_area(new), 16, places=10)
        used = {tuple(p) for p in new['vertices'][new['triangles']].reshape(-1, 3)}
        self.assertLessEqual(used, {tuple(p) for p in old['vertices']})
        self.assertTrue(all(tuple(p) in used for p in old['vertices'] if p[0] in (0, 4) or p[1] in (0, 4)))

    def test_hole_stays_open(self):
        old = read_mesh(grid(hole=True).data)
        new, report = simplify_mesh_arrays(old)
        self.assertGreater(report['removedFaces'], 0)
        self.assertAlmostEqual(projected_area(new), 15, places=10)
        # A point strictly inside the removed cell must not be inside any face.
        for triangle in new['vertices'][new['triangles']]:
            p = triangle[:, :2]
            ab, ac = p[1]-p[0], p[2]-p[0]
            u, v = np.linalg.solve(np.column_stack((ab, ac)), np.array([1.37, 1.63])-p[0])
            self.assertFalse(u > 0 and v > 0 and u+v < 1)

    def test_bump_faces_not_flattened(self):
        old = read_mesh(grid(bump=True).data)
        new, _ = simplify_mesh_arrays(old)
        keys = set(faces_with_attributes(new))
        for key in faces_with_attributes(old):
            if any(p[0][:2] == (2, 2) for p in key[1]):
                self.assertIn(key, keys)

    def test_non_affine_uv_preserved(self):
        old = read_mesh(grid(seam=True).data)
        new, _ = simplify_mesh_arrays(old)
        keys = set(faces_with_attributes(new))
        for key in faces_with_attributes(old)[:2]:
            self.assertIn(key, keys)

    def test_material_partition_preserved(self):
        obj = grid()
        obj.data.materials.append(bpy.data.materials.new('left'))
        obj.data.materials.append(bpy.data.materials.new('right'))
        for face in obj.data.polygons:
            face.material_index = int(face.center.x > 2)
        old = read_mesh(obj.data)
        new, _ = simplify_mesh_arrays(old)
        for material in (0, 1):
            subset = {**new, 'triangles': new['triangles'][new['materials'] == material]}
            self.assertAlmostEqual(projected_area(subset), 8, places=10)

    def test_context_restores_after_exception(self):
        obj = grid()
        source, count = obj.data, len(bpy.data.meshes)
        with self.assertRaisesRegex(RuntimeError, 'export failed'):
            with planar_terrain_candidate(obj) as report:
                self.assertIsNot(obj.data, source)
                self.assertGreater(report['removedFaces'], 0)
                raise RuntimeError('export failed')
        self.assertIs(obj.data, source)
        self.assertEqual(len(bpy.data.meshes), count)

    def test_unknown_attribute_rejected(self):
        obj = grid()
        obj.data.attributes.new('custom_weights', 'FLOAT', 'POINT')
        with self.assertRaisesRegex(ValueError, 'Unsupported terrain attributes'):
            with planar_terrain_candidate(obj):
                self.fail('Should not discard unknown attribute')


unittest.main(argv=[__file__])
