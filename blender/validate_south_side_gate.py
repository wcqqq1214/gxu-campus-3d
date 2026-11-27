"""Validate the photo-based south-side gate in source and both exported LODs."""

import json
import re
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'blender'))
from tree_mesh_audit import check_meshes, snapshot


def single_gate(rows):
    [row] = [item for item in rows if item.get('id') == 'south-side-gate']
    return row


catalog = json.loads((ROOT / 'public/data/landmarks.json').read_text())
record = single_gate(catalog)
entrance = single_gate(
    json.loads((ROOT / 'public/data/geography.geojson').read_text())['features']
)
assert entrance['geometry'] == {'type': 'Point', 'coordinates': record['lonLat']}
models = json.loads((ROOT / 'public/data/models.json').read_text())
assert single_gate(models['landmarks'])['url'] == 'models/south-side-gate.glb'
cx, cy = record['center']
base = record['elevation'] + 0.24


def check(objects, label):
    assert len(objects) == 1, (label, 'expected one south-side landmark', objects)
    trees = []
    for obj in objects:
        obj.data.calc_loop_triangles()
        triangles = list(obj.data.loop_triangles)
        trees.append(
            (
                BVHTree.FromPolygons(
                    [obj.matrix_world @ v.co for v in obj.data.vertices],
                    [tuple(t.vertices) for t in triangles],
                    all_triangles=True,
                ),
                [
                    re.sub(r'\.\d+$', '', obj.data.materials[t.material_index].name)
                    for t in triangles
                ],
            )
        )

    def ray(x, y, z, direction, length):
        found = []
        for tree, mats in trees:
            p, n, i, d = tree.ray_cast(
                Vector((cx + x, cy + y, base + z)), Vector(direction), length
            )
            if p is not None:
                found.append((d, p, mats[i]))
        return min(found, key=lambda item: item[0]) if found else None

    # Check clearances above and below the photographed lowered arm separately.
    # The east opening is intentionally crossed only at the arm's actual height.
    for x in [-3, -2, 2, 3]:
        for z in [0.8, 1.8, 2.8]:
            assert ray(x, -4, z, (0, 1, 0), 8) is None, (
                label,
                'unexpected vehicle-lane obstruction',
                x,
                z,
            )
    for x in [-3.9, 3.9]:
        for z in [0.6, 1.4]:
            assert ray(x, -2, z, (0, 1, 0), 5) is None, (
                label,
                'blocked pedestrian path',
                x,
                z,
            )
    notice = ray(-0.20, -2, 1.4, (0, 1, 0), 4)
    assert notice and notice[2] == 'southSideBlue', (label, 'blue notice', notice)
    cabinet = ray(0.40, -2, 0.82, (0, 1, 0), 3)
    assert cabinet and cabinet[2] == 'southSideYellow', (
        label,
        'single yellow cabinet on the east side',
        cabinet,
    )
    arm = ray(2.0, -2, 1.214, (0, 1, 0), 3)
    assert arm and arm[2] in {'southSideWhite', 'southSideRed'}, (
        label,
        'east lane lowered barrier arm',
        arm,
    )
    pier = ray(-7, -0.8, 1.0, (1, 0, 0), 3)
    assert pier and pier[2] in {'southSideStone', 'southSideSandstone'}, (
        label,
        'stone pier',
        pier,
    )
    arch = ray(-6.5, 1.2, 2.00, (1, 0, 0), 2)
    assert arch and arch[2] == 'southSideBlack', (label, 'arched ironwork', arch)
    wall = ray(-6.5, 5.67, 0.6, (1, 0, 0), 2)
    assert wall and wall[2] == 'southSideWallStone', (label, 'masonry sill', wall)
    symbol = ray(-4.86, 3.87, 2.89, (-0.743, -0.669, 0), 1.5)
    assert symbol and symbol[2] == 'southSideBlue', (label, 'single-sided sign', symbol)
    guardrail = ray(3.68, 4, 2, (0, 0, -1), 3)
    assert guardrail and guardrail[2] == 'southSideGuardrail', (
        label,
        'parking tube',
        guardrail,
    )
    panel = ray(-5.10, 4.24, 2, (0, 0, -1), 3)
    assert panel and panel[2] == 'southSideWhite', (label, 'longitudinal rail', panel)
    paint = ray(6.8, 4.55, 2, (0, 0, -1), 3)
    assert paint and paint[2] == 'southSidePaint', (
        label,
        'transverse parking line',
        paint,
    )
    manhole = ray(1.65, 6.24, 3, (0, 0, -1), 4)
    assert (
        manhole
        and manhole[2] == 'southSideMetal'
        and abs(manhole[1].z - base - 0.421) < 0.012
    ), (label, 'east interior manhole cover', manhole)
    drain = ray(-2, -1.65, 3, (0, 0, -1), 4)
    assert (
        drain
        and drain[2] in {'southSideBlack', 'southSideMetal'}
        and abs(drain[1].z - base - 0.119) < 0.02
    ), (label, 'slot drain', drain)
    island = ray(0.3, 1.0, 3, (0, 0, -1), 4)
    assert (
        island
        and island[2] == 'southSideIsland'
        and abs(island[1].z - base - 0.355) < 0.012
    ), (label, 'rounded checkpoint island', island)
    parking = ray(5.5, 2.5, 3, (0, 0, -1), 4)
    assert (
        parking
        and parking[2] == 'southSideAsphalt'
        and abs(parking[1].z - base - 0.292) < 0.012
    ), (label, 'graded parking apron', parking)
    paving = ray(-4.0, 6, 3, (0, 0, -1), 4)
    assert (
        paving
        and paving[2] == 'southSideConcrete'
        and abs(paving[1].z - base - 0.393) < 0.012
    ), (label, 'graded west paving', paving)
    materials = {
        re.sub(r'\.\d+$', '', mat.name)
        for obj in objects
        for mat in obj.data.materials
        if mat
    }
    assert materials and all(name.startswith('southSide') for name in materials), (
        label,
        'unexpected ceremonial-gate material',
        materials,
    )
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    size = [round(b - a, 4) for a, b in zip(lo, hi)]
    assert all(abs(a - b) < 0.02 for a, b in zip(size, [13.70, 9.49, 3.434])), (
        label,
        size,
    )
    return {
        'materials': sorted(materials),
        'triangles': len(triangles),
        'dimensionsMetres': size,
        'boundsBlenderMetres': [lo, hi],
    }


def source_trees():
    return {
        obj.name: (
            (round(obj.location.x, 1), round(obj.location.y, 1)),
            obj.data.name,
            tuple(map(tuple, obj.matrix_world)),
        )
        for obj in bpy.context.scene.objects
        if obj.name.startswith('树木示意-')
    }


def check_tree_delta(baseline):
    tree_path = 'public/data/vegetation.json'
    before_rows = json.loads((baseline / tree_path).read_text())
    after_rows = json.loads((ROOT / tree_path).read_text())
    after_positions = {tuple(row[:2]) for row in after_rows}
    assert len(after_positions) == len(after_rows)
    kept = [r for r in before_rows if tuple(r[:2]) in after_positions]
    assert kept == after_rows
    removed = Counter(
        tuple(r[:2]) for r in before_rows if tuple(r[:2]) not in after_positions
    )

    bpy.ops.wm.open_mainfile(filepath=str(baseline / 'blender/gxu-campus.blend'))
    original = source_trees()
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'blender/gxu-campus.blend'))
    final = source_trees()
    lost_names = sorted(original.keys() - final.keys())
    assert Counter(original[name][0] for name in lost_names) == removed
    assert final == {
        name: attrs for name, attrs in original.items() if attrs[0] not in removed
    }
    return {
        'originalDataTrees': len(before_rows),
        'finalDataTrees': len(after_rows),
        'originalEditableTrees': len(original),
        'finalEditableTrees': len(final),
        'removedEditableObjects': lost_names,
        'allRetainedNamesTransformsAndMeshLinksMatch': True,
    }


report = {}
baseline_arg = next(
    (s.split('=', 1)[1] for s in sys.argv if s.startswith('--tree-baseline-root=')),
    None,
)
if baseline_arg:
    report['treeSourceDelta'] = check_tree_delta(Path(baseline_arg))
else:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'blender/gxu-campus.blend'))
objects = [o for o in bpy.context.scene.objects if o.get('landmark') == record['id']]
assert len(objects) == 1 and len(objects[0].vertex_groups) == 5
report['source'] = check(objects, 'source')


# Raycast against both actual scene surfaces. Across the two apron edges,
# the upper face must continue the road and the skirt must reach the terrain.
def height_probe(obj, x, y, upward=False):
    tree = surface_trees[obj.name]
    z, direction = (-20, 1) if upward else (20, -1)
    point = tree.ray_cast(
        obj.matrix_world.inverted() @ Vector((cx + x, cy + y, z)),
        Vector((0, 0, direction)),
        40,
    )[0]
    assert point is not None, (obj.name, x, y)
    return (obj.matrix_world @ point).z


roads = bpy.data.objects['roads']
terrain = bpy.data.objects['terrain']
gate = objects[0]
surface_trees = {
    obj.name: BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    for obj in (gate, roads, terrain)
}
ties = []
for edge, inner, outer in [(-3.61, -3.63, -6.24), (3.81, 3.83, 7.44)]:
    for y in [-1.85, 0.1, 3.2, 6.3, 7.40]:
        difference = height_probe(gate, inner, y) - height_probe(roads, edge, y)
        bury = height_probe(terrain, outer, y) - height_probe(
            gate, outer, y, upward=True
        )
        assert -0.002 < difference < 0.035 and bury > 0, (edge, y, difference, bury)
        ties.append(
            {
                'apronMinusRoad': round(difference, 4),
                'skirtBelowTerrain': round(bury, 4),
            }
        )
report['apronTiesMetres'] = ties
report['roadElevation'] = height_probe(roads, 0, 0)
report['islandTopAboveRoad'] = height_probe(gate, 0.3, 1.0) - height_probe(
    roads, 0.3, 1.0
)
assert 0.14 < report['islandTopAboveRoad'] < 0.17
surface_trees.clear()
gate_meshes = []
for name in ['base', 'south-side-gate']:
    raw = (ROOT / f'public/models/{name}.glb').read_bytes()
    doc = json.loads(raw[20 : 20 + int.from_bytes(raw[12:16], 'little')])
    [node] = [
        n for n in doc['nodes'] if n.get('extras', {}).get('landmark') == record['id']
    ]
    assert node['name'] == 'landmark-south-side-gate'
    if name == record['id']:
        assert len(doc['nodes']) == 1
    assert 'KHR_draco_mesh_compression' in doc.get('extensionsRequired', [])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / f'public/models/{name}.glb'))
    bpy.context.view_layer.update()
    objects = [
        o
        for o in bpy.context.scene.objects
        if o.type == 'MESH' and o.get('landmark') == record['id']
    ]
    report[name] = check(objects, name)
    gate_meshes.append((name, snapshot(objects[0])))

templates = {}
for lod, asset in [('base', 'trees'), ('near', 'treesNear')]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / 'public' / models[asset]['url']))
    templates[lod] = {
        obj['template']: snapshot(obj)
        for obj in bpy.context.scene.objects
        if obj.type == 'MESH' and obj.get('template') is not None
    }
    assert set(templates[lod]) == {0, 1, 2, 3}
trees = json.loads((ROOT / 'public/data/vegetation.json').read_text())
report['treeClearance'] = check_meshes(trees, gate_meshes, templates)
assert report['treeClearance']['passed'], report['treeClearance']['collisions']
(ROOT / 'work/south-side-gate-geometry.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + '\n'
)
print(json.dumps(report, ensure_ascii=False), flush=True)
