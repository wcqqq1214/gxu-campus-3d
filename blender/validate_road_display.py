"""Compare road-tail cleanup with an actual pre-change source and GLB baseline."""
import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from road_display_cleanup import load_cuts


def load(path, source):
    if source:
        bpy.ops.wm.open_mainfile(filepath=str(path))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(path))
        bpy.context.view_layer.update()
    obj, = [o for o in bpy.context.scene.objects
            if o.type == 'MESH' and o.name.split('.')[0] == 'roads']
    obj.data.calc_loop_triangles()
    vertices = [tuple(obj.matrix_world @ v.co) for v in obj.data.vertices]
    faces = [tuple(t.vertices) for t in obj.data.loop_triangles]
    return vertices, faces, BVHTree.FromPolygons(vertices, faces, all_triangles=True)


def ray(bvh, x, y):
    return bvh.ray_cast(Vector((x, y, 200)), Vector((0, 0, -1)), 300)[0]


def in_cut(point, cuts, margin=0):
    for cut in cuts:
        x, y = cut['origin']
        dx, dy = cut['outward']
        length = (dx*dx + dy*dy)**.5
        dx, dy = dx/length, dy/length
        along = (point[0]-x)*dx + (point[1]-y)*dy
        across = -(point[0]-x)*dy + (point[1]-y)*dx
        if -margin < along < cut['length']+margin and abs(across) < cut['halfWidth']+margin:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-root', type=Path, required=True)
    parser.add_argument('--candidate-root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--cut-id', action='append', help='Validate only cuts newly applied to this baseline')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    cuts = load_cuts(ids=args.cut_id)
    config = json.loads((ROOT/'data/road-display-cleanup.json').read_text())
    report = {}
    for kind, relative, source in [('source', 'blender/gxu-campus.blend', True),
                                   ('decoded', 'public/models/base.glb', False)]:
        vertices, faces, before = load(args.baseline_root.resolve()/relative, source)
        _, _, after = load(args.candidate_root.resolve()/relative, source)
        kept = removed = boundary = 0
        maximum = boundary_maximum = 0
        problems = []
        for face in faces:
            point = tuple(sum(vertices[i][k] for i in face)/3 for k in range(3))
            old, new = ray(before, *point[:2]), ray(after, *point[:2])
            if old is None:
                continue
            if in_cut(point, cuts, -.08):
                removed += 1
                if new is not None:
                    problems.append(('tail remains', point))
            elif not in_cut(point, cuts, .08):
                if new is None:
                    problems.append(('retained road missing', point))
                    continue
                kept += 1
                # A cut triangle's newly interpolated vertices are snapped to
                # the existing ~1 cm Draco grid. Its surviving fragment may
                # move slightly; uncut triangles must retain their old plane.
                points = [vertices[i] for i in face]
                touched = any(max(p[0] for p in points) > c['bounds'][0]
                              and min(p[0] for p in points) < c['bounds'][2]
                              and max(p[1] for p in points) > c['bounds'][1]
                              and min(p[1] for p in points) < c['bounds'][3] for c in cuts)
                delta = abs(old.z-new.z)
                if touched:
                    boundary += 1
                    boundary_maximum = max(boundary_maximum, delta)
                else:
                    maximum = max(maximum, delta)
                if delta > (.02 if touched and not source else .002):
                    problems.append(('height changed', point, old.z, new.z))
        assert not problems, (kind, len(problems), problems[:10])
        assert kept > 50_000 and removed > 500, (kind, kept, removed)
        # Former road-tail witnesses detect a no-op build independently of the
        # clipping implementation. Junction centres detect accidental severing.
        for point in [c['removedProbe'] for c in cuts]:
            assert ray(before, *point) is not None, ('baseline tail missing', kind, point)
            assert ray(after, *point) is None, ('tail remains', kind, point)
        for point in config['retainedProbes']:
            assert ray(before, *point) is not None, ('baseline junction missing', kind, point)
            assert ray(after, *point) is not None, ('junction missing', kind, point)
        report[kind] = dict(retainedSamples=kept, removedSamples=removed,
                            boundarySamples=boundary, maxUncutHeightDelta=maximum,
                            maxBoundaryHeightDelta=boundary_maximum)
        print(kind, report[kind], flush=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({'passed': True, **report}, indent=2)+'\n')


if __name__ == '__main__':
    main()
