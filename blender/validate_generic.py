"""Verify campus building geometry in both LODs, saved source and shipping GLBs.

--generated-only checks generators before rebuilding. The default also checks
real source vertex groups and ray samples in base and every near chunk.
"""

import json
import math
import re
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'blender'), str(ROOT / 'scripts')]
from building_models import building_mesh
from campus_offices import IDS as OFFICE_IDS
from college_facades import BUILDERS as COLLEGE_FACADES
from dining_halls import BEI, BI, BO, CUI, DONG, FRONTS, XIU
from generic_buildings import COLLEGE_MODELS, compact_form_source
from geometry import MATERIALS
from humanities_facades import GATE, MANAGEMENT, SHAW, YULIN
from nanyuan import CANTEEN_ID
from new_east_neighbours import BUILDING_IDS as NEW_EAST_NEIGHBOURS
from new_east_neighbours import SHOP_BUILDINGS
from student_residences import IDS as RESIDENCE_IDS
from student_residences import chunk_id as residence_chunk_id
from student_water_tower import TOWER_ID
from terrain_elevation import make_elevation
from west_dorms import FINISHES


def ordinary(b):
    return (
        not b['landmark']
        and not b.get('customModel')
        and b['id'] != 'way/948683815'
        and b['tags'].get('memorial') != 'column'
    )


def component_vertices(obj, group):
    # Generator coordinates and roof probes are world-space. Incremental
    # adjustments may retain a translated/rotated editable object.
    return [
        obj.matrix_world @ v.co
        for v in obj.data.vertices
        if any(g.group == group.index for g in v.groups)
    ]


def mesh_tree(obj):
    return BVHTree.FromPolygons(
        [obj.matrix_world @ v.co for v in obj.data.vertices],
        [tuple(p.vertices) for p in obj.data.polygons],
    )


def vertex_tree(objects):
    points = [obj.matrix_world @ v.co for obj in objects for v in obj.data.vertices]
    kd = KDTree(len(points))
    for i, point in enumerate(points):
        kd.insert(point, i)
    kd.balance()
    return kd


def facade_vertices(mesh):
    return [
        point
        for name, start, end in mesh.parts
        if name in ('04_立面窗格', '05_临街店面')
        for point in mesh.v[start:end]
    ]


def check_neighbour_facade(building_id, kd, points):
    # Includes catalogue datum rounding (5 mm) and the chunk's Draco grid.
    assert points and all(kd.find(p)[2] < 0.012 for p in points), (
        building_id,
        'missing exported facade',
    )


def root_name(obj):
    while obj.parent:
        obj = obj.parent
    return obj.name


def samples(b):
    form = b['form']
    z = b['elevation']
    points = []
    if b['id'] == BEI:
        ring = b['polygons'][0][0]
        angle = math.atan2(ring[1][1] - ring[2][1], ring[1][0] - ring[2][0])
        c, s = math.cos(angle), math.sin(angle)
        return [
            dict(
                kind=kind,
                x=b['center'][0] + u * c - v * s,
                y=b['center'][1] + u * s + v * c,
                top=z + b['height'] + 4,
                expected=z + b['height'] + lift,
            )
            for kind, u, v, lift in [
                ('west-ridge', -12.5, 5, 1.12),
                ('east-ridge', 27.1, 0, 0.52),
                ('main-roof', 7, 8, 0),
            ]
        ]
    if b['id'] == CANTEEN_ID:
        # Probe independently in north-elevation coordinates, from inside each
        # gallery. A filled-in opening or a south-facing copy fails these rays.
        ring = b['polygons'][0][0]
        x, y = ring[5]
        dx, dy = (ring[4][i] - ring[5][i] for i in (0, 1))
        length = math.hypot(dx, dy)
        c, s = dx / length, dy / length
        probes = [
            ('hall-roof', 12, 26, b['height'] + 0.68),
            ('north-stair-low', 6.26, 2.05, 3.31 / 20),
            ('north-stair-high', 11.69, 2.05, 3.31),
            ('east-terrace', -0.8, 26, 17.30),
            ('wing-roof', -6.6, 41.5, b['height'] * 0.79),
            ('roof-plant', -12.04, 45.0, b['height'] + 1.90),
        ]
        probes += [
            ('north-gallery', 2, 2, h) for h in (3.31, 7.19, 11.43, 16.25, 19.96)
        ]
        return [
            {
                'kind': kind,
                'x': x + c * u - s * v,
                'y': y + s * u + c * v,
                'top': z + height + 1.5,
                'expected': z + height,
            }
            for kind, u, v, height in probes
        ]
    if b['id'] == TOWER_ID:
        x, y = b['center']
        h = b['height']
        # Avoid the central antenna and the tank lip; probe both tank overhangs.
        return [
            {
                'x': x + dx,
                'y': y,
                'top': z + h + 0.5,
                'expected': z + h,
                'kind': 'water-tank-roof',
            }
            for dx in (-2.3, 2.3)
        ]

    def area(tri):
        a, c, d = tri
        return abs((c[0] - a[0]) * (d[1] - a[1]) - (c[1] - a[1]) * (d[0] - a[0])) / 2

    def edge_distance(x, y, polygons):
        distances = []
        for poly in polygons:
            for ring in poly:
                for a, c in zip(ring, ring[1:]):
                    dx, dy = c[0] - a[0], c[1] - a[1]
                    length2 = dx * dx + dy * dy
                    t = (
                        max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / length2))
                        if length2
                        else 0
                    )
                    distances.append(math.hypot(x - a[0] - t * dx, y - a[1] - t * dy))
        return min(distances)

    parts = form['parts'] or [
        {
            'id': 'body',
            'polygons': b['polygons'],
            'triangles': b['roofTriangles'],
            'height': form['height'],
            'roof': form['roof'],
        }
    ]
    for part in parts:
        roof = part['roof']
        triangles = []
        if roof['type'] != 'flat':
            vertices = roof['geometry']['vertices']
            indices = roof['geometry']['triangles']
            triangles = [
                [vertices[k] for k in indices[i : i + 3]]
                for i in range(0, len(indices), 3)
            ]
        else:
            geometry = part.get('openBelow', {}).get('roofGeometry', part)
            for poly, indices in zip(geometry['polygons'], geometry['triangles']):
                vertices = [list(p) + [0] for ring in poly for p in ring[:-1]]
                triangles += [
                    [vertices[k] for k in indices[i : i + 3]]
                    for i in range(0, len(indices), 3)
                ]
        count = 0
        for tri in sorted(triangles, key=area, reverse=True):
            x, y, h = [sum(p[k] for p in tri) / 3 for k in range(3)]
            clearance = 0.02 if 'slattedRoof' in part.get('openBelow', {}) else 0.5
            if area(tri) < 0.1 or edge_distance(x, y, part['polygons']) < clearance:
                continue
            dome = form.get('roofDome')
            # Probe the supporting slab from inside the drum where covered;
            # a compact roof can have every triangle centroid below its dome.
            # The separate apex probe checks the new visible silhouette.
            covered = dome and math.dist((x, y), dome['center']) < dome['radius'] + 0.1
            for volume in form.get('roofVolumes', []):
                if volume['part'] != part['id']:
                    continue
                dx, dy = x - volume['center'][0], y - volume['center'][1]
                cs, sn = math.cos(volume['angle']), math.sin(volume['angle'])
                overhang = volume.get('cap', {}).get('overhang', 0)
                covered = covered or (
                    abs(dx * cs + dy * sn) <= volume['width'] / 2 + overhang + 0.01
                    and abs(-dx * sn + dy * cs) <= volume['depth'] / 2 + overhang + 0.01
                )
            crown = form.get('roofCrown')
            if crown and crown['part'] == part['id']:
                dx, dy = x - crown['corner'][0], y - crown['corner'][1]
                u, v = crown['u'], crown['v']
                det = u[0] * v[1] - u[1] * v[0]
                s, t = (dx * v[1] - dy * v[0]) / det, (u[0] * dy - u[1] * dx) / det
                covered = (
                    covered
                    or (0 <= s <= crown['width'] and 0 <= t <= crown['depth'])
                    or (
                        0 <= s <= crown['screenThickness']
                        and crown['depth'] <= t <= crown['screenBottomDepth']
                    )
                )
            points.append(
                {
                    'kind': 'roof',
                    'part': part['id'],
                    'x': x,
                    'y': y,
                    'top': z + part['height'] + h + (0.05 if covered else 4),
                    'expected': z + part['height'] + h,
                }
            )
            count += 1
            if count >= 3:
                break
        assert count > 0, (b['id'], part['id'], 'no usable roof samples')
    if 'roofDome' in form:
        dome = form['roofDome']
        x, y = dome['center']
        apex = z + dome['baseHeight'] + dome['drumHeight'] + dome['rise']
        points.append(
            {
                'kind': 'roof-dome-apex',
                'x': x,
                'y': y,
                'top': apex + 1,
                'expected': apex,
            }
        )
    for volume in form.get('roofVolumes', []):
        x, y = volume['center']
        apex = (
            z
            + volume['baseHeight']
            + volume['rise']
            + volume.get('cap', {}).get('height', 0)
        )
        points.append(
            {
                'kind': 'roof-volume-top',
                'x': x,
                'y': y,
                'top': apex + 1,
                'expected': apex,
            }
        )
    if 'roofCrown' in form:
        c = form['roofCrown']
        for kind, s, t, rise in [
            ('curtain-crown', c['width'] / 2, c['depth'] / 2, c['rise']),
            (
                'crown-screen',
                c['screenThickness'] / 2,
                (c['depth'] + c['screenTopDepth']) / 2,
                c['screenRise'],
            ),
        ]:
            x, y = [c['corner'][k] + c['u'][k] * s + c['v'][k] * t for k in (0, 1)]
            apex = z + c['baseHeight'] + rise
            points.append(
                {'kind': kind, 'x': x, 'y': y, 'top': apex + 1, 'expected': apex}
            )
    if 'gableScreen' in form:
        c = form['gableScreen']
        s = c['length'] * c['peakT']
        d = c['thickness'] / 2
        x, y = [
            c['start'][k] + c['tangent'][k] * s - c['normal'][k] * d for k in (0, 1)
        ]
        apex = z + c['baseHeight'] + c['peakRise']
        points.append(
            {
                'kind': 'gable-screen-apex',
                'x': x,
                'y': y,
                'top': apex + 1,
                'expected': apex,
            }
        )
    if 'stairTower' in form:
        s = form['stairTower']
        x, y = s['origin']
        floor = z + s['config']['baseHeight']
        points.append(
            {
                'kind': 'stair-ground-platform',
                'x': x,
                'y': y,
                'top': floor + 0.5,
                'expected': floor,
            }
        )
        return points
    if b['id'] in FRONTS:
        # Probe the photo-specific stairs and canopies in each published entrance
        # frame. Stock platform distances do not apply to these buildings.
        entry = form['entrances'][0]
        nx, ny = (
            math.sin(math.radians(entry['bearing'])),
            math.cos(math.radians(entry['bearing'])),
        )
        front_probes = {
            CUI: [
                ('lowest-step', 3.95, 0.12),
                ('middle-step', 3.74, 0.24),
                ('top-step', 3.50, 0.36),
                ('portico', 3.43, 4.799),
            ],
            BO: [
                ('threshold', 0.78, 0.212),
                ('light-landing', 2.58, 0.17),
                ('outer-granite', 5.455, 0.086),
                ('fascia', 2.30, 4.641),
            ],
            DONG: [
                ('upper-landing', 1.63, 0.32),
                ('lowest-step', 2.01, 0.178),
                ('entrance-canopy', 1.12, 3.99),
            ],
            XIU: [
                ('top-step', 5.95, 2.027),
                ('lowest-step', 10.52, 0.127),
                ('canopy', 1.8, 6.173),
            ],
            BI: [('threshold', 0.6, 0.09)],
        }
        for kind, out, height in front_probes[b['id']]:
            points.append(
                dict(
                    kind=kind,
                    x=entry['center'][0] + nx * out,
                    y=entry['center'][1] + ny * out,
                    top=z + height + (0.07 if b['id'] in (CUI, DONG) else 0.26),
                    expected=z + height,
                )
            )
        if b['id'] == BI:
            # Probe each finished tread from within the stairwell, below the cover.
            a, c = b['polygons'][0][0][1:3]
            half = math.dist(a, c) / 2
            start, end = half + 1.45, half + 4.55
            going = (end - start) / 12
            stair_samples = [
                ('entrance-paving', start - 0.55, 3.05, 0.17),
                ('turn-platform', half + 4.73, 2.80, 1.725),
                ('upper-landing', start - 0.7, 1.25, 3.28),
            ]
            for i in range(12):
                rise = 1.555 * (i + 1) / 12
                stair_samples.extend(
                    [
                        ('outward-tread', start + (i + 0.5) * going, 3.05, 0.17 + rise),
                        (
                            'return-tread',
                            end - (i + 0.5) * (4.55 - 1.05) / 12,
                            2.14,
                            1.725 + rise,
                        ),
                    ]
                )
            for kind, along, local_out, h in stair_samples:
                out = local_out - 7.32
                points.append(
                    dict(
                        kind=kind,
                        x=entry['center'][0] - ny * along + nx * out,
                        y=entry['center'][1] + nx * along + ny * out,
                        top=z + h + 0.08,
                        expected=z + h,
                    )
                )
            east = next(e for e in form['entrances'] if e['id'] == 'flavor-east')
            angle = math.radians(east['bearing'])
            assert 70 < east['bearing'] < 110 and not east['primary']
            # Probe the sign's drip edge beside the overhead light.
            for kind, out, along, height in [
                ('flavor-step', 0.8, 0.0, 0.15),
                ('flavor-sign', 0.29, 0.95, 3.672),
            ]:
                points.append(
                    dict(
                        kind=kind,
                        x=east['center'][0]
                        + math.sin(angle) * out
                        - math.cos(angle) * along,
                        y=east['center'][1]
                        + math.cos(angle) * out
                        + math.sin(angle) * along,
                        top=z + height + 0.22,
                        expected=z + height,
                    )
                )
        return points
    for e in form['entrances']:
        x, y = e['center']
        a = math.radians(e['bearing'])
        nx, ny = math.sin(a), math.cos(a)
        if 'recessedStairEntry' in e:
            p = e['recessedStairEntry']
            distance = (p['outerEnd'] + p['innerStart']) / 2
            points.append(
                {
                    'kind': 'recessed-entry-landing',
                    'x': x - nx * distance,
                    'y': y - ny * distance,
                    'top': z + p['platformHeight'] + 0.2,
                    'expected': z + p['platformHeight'],
                }
            )
            continue
        if b['id'] == 'relation/12875606' and e['id'] == 'southeast-main':
            # Sample the roof near both sloping eaves and the actual central
            # door header. The former rectangular generic roof was replaced.
            cx, cy = e['flushEntrance']['returnGlazing']['corner']
            for kind, dx, dy, h in [
                ('civil-west-eave', -11.3, -4.7, 8.21),
                ('civil-inscribed-eave', -2.0, -4.7, 8.21),
                ('civil-door-header', -6.23, -0.30, 2.78),
            ]:
                points.append(
                    dict(
                        kind=kind,
                        x=cx + dx,
                        y=cy + dy,
                        top=z + h + 0.18,
                        expected=z + h,
                    )
                )
            continue
        if 'flushEntrance' in e:
            p = e['flushEntrance']
            expected = z + p['floorHeight'] + p['doorHeight'] + p['frameWidth'] / 2
            points.append(
                {
                    'kind': 'flush-door-header',
                    'x': x + nx * 0.13,
                    'y': y + ny * 0.13,
                    'top': expected + 0.2,
                    'expected': expected,
                }
            )
            continue
        if 'shelter' in e:
            # This building owns the doorway; a separate mapped roof owns
            # its floor and canopy. Probe its stone header below that soffit.
            p = e['shelter']
            expected = (
                z + p['floorHeight'] + p['doorHeight'] + p['transomHeight'] + 0.12
            )
            for i in range(p['bays']):
                offset = -e['width'] / 2 + (i + 0.5) * e['width'] / p['bays']
                points.append(
                    {
                        'kind': 'sheltered-door-header',
                        'x': x + nx * 0.10 + ny * offset,
                        'y': y + ny * 0.10 - nx * offset,
                        'top': expected + 0.03,
                        'expected': expected,
                    }
                )
            continue
        if 'attachedPortico' in e:
            p = e['attachedPortico']
            distance = p['depth'] / 2
            points.append(
                {
                    'kind': 'entrance-platform',
                    'x': x + nx * distance,
                    'y': y + ny * distance,
                    'top': z + p['platformHeight'] + 0.5,
                    'expected': z + p['platformHeight'],
                }
            )
            points.append(
                {
                    'kind': 'entrance-canopy',
                    'x': x + nx * distance,
                    'y': y + ny * distance,
                    'top': z + p['clearHeight'] + p['slabThickness'] + 0.5,
                    'expected': z + p['clearHeight'] + p['slabThickness'],
                }
            )
            continue
        if 'stairFlight' in e:
            p = e['stairFlight']
            rise = (e['landingHeight'] - p['baseHeight']) / p['riserCount']
            for i in range(p['riserCount']):
                distance = (
                    p['landingDepth'] / 2
                    if i == 0
                    else p['landingDepth'] + (i - 0.5) * p['tread']
                )
                expected = z + e['landingHeight'] - i * rise
                for offset in (-p['width'] / 2 + 0.2, 0, p['width'] / 2 - 0.2):
                    points.append(
                        {
                            'kind': 'entrance-stair',
                            'x': x + nx * distance + ny * offset,
                            'y': y + ny * distance - nx * offset,
                            'top': expected + 0.4,
                            'expected': expected,
                        }
                    )
            continue
        if (
            b['id'] == SHAW
            and e['id'] == 'south-colonnade'
            and any(part['id'] == 'stair-core' for part in form['parts'])
        ):
            # At 1.6 m the ray hits the third tread below Shaw's 0.40 m landing.
            platform = 0.10
        elif 'landingHeight' in e:
            platform = e['landingHeight'] / 2
        else:
            platform = e.get('platformHeight', 0.075)
        points.append(
            {
                'kind': 'entrance-platform',
                'x': x + nx * 1.6,
                'y': y + ny * 1.6,
                'top': z + platform + 0.5,
                'expected': z + platform,
            }
        )
    return points


def check_samples(b, trees, tolerance):
    result = []
    for p in samples(b):
        hits = [
            tree.ray_cast(Vector((p['x'], p['y'], p['top'])), Vector((0, 0, -1)))
            for tree in trees
        ]
        heights = [hit[0].z for hit in hits if hit[0] is not None]
        if not heights:
            raise AssertionError((b['id'], p, 'missing surface'))
        actual = max(heights)
        error = abs(actual - p['expected'])
        if error > tolerance:
            raise AssertionError((b['id'], p, actual, error, tolerance))
        result.append({'kind': p['kind'], 'errorMeters': round(error, 6)})
    if b['id'] == BI:
        # A solid end drum can also carry a landing. Check the clear span underneath.
        a, c = b['polygons'][0][0][1:3]
        tangent = (Vector(a) - Vector(c)).normalized()
        outward = Vector((tangent.y, -tangent.x))
        xy = (
            (Vector(a) + Vector(c)) / 2
            + tangent * (math.dist(a, c) / 2 + 5.60)
            + outward * (4.48 - 7.32)
        )
        origin = Vector((*xy, b['elevation'] + 0.75))
        inward = Vector((-outward.x, -outward.y, 0))
        assert all(tree.ray_cast(origin, inward, 3.85)[0] is None for tree in trees), (
            b['id'],
            'blocked half-landing clearance',
        )
    if b['id'] == CANTEEN_ID:
        # A floor ray alone could also pass if a later edit sealed the north wall.
        ring = b['polygons'][0][0]
        west = (Vector(ring[4]) - Vector(ring[5])).normalized()
        inward = Vector((-west.y, west.x, 0))
        front = Vector((*ring[5], b['elevation'])) + Vector((west.x, west.y, 0)) * 2
        for h in (5.8, 10, 14.7, 19, 22.5):
            origin = front - inward + Vector((0, 0, h))
            hits = [tree.ray_cast(origin, inward, 8) for tree in trees]
            depths = [hit[3] - 1 for hit in hits if hit[0] is not None]
            assert depths and 4.5 < min(depths) < 5.1, (b['id'], h, depths)
    return result


def surface_points(vertices, faces):
    # Retain vertices and triangle-interior witnesses; welding and Draco can
    # discard a vertex on a planar face without changing the visible surface.
    vertices = np.asarray(vertices, dtype=np.float32)
    points = vertices[list({index for face in faces for index in face})]
    triangles = [face for face in faces if len(face) == 3]
    if triangles:
        centers = vertices[triangles].mean(axis=1)
        points = np.concatenate((points, centers))
    return np.unique(points, axis=0)


def authored_points(mesh, building_id):
    assert mesh.f and len(mesh.f) == len(mesh.m), (
        building_id,
        'empty or unpainted mesh',
    )
    points = surface_points(mesh.v, mesh.f)
    assert np.isfinite(points).all(), building_id
    return points


def point_set_error(actual, expected):
    # Welded vertices can have a different order and duplicate count.
    maximum = 0.0
    for points, reference in ((actual, expected), (expected, actual)):
        tree = KDTree(len(reference))
        for index, point in enumerate(reference):
            tree.insert(point, index)
        tree.balance()
        maximum = max(maximum, max(tree.find(point)[2] for point in points))
    return maximum


def check_components(obj, mesh, parts, building_id, tolerance):
    for name, start, end in parts:
        group = obj.vertex_groups.get(name)
        assert group is not None, (building_id, name, 'missing editable component')
        actual = component_vertices(obj, group)
        expected = mesh.v[start:end]
        if not actual and not expected:
            continue
        assert actual and expected, (building_id, name, 'empty source component')
        error = point_set_error(actual, expected)
        assert error < tolerance, (building_id, name, 'stale source form', error)


def check_authored_source(obj, mesh, building_id, component_tolerance=0.011):
    # Compare the same editable representation on each side. Welding can reduce
    # quads to triangles and change their centres without moving the surface.
    predicted = mesh.object('source-weld-check', bpy.context.scene.collection)
    compact_form_source(predicted)
    # Blender names each part separately, including .001 suffixes for repeated labels.
    parts = [
        (group.name, start, end)
        for group, (_, start, end) in zip(
            predicted.vertex_groups, mesh.parts, strict=True
        )
    ]
    actual, expected = [
        surface_points(
            [o.matrix_world @ vertex.co for vertex in o.data.vertices],
            [tuple(face.vertices) for face in o.data.polygons],
        )
        for o in (obj, predicted)
    ]
    data = predicted.data
    bpy.data.objects.remove(predicted, do_unlink=True)
    bpy.data.meshes.remove(data)
    maximum = point_set_error(actual, expected)
    assert maximum < 0.011, (building_id, 'stale editable surface', maximum)
    check_components(obj, mesh, parts, building_id, component_tolerance)
    return [
        {
            'kind': 'editable-surface',
            'points': len(actual),
            'errorMeters': round(maximum, 6),
        }
    ]


def check_authored_surface(building_id, points, trees, tolerance):
    maximum = 0.0
    for point in points:
        distances = [tree.find_nearest(point, tolerance)[3] for tree in trees]
        distance = min((d for d in distances if d is not None), default=None)
        assert distance is not None, (
            building_id,
            'missing authored surface',
            tuple(point),
            tolerance,
        )
        maximum = max(maximum, distance)
    return [
        {
            'kind': 'authored-surface',
            'points': len(points),
            'errorMeters': round(maximum, 6),
        }
    ]


def check_editable_source(bs, authored, zones, report):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'blender/gxu-campus.blend'))
    objects = {
        o.get('featureId'): o
        for o in bpy.context.scene.objects
        if o.type == 'MESH' and o.get('featureId')
    }
    MATERIALS[:] = list(bpy.data.materials)
    C = {mat.name: i for i, mat in enumerate(MATERIALS)}
    # The neighbour update rebuilds whole chunks from unrounded terrain elevations.
    neighbour_chunk_members = {
        fid
        for zone in zones
        if NEW_EAST_NEIGHBOURS.intersection(zone['featureIds'])
        for fid in zone['featureIds']
    }
    elevation = make_elevation(
        json.loads((ROOT / 'public/data/terrain.json').read_text())
    )
    report['source'] = []
    for b in bs:
        assert b['id'] in objects, (b['id'], 'missing editable source object')
        o = objects[b['id']]
        in_neighbour_chunk = b['id'] in neighbour_chunk_members
        z = elevation(*b['center']) if in_neighbour_chunk else b['elevation']
        expected = building_mesh(b, z, C, b['insideCampus'])
        component_tolerance = 0.001 if in_neighbour_chunk else 0.011
        if b['id'] in authored:
            report['source'].append(
                {
                    'id': b['id'],
                    'samples': check_authored_source(
                        o, expected, b['id'], component_tolerance
                    ),
                }
            )
            continue
        parts = (
            expected.parts
            if in_neighbour_chunk or b['id'] in FRONTS or b['id'] == CANTEEN_ID
            else expected.parts[:3]
        )
        check_components(o, expected, parts, b['id'], component_tolerance)
        if b['id'] == TOWER_ID:
            actual = [o.matrix_world @ v.co for v in o.data.vertices]
            assert actual and expected.v
            assert point_set_error(actual, expected.v) < 0.011, (
                'Stale editable water tower'
            )
        report['source'].append(
            {'id': b['id'], 'samples': check_samples(b, [mesh_tree(o)], 0.011)}
        )
    neighbours = [b for b in bs if b['id'] in NEW_EAST_NEIGHBOURS]
    if neighbours:
        (gate,) = [
            o for o in bpy.context.scene.objects if o.get('landmark') == 'new-east-gate'
        ]
        gate_tree = mesh_tree(gate)
        for b in neighbours:
            assert not gate_tree.overlap(mesh_tree(objects[b['id']])), (
                b['id'],
                'facade intersects gate enclosure',
            )
        report['neighbourGateClearancePassed'] = True
        for shop_id in sorted(SHOP_BUILDINGS & {b['id'] for b in neighbours}):
            shop = objects[shop_id]
            group = shop.vertex_groups['05_临街店面'].index
            indices = {
                v.index
                for v in shop.data.vertices
                if any(g.group == group for g in v.groups)
            }
            faces = [
                tuple(p.vertices)
                for p in shop.data.polygons
                if all(i in indices for i in p.vertices)
            ]
            shop_tree = BVHTree.FromPolygons(
                [shop.matrix_world @ v.co for v in shop.data.vertices], faces
            )
            for other_id in NEW_EAST_NEIGHBOURS - {shop_id}:
                assert not shop_tree.overlap(mesh_tree(objects[other_id])), (
                    shop_id,
                    other_id,
                    'shopfront intersects adjacent building',
                )
            report['shopfrontNeighbourClearancePassed'] = True
            terrain_tree = mesh_tree(bpy.data.objects['terrain'])
            paving = [
                p
                for p in shop.data.polygons
                if shop.data.materials[p.material_index].name
                in {'eastShopPaving', 'eastShopPavingJoint'}
            ]
            assert paving, 'Missing shop apron'
            for face in paving:
                point = shop.matrix_world @ face.center
                hit, *_ = terrain_tree.ray_cast(
                    point + Vector((0, 0, 2)), Vector((0, 0, -1)), 5
                )
                assert hit is not None and 0.01 < point.z - hit.z < 0.08, (
                    'Shop apron ground clearance',
                    point,
                    hit,
                )
            report['shopApronGroundingPassed'] = True


def check_shipping_meshes(bs, authored, facades, by_chunk, by_building, report):
    # Import shipping meshes, not a newly re-exported test substitute.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / 'public/models/base.glb'))
    bpy.context.view_layer.update()
    objects = {}
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            objects.setdefault(root_name(o), []).append(o)
    keys = {by_building[b['id']] if b['insideCampus'] else 'context' for b in bs}
    trees = {key: [mesh_tree(o) for o in objects[key]] for key in keys}
    neighbour_keys = {
        by_building[b['id']] if b['insideCampus'] else 'context'
        for b in bs
        if b['id'] in facades
    }
    facade_trees = {key: vertex_tree(objects[key]) for key in neighbour_keys}
    report['base'] = []
    for b in bs:
        key = by_building[b['id']] if b['insideCampus'] else 'context'
        if b['id'] in RESIDENCE_IDS:
            assert bpy.data.objects[key].get('buildingId') == b['id'], (
                key,
                'wrong base residence',
            )
        probes = (
            check_authored_surface(b['id'], authored[b['id']][0], trees[key], 0.05)
            if b['id'] in authored
            else check_samples(b, trees[key], 0.05)
        )
        report['base'].append({'id': b['id'], 'samples': probes})
        if b['id'] in facades:
            check_neighbour_facade(b['id'], facade_trees[key], facades[b['id']][0])
    report['near'] = []
    for chunk in sorted({by_building[b['id']] for b in bs if b['insideCampus']}):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(
            filepath=str(ROOT / 'public' / by_chunk[chunk]['url'])
        )
        bpy.context.view_layer.update()
        objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        assert {root_name(o) for o in objects} == {chunk}, (
            chunk,
            'incorrect replacement node',
        )
        trees = [mesh_tree(o) for o in objects]
        facade_tree = vertex_tree(objects) if chunk in neighbour_keys else None
        for b in bs:
            if by_building.get(b['id']) == chunk:
                if b['id'] in RESIDENCE_IDS:
                    assert bpy.data.objects[chunk].get('buildingId') == b['id'], (
                        chunk,
                        'wrong near residence',
                    )
                probes = (
                    check_authored_surface(b['id'], authored[b['id']][1], trees, 0.02)
                    if b['id'] in authored
                    else check_samples(b, trees, 0.02)
                )
                report['near'].append({'id': b['id'], 'samples': probes})
                if b['id'] in facades:
                    check_neighbour_facade(b['id'], facade_tree, facades[b['id']][1])


def main():
    prefix = next(
        (a.split('=', 1)[1] for a in sys.argv if a.startswith('--report-prefix=')),
        'generic',
    )
    if not re.fullmatch('[a-z0-9-]+', prefix):
        raise ValueError('Invalid report prefix')
    bs = [
        b
        for b in json.loads((ROOT / 'public/data/buildings.json').read_text())
        if ordinary(b)
    ]
    generated_only = '--generated-only' in sys.argv
    chunk = next(
        (a.split('=', 1)[1] for a in sys.argv if a.startswith('--chunk=')), None
    )
    if generated_only:
        by_building = {
            b['id']: residence_chunk_id(b['id'])
            if b['id'] in RESIDENCE_IDS
            else b.get('chunk')
            for b in bs
            if b['insideCampus']
        }
    else:
        zones = json.loads((ROOT / 'public/data/models.json').read_text())['zones']
        by_chunk = {zone['id']: zone for zone in zones}
        by_building = {}
        for zone in zones:
            for fid in zone['featureIds']:
                assert fid not in by_building, (fid, 'assigned to two near chunks')
                by_building[fid] = zone['id']
        catalogue_ids = {b['id'] for b in bs}
        assert RESIDENCE_IDS <= catalogue_ids, (
            'missing residences',
            RESIDENCE_IDS - catalogue_ids,
        )
        for b in bs:
            if b['insideCampus']:
                assert by_building[b['id']] == b['chunk'], (
                    b['id'],
                    'wrong catalogue chunk',
                )
                if b['id'] in RESIDENCE_IDS:
                    key = residence_chunk_id(b['id'])
                    assert by_chunk[key]['featureIds'] == [b['id']], (
                        key,
                        'residence must replace its own base mesh',
                    )
    if chunk:
        bs = [b for b in bs if by_building.get(b['id']) == chunk]
        assert bs, ('Unknown or empty ordinary building chunk', chunk)
    colors = [
        'pink',
        'residenceStone',
        *FINISHES,
        'curb',
        'leaf',
        'leaf2',
        'livingWarm',
        'livingCool',
        'stone',
        'stoneWarm',
        'wood',
        'stoneCool',
        'white',
        'timeLetter',
        'tenWall',
        'tenTrim',
        'tenGlass',
        'wallStone',
        'fenceIron',
        'gateRed',
        'gateRecess',
        'gateStone',
        'gateTrim',
        'gateJoint',
        'lampMetal',
        'courtMetal',
        'bridgeConcrete',
        'asphalt',
        'libraryGlass',
        'libraryTrim',
        'bark',
        'bridgeJoint',
        'drainStone',
        'road',
        'roadWhite',
        'roadYellow',
        'sportWhite',
        'water',
        'libraryStone',
        'libraryMullion',
        'huicuiFrame',
        'huicuiTrim',
        'huicuiWall',
        'residencePodium',
        'libraryInk',
        'residenceGlass',
        'slate',
        'paleRoof',
        'blueRoof',
        'red',
        'dark',
        'path',
        'shadeGlass',
        'glass',
        'grass',
        'green',
        'metal',
    ]
    C = {k: i for i, k in enumerate(colors)}
    MATERIALS[:] = [bpy.data.materials.new('generic-check-' + name) for name in colors]
    generated = []
    authored_ids = (
        RESIDENCE_IDS
        | OFFICE_IDS
        | COLLEGE_MODELS.keys()
        | COLLEGE_FACADES.keys()
        | {GATE, MANAGEMENT, YULIN}
    )
    authored = {}
    facades = {}
    for b in bs:
        low = building_mesh(b, b['elevation'], C, False)
        high = building_mesh(b, b['elevation'], C, True)
        if b['id'] in SHOP_BUILDINGS:
            facades[b['id']] = (facade_vertices(low), facade_vertices(high))
        if b['id'] in authored_ids or 'stairTower' in b['form']:
            # These models have independently authored LODs and facade groups.
            authored[b['id']] = (
                authored_points(low, b['id']),
                authored_points(high, b['id']),
            )
            generated.append(
                {'id': b['id'], 'farFaces': len(low.f), 'nearFaces': len(high.f)}
            )
            continue
        for (name, a, c), (other, x, y) in zip(low.parts[:3], high.parts[:3]):
            assert name == other and low.v[a:c] == high.v[x:y], (
                b['id'],
                name,
                'LOD form mismatch',
            )
        assert all(math.isfinite(x) for v in high.v for x in v)
        if b['form']['roof']['type'] != 'flat':
            obj = high.object('source-weld-check', bpy.context.scene.collection)
            compact_form_source(obj)
            group = obj.vertex_groups['02_屋顶轮廓'].index
            actual = [
                v.co
                for v in obj.data.vertices
                if any(g.group == group for g in v.groups)
            ]
            kd = KDTree(len(actual))
            for i, point in enumerate(actual):
                kd.insert(point, i)
            kd.balance()
            _, start, end = high.parts[1]
            assert all(kd.find(point)[2] < 0.0002 for point in high.v[start:end]), (
                b['id'],
                'welding lost shared eave group',
            )
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.meshes.remove(mesh)
        # Dining facilities must not get the residential balcony extension.
        if b['form']['archetype'] == 'canteen' and b['id'] != CANTEEN_ID:
            residential = {**b, 'form': {**b['form'], 'archetype': 'dormitory'}}
            assert len(high.v) < len(
                building_mesh(residential, b['elevation'], C, True).v
            )
        generated.append(
            {
                'id': b['id'],
                'roof': b['form']['roof']['type'],
                'archetype': b['form']['archetype'],
                'sharedComponents': min(3, len(high.parts)),
            }
        )
    report = {
        'generatedBuildings': len(bs),
        'generated': generated,
        'scope': 'ordinary buildings only; dedicated landmarks and monuments use their existing verifiers',
        'tolerancesMeters': {'source': 0.011, 'baseDraco': 0.05, 'nearDraco': 0.02},
    }
    target = ROOT / 'work/model-checks'
    target.mkdir(parents=True, exist_ok=True)
    if generated_only:
        report['generatedPassed'] = True
        (target / (prefix + '-generated.json')).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        )
        print(f'Generated form passed: {len(bs)} ordinary buildings', flush=True)
        return
    check_shipping_meshes(bs, authored, facades, by_chunk, by_building, report)
    print(f'Published base/near geometry passed: {len(bs)} buildings', flush=True)
    check_editable_source(bs, authored, zones, report)
    report['passed'] = True
    (target / (prefix + '-geometry.json')).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    )
    print(f'Source/base/near form passed: {len(bs)} buildings', flush=True)


if __name__ == '__main__':
    main()
