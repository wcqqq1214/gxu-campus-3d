"""Audit full-width agriculture stairs against the actual adjacent road.

A mapped road already overlaps the steps in XY; an extra gap connector would
not fix its height mismatch. This diagnostic checks source/base/near geometry,
using base ground for the near building. It never edits production assets.
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
from inspect_foundation_clearance import layer


def owner(obj):
    while obj.parent:
        obj = obj.parent
    return obj


def sampler(objects):
    trees = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        trees.append(BVHTree.FromPolygons(
            [obj.matrix_world @ v.co for v in obj.data.vertices],
            [tuple(p.vertices) for p in obj.data.polygons]))

    def height(x, y, top, bottom):
        hits = [t.ray_cast(Vector((x, y, top)), Vector((0, 0, -1)), top-bottom)[0]
                for t in trees]
        return max((p.z for p in hits if p is not None), default=None)
    return height


def inspect(building, building_height, road_height, terrain_height, label):
    entry = next(e for e in building['form']['entrances'] if e['id'] == 'south-portico-door')
    steps = entry.get('steps', 3)
    step_base = entry.get('stepBaseHeight', 0)
    rise = (entry['platformHeight'] - step_base) / steps
    datum = building['elevation']
    angle = math.radians(entry['bearing'])
    normal = (math.sin(angle), math.cos(angle))
    tangent = (normal[1], -normal[0])
    origin = entry['outerCenter']
    width = entry.get('stepWidth', entry['porticoWidth'])
    # Match recessed stair generation: pitch .3 m, solid depth .32 m.
    toe = steps * .3 + .01
    count = math.ceil((width - .4) / .5)
    offsets = [-width/2 + .2 + (width-.4)*i/count for i in range(count+1)]
    rows, failures = [], []
    geometry_tolerance = .011 if label == 'source' else .025
    join_tolerance = .03

    def height(fn, x, distance):
        px = origin[0] + tangent[0]*x + normal[0]*distance
        py = origin[1] + tangent[1]*x + normal[1]*distance
        return fn(px, py, datum+entry['platformHeight']+.5, datum-10)

    for x in offsets:
        treads = [height(building_height, x, (i+.5)*.3) for i in range(steps)]
        under = [max(v for v in (height(road_height, x, (i+.5)*.3),
                                  height(terrain_height, x, (i+.5)*.3)) if v is not None)
                 for i in range(steps)]
        approach = [height(road_height, x, distance) for distance in (toe+.025, toe+.25, toe+1)]
        heights_ok = all(t is not None and abs(t-(datum+step_base+rise*(steps-i))) <= geometry_tolerance
                         for i,t in enumerate(treads))
        clearances = [t-g if t is not None else None for t,g in zip(treads,under)]
        join = treads[-1]-approach[0] if treads[-1] is not None and approach[0] is not None else None
        # The target is the already adopted model riser, not an accessibility
        # or building-code threshold. Positive midpoint clearance is insufficient.
        reasons = []
        if not heights_ok:
            reasons.append('missing or stale stair tread')
        if any(c is None or c < -geometry_tolerance for c in clearances):
            reasons.append('ground or road covers stair')
        if any(h is None for h in approach):
            reasons.append('missing approach road')
        if join is None or abs(join-rise) > join_tolerance:
            reasons.append('outer riser differs from adopted stair rise')
        row = dict(offset=x, treadHeights=treads, groundClearances=clearances,
                   approachRoadHeights=approach, outerRiser=join, reasons=reasons)
        rows.append(row)
        if reasons:
            failures.append(row)
    measured = [r['outerRiser'] for r in rows if r['outerRiser'] is not None]
    return dict(representation=label, passed=not failures, width=width,
                expectedRiser=rise, joinTolerance=join_tolerance,
                geometryTolerance=geometry_tolerance, transversePositions=len(rows),
                outerRiserRange=[min(measured),max(measured)] if measured else None,
                failures=failures, samples=rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--fail-on-mismatch', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    root = args.root.resolve()
    building = next(b for b in json.loads((root/'public/data/buildings.json').read_text())
                    if b['id'] == 'way/759185166')
    result = dict(buildingId=building['id'], surfaceId='way/759187871',
                  scope='Actual full-width stair-to-existing-road interface. Source and base ground checked; near building reuses base ground. No engineering or surveyed-elevation claim.',
                  representations=[])
    for label in ('source', 'base', 'near'):
        if label == 'source':
            bpy.ops.wm.open_mainfile(filepath=str(root/'blender/gxu-campus.blend'))
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            path = 'base.glb' if label == 'base' else building['chunk']+'.glb'
            bpy.ops.import_scene.gltf(filepath=str(root/'public/models'/path))
        bpy.context.view_layer.update()
        objects = list(bpy.context.scene.objects)
        if label != 'near':
            road = sampler([o for o in objects if layer(o) == 'roads'])
            terrain = sampler([o for o in objects if layer(o) == 'terrain'])
        selected = ([o for o in objects if o.get('featureId') == building['id']] if label == 'source'
                    else [o for o in objects if owner(o).name == building['chunk']] if label == 'base'
                    else objects)
        if not selected:
            raise ValueError('Missing target building '+label)
        result['representations'].append(inspect(building, sampler(selected), road, terrain, label))
    result['passed'] = all(r['passed'] for r in result['representations'])
    paths = ['public/data/buildings.json', 'blender/gxu-campus.blend', 'public/models/base.glb',
             'public/models/'+building['chunk']+'.glb']
    result['fingerprints'] = {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
    result['implementationSha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'representations'}),flush=True)
    if args.fail_on_mismatch and not result['passed']:
        raise AssertionError('Full-width agriculture stair/road mismatch; see '+str(args.report))


if __name__ == '__main__':
    main()
