"""Probe actual closed facade walls above shared ground, including both LODs.

This detects sampled open gaps under walls; it does not establish real site
levels. Open porticos and facades explicitly beginning above ground are excluded.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from generic_buildings import facade_segments
from inspect_foundation_clearance import layer, top_tree


def wall_tree(objects):
    vertices, faces = [], []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        faces.extend(tuple(offset + i for i in p.vertices) for p in obj.data.polygons)
    if not faces:
        raise ValueError('Missing building geometry')
    return BVHTree.FromPolygons(vertices, faces)


def probes(building, ground, roads):
    excluded = {p['id'] for p in building['form']['parts'] if p.get('openBelow')}
    rows = []
    down = Vector((0, 0, -1))
    datum = building['elevation']
    for index, facade in enumerate(facade_segments(building)):
        if facade.get('part') in excluded or facade.get('minimumHeight', 0) > 0:
            continue
        a, b = facade['start'], facade['end']
        normal = facade['normal']
        count = max(1, math.ceil(math.dist(a, b) / 2))
        for i in range(count):
            t = (i + .5) / count
            x, y = (a[k] + (b[k] - a[k]) * t for k in (0, 1))
            # Immediately outside the wall, not a distant DEM lattice node.
            origin = Vector((x + normal[0] * .02, y + normal[1] * .02, datum + 50))
            g = ground.ray_cast(origin, down, 100)[0]
            if g is None:
                raise ValueError('Missing facade ground')
            road_origin = Vector((origin.x, origin.y, datum - .01))
            r = roads.ray_cast(road_origin, down, 100)[0]
            surface = max(g.z, r.z if r is not None else -math.inf)
            # Check every <=10 cm from 5 cm above ground to 5 cm below datum.
            low, high = surface + .05, datum - .05
            if low > high:
                continue
            intervals = max(1, math.ceil((high - low) / .1))
            heights = [low + (high - low) * j / intervals for j in range(intervals + 1)]
            rows.append(dict(facade=index, xy=[x, y], normal=normal,
                             surfaceHeight=surface, heights=heights))
    if not rows:
        raise ValueError('No below-datum wall samples')
    return rows


def check(tree, rows):
    failures = []
    rays = 0
    for row in rows:
        x, y = row['xy']; nx, ny = row['normal']
        missing = []
        for z in row['heights']:
            rays += 1
            hit = tree.ray_cast(Vector((x + nx * .4, y + ny * .4, z)),
                                Vector((-nx, -ny, 0)), .8)[0]
            if hit is None:
                missing.append(z)
        if missing:
            failures.append(dict(facade=row['facade'], xy=row['xy'],
                                 ground=row['surfaceHeight'], missingHeights=missing))
    return dict(passed=not failures, facadeLocations=len(rows), rays=rays,
                openGapLocations=len(failures), failures=failures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--building-id', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--fail-on-gap', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    data = args.root / 'public/data/buildings.json'
    b = next(b for b in json.loads(data.read_text()) if b['id'] == args.building_id)
    paths = dict(source=args.root / 'blender/gxu-campus.blend',
                 base=args.root / 'public/models/base.glb',
                 near=args.root / f'public/models/{b["chunk"]}.glb')
    results = []
    for name, path in paths.items():
        if name == 'source':
            bpy.ops.wm.open_mainfile(filepath=str(path))
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.gltf(filepath=str(path))
        bpy.context.view_layer.update()
        objects = list(bpy.context.scene.objects)
        if name != 'near':
            ground, _ = top_tree([o for o in objects if layer(o) == 'terrain'])
            roads, _ = top_tree([o for o in objects if layer(o) == 'roads'])
            rows = probes(b, ground, roads)
        # The near chunk uses the same ground and probes as the base model.
        target = ([o for o in objects if o.get('featureId') == b['id']] if name == 'source'
                  else [o for o in objects if o.type == 'MESH' and layer(o) == 'buildings'])
        result = check(wall_tree(target), rows)
        results.append(dict(representation=name, **result))
    report = dict(buildingId=b['id'], datum=b['elevation'], representations=results,
                  passed=all(r['passed'] for r in results),
                  sampling=dict(horizontalSpacingMeters=2, verticalSpacingMaximumMeters=.1,
                                groundClearanceMeters=.05, facadeOffsetMeters=.02,
                                horizontalRayLengthMeters=.8),
                  limitations='Sampled model wall closure, not measured site elevations or proof of watertightness.',
                  fingerprints={k: hashlib.sha256(p.read_bytes()).hexdigest()
                                for k, p in dict(buildings=data, **paths).items()})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('WALL_GAPS', [(r['representation'], r['openGapLocations']) for r in results], flush=True)
    if args.fail_on_gap and not report['passed']:
        raise AssertionError('Open gaps under sampled facade walls')


if __name__ == '__main__':
    main()
