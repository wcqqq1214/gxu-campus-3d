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
from road_surface_clearance import load_repairs


def surface_bvh(name, material=None):
    obj, = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.split('.')[0] == name]
    obj.data.calc_loop_triangles()
    vertices = [tuple(obj.matrix_world @ v.co) for v in obj.data.vertices]
    faces = [tuple(t.vertices) for t in obj.data.loop_triangles
             if material is None or obj.data.materials[t.material_index].name == material]
    return BVHTree.FromPolygons(vertices, faces, all_triangles=True)


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
        polygon = cut['polygon']
        if all(((b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0]))
               / ((b[0]-a[0])**2+(b[1]-a[1])**2)**.5 > -margin
               for a,b in zip(polygon,polygon[1:]+polygon[:1])):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-root', type=Path, required=True)
    parser.add_argument('--candidate-root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--cut-id', action='append', help='Validate only cuts newly applied to this baseline')
    parser.add_argument('--repair-clearance', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    cuts = load_cuts(ids=args.cut_id)
    config = json.loads((ROOT/'data/road-display-cleanup.json').read_text())
    repairs = load_repairs() if args.repair_clearance else []
    def repair_point(point):
        return any(r['bounds'][0]-.08 <= point[0] <= r['bounds'][2]+.08
                   and r['bounds'][1]-.08 <= point[1] <= r['bounds'][3]+.08 for r in repairs)
    report = {}
    for kind, relative, source in [('source', 'blender/gxu-campus.blend', True),
                                   ('decoded', 'public/models/base.glb', False)]:
        vertices, faces, before = load(args.baseline_root.resolve()/relative, source)
        old_asphalt = surface_bvh('roads', 'asphalt') if repairs else None
        _, _, after = load(args.candidate_root.resolve()/relative, source)
        new_asphalt = surface_bvh('roads', 'asphalt') if repairs else None
        terrain = surface_bvh('terrain') if repairs else None
        kept = removed = boundary = 0
        maximum = boundary_maximum = repair_maximum = 0
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
                if repair_point(point):
                    repair_maximum = max(repair_maximum, delta)
                elif touched:
                    boundary += 1
                    boundary_maximum = max(boundary_maximum, delta)
                else:
                    maximum = max(maximum, delta)
                if delta > (.02 if touched and not source else .002) and not repair_point(point):
                    problems.append(('height changed', point, old.z, new.z))
        assert not problems, (kind, len(problems), problems[:10])
        assert kept > 50_000 and removed > 0, (kind, kept, removed)
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
                            maxBoundaryHeightDelta=boundary_maximum, maxRepairHeightDelta=repair_maximum)
        repaired_samples = old_pokes = 0
        minimum_clearance = float('inf')
        for repair in repairs:
            x0,y0,x1,y1 = repair['bounds']
            for ix in range(int((x1-x0)*2)):
                for iy in range(int((y1-y0)*2)):
                    x,y = x0+(ix+.5)/2,y0+(iy+.5)/2
                    old,new,ground = ray(old_asphalt,x,y),ray(new_asphalt,x,y),ray(terrain,x,y)
                    if old is None or ground is None:
                        continue
                    assert new is not None, ('repair left hole',kind,x,y)
                    delta = new.z-ground.z
                    assert delta > .03, ('terrain pokes through',kind,x,y,delta)
                    minimum_clearance = min(minimum_clearance,delta)
                    repaired_samples += 1
                    old_pokes += old.z <= ground.z
            for point in repair['probes']:
                old,new,ground = ray(old_asphalt,*point),ray(new_asphalt,*point),ray(terrain,*point)
                assert old is not None and ground is not None and old.z < ground.z, ('baseline spot missing',kind,point)
                assert new is not None and new.z-ground.z > .03, ('spot remains',kind,point)
        if repairs:
            assert old_pokes > 100 and repaired_samples > 1000
            report[kind]['clearance'] = dict(samples=repaired_samples,oldPokes=old_pokes,minClearance=minimum_clearance)
        print(kind, report[kind], flush=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({'passed': True, **report}, indent=2)+'\n')


if __name__ == '__main__':
    main()
