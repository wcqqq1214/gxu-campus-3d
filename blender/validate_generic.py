"""Verify ordinary form in both generators, saved source and decoded shipping GLBs.

--generated-only checks generators before rebuilding. The default also checks
real source vertex groups and ray samples in base and every near chunk.
"""

import json
import math
import re
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from dining_halls import BEI, BI, BO, CUI, DONG, FRONTS, XIU
from east27_dining import EAST27_ID, hall_frame
from generic_buildings import compact_form_source, ordinary_building
from geometry import MATERIALS
from nanyuan import CANTEEN_ID
from new_east_neighbours import BUILDING_IDS as NEW_EAST_NEIGHBOURS
from new_east_neighbours import SHOP_BUILDINGS
from student_water_tower import TOWER_ID
from west22 import WEST22
from west23 import WEST23
from west_dorms import FINISHES, roof_frame
from west_dorms import NUMBERS as WEST_DORMS


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


def check_neighbour_facade(b, kd, C, detail):
    expected = ordinary_building(b, b['elevation'], C, detail)
    ranges = [
        (start, end)
        for name, start, end in expected.parts
        if name in ('04_立面窗格', '05_临街店面')
    ]
    # Includes catalogue datum rounding (5 mm) and the chunk's Draco grid.
    assert all(
        kd.find(p)[2] < 0.012 for start, end in ranges for p in expected.v[start:end]
    ), (b['id'], 'missing exported facade')


def root_name(obj):
    while obj.parent:
        obj = obj.parent
    return obj.name


def samples(b):
    form = b['form']
    z = b['elevation']
    points = []
    if b['id'] in WEST_DORMS:
        ux, uy, x0, y0, x1, _ = roof_frame(b)
        h = z + b['height']
        # Open perimeter of the flat roof and a collector within the eastern array.
        for label, x, y, lift in [
            ('south-deck', (x0 + x1) / 2, y0 + 0.56, 0),
            ('east-collector', x1 - 9.0, y0 + 2.7, 0.47),
        ]:
            points.append(
                dict(
                    kind=label,
                    x=ux * x - uy * y,
                    y=uy * x + ux * y,
                    top=h + 2,
                    expected=h + lift,
                )
            )
        return points
    if b['id'] == WEST23:
        x = b['bounds'][0] + 6.3
        y = b['bounds'][3]
        return [
            dict(kind=kind, x=x - u, y=y - v, expected=z + h, top=z + h + 0.13)
            for kind, u, v, h in [
                ('roof', -20, 8, b['height'] + 0.12),
                ('west-arcade', 1.6, 0.8, 0),
                ('left-entrance-mat', -14.4, -0.35, 0.021),
                ('right-entrance-mat', -11.4, -0.30, 0.021),
                ('fascia', -3.4, -0.28, 2.66),
            ]
        ]
    if b['id'] == WEST22:
        xmin, ymin, xmax, ymax = b['bounds']
        length = xmax - xmin
        targets = [
            ('roof', length / 2, (ymax - ymin) / 2, b['height'] + 0.14),
            ('threshold-mat', length * 3.5 / 18 + 1.2, 0.22, 0.024),
            ('arcade', 30, -2.1, 0),
        ]
        angle = math.radians(-2.45)
        for k in range(6):
            v = -(k + 0.5) * 2.50 / 6
            targets.append(
                (
                    f'east-tread-{k + 1}',
                    length + 1.94 - v * math.sin(angle),
                    -8.01 + v * math.cos(angle),
                    -(k + 1) * 1.245 / 7,
                )
            )
        return [
            dict(kind=kind, x=xmin + x, y=ymin + y, top=z + h + 0.12, expected=z + h)
            for kind, x, y, h in targets
        ]
    if b['id'] == EAST27_ID:
        x, y, a = hall_frame(b)
        for kind, u, v, top, h in (
            ('covered-dining-floor', -3, -4.1, 0.60, 0.07),
            ('serving-ledge', 2, -0.27, 1.58, 1.0),
            ('east-link-roof', 29, 16.5, 25, b['height'] + 0.12),
            ('court-crossing', -34, 16.55, 0.60, 0.09),
        ):
            points.append(
                dict(
                    kind=kind,
                    x=x + u * math.cos(a) - v * math.sin(a),
                    y=y + u * math.sin(a) + v * math.cos(a),
                    top=z + top,
                    expected=z + h,
                )
            )
        return points
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
        platform = (
            e['landingHeight'] / 2
            if 'landingHeight' in e
            else e.get('platformHeight', 0.075)
        )
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
    chunk = next(
        (a.split('=', 1)[1] for a in sys.argv if a.startswith('--chunk=')), None
    )
    if chunk:
        bs = [b for b in bs if b.get('chunk') == chunk]
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
        'wallStone',
        'fenceIron',
        'gateRed',
        'gateRecess',
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
    for b in bs:
        low = ordinary_building(b, b.get('elevation', 0), C, False)
        high = ordinary_building(b, b.get('elevation', 0), C, True)
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
                ordinary_building(residential, b.get('elevation', 0), C, True).v
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
    if '--generated-only' in sys.argv:
        report['generatedPassed'] = True
        (target / (prefix + '-generated.json')).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        )
        print(f'Generated form passed: {len(bs)} ordinary buildings', flush=True)
        return
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'blender/gxu-campus.blend'))
    objects = {
        o.get('featureId'): o
        for o in bpy.context.scene.objects
        if o.type == 'MESH' and o.get('featureId')
    }
    C.clear()
    MATERIALS.clear()
    for mat in bpy.data.materials:
        C[mat.name] = len(MATERIALS)
        MATERIALS.append(mat)
    report['source'] = []
    for b in bs:
        o = objects[b['id']]
        expected = ordinary_building(b, b['elevation'], C, b['insideCampus'])
        if b['id'] == TOWER_ID:
            actual = [o.matrix_world @ v.co for v in o.data.vertices]
            for left, right in ((actual, expected.v), (expected.v, actual)):
                assert left and right
                kd = KDTree(len(right))
                for i, point in enumerate(right):
                    kd.insert(point, i)
                kd.balance()
                assert all(kd.find(point)[2] < 0.011 for point in left), (
                    'Stale editable water tower'
                )
        for name, start, end in (
            expected.parts
            if b['id'] in NEW_EAST_NEIGHBOURS
            or b['id'] in FRONTS
            or b['id'] in (CANTEEN_ID, EAST27_ID, WEST22, WEST23)
            else expected.parts[:3]
        ):
            group = o.vertex_groups.get(name)
            assert group is not None, (b['id'], name, 'missing editable component')
            actual = component_vertices(o, group)
            # Source vertices are welded for file size; compare geometry in
            # both directions, independent of duplicate count or mesh ordering.
            predicted = expected.v[start:end]
            for left, right in ((actual, predicted), (predicted, actual)):
                if not left and not right:
                    continue
                assert left and right, (b['id'], name, 'empty source component')
                kd = KDTree(len(right))
                for i, point in enumerate(right):
                    kd.insert(point, i)
                kd.balance()
                assert all(kd.find(point)[2] < 0.011 for point in left), (
                    b['id'],
                    name,
                    'stale source form',
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
            for other in neighbours:
                if other['id'] != shop_id:
                    assert not shop_tree.overlap(mesh_tree(objects[other['id']])), (
                        'Shopfront intersects adjacent building'
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
    # Import shipping meshes, not a newly re-exported test substitute.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / 'public/models/base.glb'))
    bpy.context.view_layer.update()
    objects = {}
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            objects.setdefault(root_name(o), []).append(o)
    trees = {key: [mesh_tree(o) for o in group] for key, group in objects.items()}
    neighbour_keys = {
        b['chunk'] if b['insideCampus'] else 'context' for b in neighbours
    }
    facade_trees = {key: vertex_tree(objects[key]) for key in neighbour_keys}
    report['base'] = []
    for b in bs:
        key = b['chunk'] if b['insideCampus'] else 'context'
        report['base'].append(
            {'id': b['id'], 'samples': check_samples(b, trees[key], 0.05)}
        )
        if b['id'] in NEW_EAST_NEIGHBOURS:
            check_neighbour_facade(b, facade_trees[key], C, False)
    report['near'] = []
    for chunk in sorted({b['chunk'] for b in bs if b['insideCampus']}):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(ROOT / 'public/models' / f'{chunk}.glb'))
        bpy.context.view_layer.update()
        objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        trees = [mesh_tree(o) for o in objects]
        facade_tree = vertex_tree(objects) if chunk in neighbour_keys else None
        for b in bs:
            if b.get('chunk') == chunk:
                report['near'].append(
                    {'id': b['id'], 'samples': check_samples(b, trees, 0.02)}
                )
                if b['id'] in NEW_EAST_NEIGHBOURS:
                    check_neighbour_facade(b, facade_tree, C, True)
    report['passed'] = True
    (target / (prefix + '-geometry.json')).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    )
    print(f'Source/base/near form passed: {len(bs)} buildings', flush=True)


if __name__ == '__main__':
    main()
