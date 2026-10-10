"""Check photo-counted eastern fourth-floor windows on actual source and both shipping LODs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
ID = 'way/759185166'
CHUNK = 'chunk-p0-n1'
# Fixed mapped wall and estimated acceptance dimensions, not read from panels.
A = Vector((351.1322913092557, -331.5443559998629, 5.58))
B = Vector((313.7703710999319, -339.9712799998642, 5.58))
T = (B - A).normalized()
N = Vector((.22002141575468165, -.9754950418168743, 0))
UP = Vector((0, 0, 1))


def root_name(obj):
    while obj.parent:
        obj = obj.parent
    return obj.name


def check(objects, tolerance):
    trees = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        triangles = obj.data.loop_triangles
        trees.append((BVHTree.FromPolygons(
            [obj.matrix_world @ v.co for v in obj.data.vertices],
            [tuple(t.vertices) for t in triangles], all_triangles=True),
            [obj.data.materials[t.material_index].name.split('.')[0] for t in triangles]))
    samples = []

    def probe(kind, along, height, material, distance):
        origin = A + T * along + UP * height + N * .8
        hits = []
        for tree, materials in trees:
            hit = tree.ray_cast(origin, -N, 1.2)
            if hit[0] is not None:
                hits.append((hit[3], materials[hit[2]]))
        first = min(hits, default=None)
        if not first or first[1] != material or abs(first[0] - distance) > tolerance:
            raise AssertionError((kind, along, height, first, material, distance))
        samples.append(dict(kind=kind, alongMeters=along, height=height,
                            distance=first[0], material=first[1]))

    low, high = 10.8, 12.7
    transom = low + .06 + (high - low - .12) * .72
    for column in range(15):
        center = (B - A).length * (column + .5) / 15
        # Offset glass probes away from the central vertical mullion.
        probe('lower-left-glass', center - .3, low + .5, 'glass', .76)
        probe('lower-right-glass', center + .3, low + .5, 'glass', .76)
        probe('upper-glass', center + .3, high - .2, 'glass', .76)
        probe('left-frame', center - .795, low + .5, 'white', .65)
        probe('central-mullion', center, low + .5, 'white', .65)
        probe('transom-frame', center + .3, transom, 'white', .65)
        probe('wall-above', center, high + .18, 'stone', .8)
        probe('wall-below', center, low - .18, 'stone', .8)
    for column in range(1, 15):
        probe('wall-between-windows', (B - A).length * column / 15,
              low + .5, 'stone', .8)
    # The retained eastern return frame protrudes by 0.32m at the corner.
    for along in (.39, (B - A).length - .39):
        probe('wall-at-end', along, low + .5, 'stone', .8)
    return dict(passed=True, windows=15, rows=1, storey=4,
                sampleCount=len(samples), toleranceMeters=tolerance, samples=samples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    paths = dict(source=args.root / 'blender/gxu-campus.blend',
                 base=args.root / 'public/models/base.glb',
                 near=args.root / f'public/models/{CHUNK}.glb')
    report = dict(passed=False, buildingId=ID,
                  method='Fixed wall endpoints, independent 15-window fourth-storey acceptance stations; BVH on actual loop triangles',
                  scope='Photo-supported count; estimated dimensions and exterior glazing, not measured construction')
    try:
        for label, path in paths.items():
            if label == 'source':
                bpy.ops.wm.open_mainfile(filepath=str(path))
                objects = [o for o in bpy.context.scene.objects if o.get('featureId') == ID]
            else:
                bpy.ops.wm.read_factory_settings(use_empty=True)
                bpy.ops.import_scene.gltf(filepath=str(path))
                bpy.context.view_layer.update()
                objects = [o for o in bpy.context.scene.objects
                           if label == 'near' or root_name(o) == CHUNK]
            report[label] = check(objects, {'source': .012, 'base': .035, 'near': .02}[label])
        report['passed'] = True
    except Exception as error:
        report['failure'] = str(error)
    report['fingerprints'] = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in paths.items()}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Agriculture fourth-floor windows:', report['passed'], report.get('failure', ''), flush=True)
    if not report['passed']:
        raise AssertionError(report['failure'])


if __name__ == '__main__':
    main()
