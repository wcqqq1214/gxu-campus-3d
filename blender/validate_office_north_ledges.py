"""Check the eight photo-constrained north facade ledges in actual artifacts."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]


def check(objects, building, tolerance):
    trees = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        triangles = list(obj.data.loop_triangles)
        tree = BVHTree.FromPolygons(
            [obj.matrix_world @ v.co for v in obj.data.vertices],
            [tuple(t.vertices) for t in triangles], all_triangles=True)
        materials = [obj.data.materials[t.material_index].name.split('.')[0]
                     for t in triangles]
        trees.append((tree, materials))
    rows = []
    # Independent dimensional expectations, not read from the proposed ledge rules.
    for edge, tops, depth, thickness in [
        (1, [9.9, 13.2], .38, .18),
        (3, [3.3, 6.6, 9.85], .28, .14),
        (11, [3.3, 6.6, 9.85], .28, .14),
    ]:
        facade = next(f for f in building['form']['facades'] if f['edge'] == edge)
        start, end = (Vector((*facade[k], 0)) for k in ('start', 'end'))
        normal = Vector((*facade['normal'], 0))
        for top in tops:
            for fraction in [.04, .25, .5, .75, .96]:
                point = start.lerp(end, fraction)
                origin = point + normal * (depth - .065)
                origin.z = building['elevation'] + top + .12
                hits = []
                for tree, materials in trees:
                    hit, n, index, distance = tree.ray_cast(origin, Vector((0, 0, -1)), .25)
                    if hit is not None:
                        hits.append((distance, hit, n, materials[index]))
                assert hits, ('missing projecting ledge', edge, top, fraction)
                _, hit, n, material = min(hits, key=lambda h: h[0])
                top_error = hit.z - building['elevation'] - top
                assert abs(top_error) <= tolerance
                assert n.z > .99 and material == 'white', (edge, top, fraction, n, material)
                # The face must project to the expected depth and have finite thickness.
                origin = point + normal * .8
                origin.z = building['elevation'] + top - thickness / 2
                hits = []
                for tree, _ in trees:
                    hit, _, _, distance = tree.ray_cast(origin, -normal, 1)
                    if hit is not None:
                        hits.append((distance, hit))
                assert hits, ('missing ledge front face', edge, top, fraction)
                distance, _ = min(hits, key=lambda h: h[0])
                assert abs(.8 - distance - depth) <= tolerance, (edge, top, fraction, distance)
                rows.append(dict(edge=edge, top=top, fraction=fraction,
                                 topError=top_error,
                                 projection=.8 - distance))
    return dict(passed=True, locations=len(rows), rays=len(rows) * 2,
                toleranceMeters=tolerance, samples=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    building = next(b for b in json.loads((args.root / 'public/data/buildings.json').read_text())
                    if b['id'] == 'way/671978896')
    paths = dict(source=args.root / 'blender/gxu-campus.blend',
                 base=args.root / 'public/models/base.glb',
                 near=args.root / f'public/models/{building["chunk"]}.glb')
    report = dict(passed=False, scope='Eight north-facing ledges; 40 locations, top and front face rays per representation.')
    try:
        for label, path in paths.items():
            if label == 'source':
                bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))
            else:
                bpy.ops.wm.read_factory_settings(use_empty=True)
                bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
            bpy.context.view_layer.update()
            def selected(obj):
                if label == 'source':
                    return obj.get('featureId') == building['id']
                while obj.parent:
                    obj = obj.parent
                return re.sub(r'\.\d+$', '', obj.name) == building['chunk']
            report[label] = check([o for o in bpy.context.scene.objects if selected(o)],
                                  building, dict(source=.006, base=.05, near=.02)[label])
        report['passed'] = True
    except Exception as error:
        report['failure'] = str(error)
        raise
    finally:
        report['fingerprints'] = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in paths.items()}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print('Office north ledges:', report['passed'], flush=True)


if __name__ == '__main__':
    main()
