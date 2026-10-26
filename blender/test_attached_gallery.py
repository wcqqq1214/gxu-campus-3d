"""Source-mesh gallery regression; run in Blender with --factory-startup.

The retained fifth-teaching-building data supplies two real, wing-bounded bays.
No saved .blend or exported model is required. Negative controls alter the
generated faces, then use the same BVH checks as the positive regressions.
"""
import copy
import json
import math
import sys
import unittest
from collections import Counter
from pathlib import Path

from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from generic_buildings import ordinary_building
from gallery_checks import check_galleries

COLORS = {name: i for i, name in enumerate([
    'stone', 'pink', 'white', 'glass', 'dark', 'shadeGlass', 'paleRoof', 'red'])}
TOLERANCE = 1e-4
ANGLES = (0, math.pi / 2, math.pi * .173)


def building_fixture(angle=0):
    building = next(b for b in json.loads((ROOT / 'public/data/buildings.json').read_text())
                    if b['id'] == 'way/759129515')
    c, s = math.cos(angle), math.sin(angle)

    def rotate(point):
        return [point[0] * c - point[1] * s, point[0] * s + point[1] * c] + list(point[2:])

    def polygons(items):
        return [[[rotate(point) for point in ring] for ring in poly] for poly in items]

    building['polygons'] = polygons(building['polygons'])
    for part in building['form']['parts']:
        part['polygons'] = polygons(part['polygons'])
        if 'parapetEdges' in part:
            part['parapetEdges'] = [[rotate(point) for point in edge] for edge in part['parapetEdges']]
        if 'geometry' in part['roof']:
            roof = part['roof']['geometry']
            roof['vertices'] = [rotate(point) for point in roof['vertices']]
            if 'boundaryWalls' in roof:
                roof['boundaryWalls'] = [[rotate(point) for point in face] for face in roof['boundaryWalls']]
    # Entrance platforms have separate contracts; their unrelated geometry must
    # not mask a missing gallery slab in these facade probes.
    building['form']['entrances'] = []
    for facade in building['form']['facades']:
        for key in ('start', 'end', 'normal'):
            facade[key] = rotate(facade[key])
    return building


def gallery_facades(building):
    return [f for f in building['form']['facades'] if 'attachedGallery' in f]


def frame(facade, z=0):
    a = Vector((*facade['start'], z))
    edge = Vector((*facade['end'], z)) - a
    u = edge.normalized()
    n = Vector((*facade['normal'], 0))

    def point(t, depth, height):
        return tuple(a + u * t + n * depth + Vector((0, 0, height)))

    def local(vertex):
        delta = Vector(vertex) - a
        return delta.dot(u), delta.dot(n), delta.z

    return edge.length, point, local


def check_mesh(building, mesh, z=0):
    return check_galleries(building, [BVHTree.FromPolygons(mesh.v, mesh.f)], TOLERANCE, z)


def require_single_slab_front(building, mesh, z=0):
    """Reject coincident stone wall and white slab front faces (z-fighting)."""
    for facade in gallery_facades(building):
        length, point, _ = frame(facade, z)
        p = facade['attachedGallery']
        origin = Vector(point(length * .37, p['depth'] + .3,
                              p['floorHeight'] - p['slabThickness'] / 2))
        direction = -Vector((*facade['normal'], 0))
        hits = 0
        for face in mesh.f:
            vertices = [Vector(mesh.v[index]) for index in face]
            for i in range(1, len(vertices) - 1):
                hit = intersect_ray_tri(vertices[0], vertices[i], vertices[i + 1],
                                        direction, origin, True)
                if hit is not None and abs((hit - origin).length - .3) <= TOLERANCE:
                    hits += 1
                    break
        assert hits == 1, ('coplanar wall/slab front', facade['edge'], hits)


def defective_mesh(mesh, facade, defect, z=0):
    """Inject real geometric faults; never replace BVH/ray or check results."""
    broken = copy.deepcopy(mesh)
    length, point, local = frame(facade, z)
    p = facade['attachedGallery']
    lo, hi = p['endInset'], length - p['endInset']
    depth, floor = p['depth'], p['floorHeight']

    def face_at(points):
        broken.face([point(*v) for v in points], COLORS['white'])

    def remove_faces(predicate):
        retained = [(face, mat) for face, mat in zip(broken.f, broken.m)
                    if not predicate([local(broken.v[index]) for index in face])]
        assert len(retained) < len(broken.f), ('mutation removed no geometry', defect)
        broken.f = [face for face, _ in retained]
        broken.m = [mat for _, mat in retained]

    def inside_bay(vertices):
        return all(lo - .02 <= t <= hi + .02 and -.001 <= d <= depth + .001
                   for t, d, _ in vertices)

    if defect == 'closed-upper-gallery':
        face_at([(lo, depth, floor + 1), (hi, depth, floor + 1),
                 (hi, depth, facade['height'] - .5), (lo, depth, facade['height'] - .5)])
    elif defect == 'missing-deck':
        remove_faces(lambda vertices: inside_bay(vertices) and any(
            all(abs(h - expected) < TOLERANCE for _, _, h in vertices)
            for expected in (floor, floor - p['slabThickness'])))
    elif defect == 'filled-baluster-gaps':
        face_at([(lo, depth - .08, floor + .12), (hi, depth - .08, floor + .12),
                 (hi, depth - .08, floor + p['railHeight'] - .1),
                 (lo, depth - .08, floor + p['railHeight'] - .1)])
    elif defect == 'flat-soffit':
        # Move only the sloped underside. The original top roof remains, so a
        # generic silhouette check alone would accept this fault.
        soffit = facade['height'] - p['slabThickness']
        remove_faces(lambda vertices: inside_bay(vertices) and all(
            abs(h - (soffit - p['roofDrop'] * d / depth)) < TOLERANCE
            for _, d, h in vertices))
        face_at([(lo, 0, soffit), (hi, 0, soffit),
                 (hi, depth, soffit), (lo, depth, soffit)])
    elif defect == 'roof-wing-gap':
        for height in (facade['height'], facade['height'] - p['slabThickness']):
            remove_faces(lambda vertices: inside_bay(vertices) and all(
                abs(h - (height - p['roofDrop'] * d / depth)) < TOLERANCE
                for _, d, h in vertices))
            face_at([(lo + .12, 0, height), (hi - .12, 0, height),
                     (hi - .12, depth, height - p['roofDrop']),
                     (lo + .12, depth, height - p['roofDrop'])])
    elif defect == 'missing-lower-front-wall':
        remove_faces(lambda vertices: inside_bay(vertices) and all(
            abs(d - depth) < TOLERANCE and h <= floor - p['slabThickness'] + TOLERANCE
            for _, d, h in vertices))
    elif defect == 'missing-upper-opening':
        opening = p['upperOpenings'][0]
        center = opening['t'] * length
        remove_faces(lambda vertices: all(
            abs(t - center) <= opening['width'] / 2 + .071 and .009 <= d <= .211
            and opening['bottom'] - TOLERANCE <= h <= opening['top'] + TOLERANCE
            for t, d, h in vertices))
    elif defect == 'legacy-rear-window':
        face_at([(length / 2 - .5, .1, 1), (length / 2 + .5, .1, 1),
                 (length / 2 + .5, .1, 2.8), (length / 2 - .5, .1, 2.8)])
    elif defect == 'overlapping-slab-front':
        face_at([(lo, depth, floor - p['slabThickness']),
                 (hi, depth, floor - p['slabThickness']),
                 (hi, depth, floor), (lo, depth, floor)])
    else:
        raise ValueError(defect)
    assert broken.v != mesh.v or broken.f != mesh.f, ('mutation did not change mesh', defect)
    return broken


class AttachedGalleryGeometryTests(unittest.TestCase):
    def test_real_galleries_remain_open_and_solid_in_both_lods(self):
        for angle in ANGLES:
            building = building_fixture(angle)
            for detail in (False, True):
                with self.subTest(angle=angle, detail=detail):
                    mesh = ordinary_building(building, building['elevation'], COLORS, detail)
                    report = check_mesh(building, mesh, building['elevation'])
                    self.assertTrue(report['passed'])
                    self.assertEqual(Counter(sample['kind'] for sample in report['samples']), {
                        'upper-gallery-void': 8, 'gallery-deck': 8,
                        'sloping-gallery-soffit': 8, 'lower-gallery-solid': 8,
                        'gallery-roof-wing-join': 4, 'front-baluster': 6,
                        'upper-window': 4, 'upper-door': 2, 'rear-lower-wall': 2,
                    })

    def test_slab_front_has_one_surface_in_both_lods(self):
        for angle in ANGLES:
            building = building_fixture(angle)
            for detail in (False, True):
                with self.subTest(angle=angle, detail=detail):
                    mesh = ordinary_building(building, 0, COLORS, detail)
                    require_single_slab_front(building, mesh)

    def test_gallery_body_is_identical_between_lods(self):
        for angle in ANGLES:
            building = building_fixture(angle)
            meshes = [ordinary_building(building, 0, COLORS, detail) for detail in (False, True)]

            def body(mesh):
                _, start, end = next(part for part in mesh.parts if part[0] == '01_主体轮廓')
                faces = [tuple(index - start for index in face) for face in mesh.f
                         if all(start <= index < end for index in face)]
                return mesh.v[start:end], faces

            with self.subTest(angle=angle):
                self.assertEqual(body(meshes[0]), body(meshes[1]))

    def test_real_mesh_faults_are_rejected_by_retained_bvh_checks(self):
        defects = {
            'closed-upper-gallery': 'closed upper gallery',
            'missing-deck': 'gallery-deck',
            'filled-baluster-gaps': 'filled front baluster gap',
            'flat-soffit': 'sloping-gallery-soffit',
            'roof-wing-gap': 'gallery-roof-wing-join',
            'missing-lower-front-wall': 'lower-gallery-solid',
            'missing-upper-opening': 'upper-window',
            'legacy-rear-window': 'rear-lower-wall',
        }
        for angle in ANGLES:
            building = building_fixture(angle)
            for detail in (False, True):
                mesh = ordinary_building(building, 0, COLORS, detail)
                check_mesh(building, mesh)
                for defect, reason in defects.items():
                    with self.subTest(angle=angle, detail=detail, defect=defect):
                        broken = defective_mesh(mesh, gallery_facades(building)[0], defect)
                        with self.assertRaisesRegex(AssertionError, reason):
                            check_mesh(building, broken)

    def test_overlapping_slab_front_is_rejected(self):
        building = building_fixture()
        mesh = ordinary_building(building, 0, COLORS, False)
        require_single_slab_front(building, mesh)
        broken = defective_mesh(mesh, gallery_facades(building)[0], 'overlapping-slab-front')
        with self.assertRaisesRegex(AssertionError, 'coplanar wall/slab front'):
            require_single_slab_front(building, broken)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
