"""Apply one prepared, terrain-only foundation repair to an isolated source.

Keep unchanged source faces and their loop UVs. Changed faces must use the
existing XY/4 ground projection. Road cuts need their own export workflow.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
sys.path.insert(0, str(ROOT / 'scripts'))
from foundation_contract import load_foundations
from foundation_geometry import build_foundations
from geometry import Mesh


def source_mesh(obj):
    if obj.matrix_world != Matrix.Identity(4) or obj.modifiers:
        raise ValueError('Expected an untransformed source mesh without modifiers')
    result = Mesh()
    result.v = [tuple(v.co) for v in obj.data.vertices]
    result.f = [tuple(p.vertices) for p in obj.data.polygons]
    result.m = [p.material_index for p in obj.data.polygons]
    return result


def containing_xy_triangle(points, triangles, center):
    """Double-precision containment for thin triangles missed by the BVH."""
    x, y = center[:2]
    for index, ids in enumerate(triangles):
        a, b, c = (points[i] for i in ids)
        if not (min(a[0], b[0], c[0]) <= x <= max(a[0], b[0], c[0])
                and min(a[1], b[1], c[1]) <= y <= max(a[1], b[1], c[1])):
            continue
        area = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        if area == 0:
            continue
        sides = [(q[0]-p[0])*(y-p[1]) - (q[1]-p[1])*(x-p[0])
                 for p, q in ((a, b), (b, c), (c, a))]
        if min(sides) >= 0 or max(sides) <= 0:
            return index
    return None


def replace_terrain(obj, result):
    old = obj.data
    if len(old.uv_layers) != 1:
        raise ValueError('Expected exactly one terrain UV layer')
    old.calc_loop_triangles()
    lookup = {(tuple(tuple(old.vertices[i].co) for i in p.vertices), p.material_index):
              (p.use_smooth, [tuple(old.uv_layers.active.data[k].uv) for k in p.loop_indices])
              for p in old.polygons}
    flat = [Vector((v.co.x, v.co.y, 0)) for v in old.vertices]
    triangles = list(old.loop_triangles)
    tree = BVHTree.FromPolygons(flat, [tuple(t.vertices) for t in triangles], all_triangles=True)
    precise_xy = None
    mesh = bpy.data.meshes.new(old.name + '-foundation-repair')
    mesh.from_pydata(result.v, [], result.f)
    new_keys = {(tuple(tuple(mesh.vertices[i].co) for i in p.vertices), material)
                for p, material in zip(mesh.polygons, result.m)}
    for face in old.polygons:
        key = (tuple(tuple(old.vertices[i].co) for i in face.vertices), face.material_index)
        if key in new_keys:
            continue
        for k in face.loop_indices:
            point = old.vertices[old.loops[k].vertex_index].co
            if tuple(old.uv_layers.active.data[k].uv) != (point.x / 4, point.y / 4):
                raise ValueError('Changed terrain must use the original XY/4 projection')
    for material in old.materials:
        mesh.materials.append(material)
    uv = mesh.uv_layers.new(name=old.uv_layers.active.name)
    unchanged = projected = precise_fallbacks = 0
    for face, material in zip(mesh.polygons, result.m):
        face.material_index = material
        points = [mesh.vertices[i].co for i in face.vertices]
        prior = lookup.get((tuple(tuple(p) for p in points), material))
        if prior:
            face.use_smooth, values = prior
            unchanged += 1
        else:
            center = sum((Vector((p.x, p.y, 0)) for p in points), Vector()) / len(points)
            _, _, index, distance = tree.find_nearest(center)
            if index is None or distance > .0001:
                # A millimetre-wide end on a metre-long triangle can make the
                # float BVH return an edge distance for an interior point.
                # Require actual containment; do not enlarge the distance gate.
                if precise_xy is None:
                    precise_xy = [tuple(v.co[:2]) for v in old.vertices]
                index = containing_xy_triangle(precise_xy,
                                               (t.vertices for t in triangles), center)
                if index is None:
                    raise ValueError('Repaired terrain escaped the original XY surface')
                precise_fallbacks += 1
            tri = triangles[index]
            if tri.material_index != material:
                raise ValueError('Repair crossed an original terrain material boundary')
            values = [(p.x / 4, p.y / 4) for p in points]
            face.use_smooth = old.polygons[tri.polygon_index].use_smooth
            projected += 1
        for k, value in zip(face.loop_indices, values):
            uv.data[k].uv = value
    obj.data = mesh
    return {'unchangedFacesWithExactUVs': unchanged, 'projectedFaces': projected,
            'preciseContainmentFallbackFaces': precise_fallbacks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--foundation-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = args.output.resolve()
    source = ROOT / 'blender/gxu-campus.blend'
    if output == source.resolve() or output.exists():
        raise ValueError('Use a new isolated candidate file')
    record = next(r for r in load_foundations(ROOT)['foundations'] if r['id'] == args.foundation_id)
    if record['trimmedRoadArea'] > 1e-7:
        raise ValueError('This candidate tool only supports terrain-only repairs')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    terrain, roads = (source_mesh(bpy.data.objects[n]) for n in ('terrain', 'roads'))
    repaired, retained, report = build_foundations({'foundations': [record]}, terrain, roads)
    if (retained.v, retained.f, retained.m) != (roads.v, roads.f, roads.m):
        raise ValueError('Unexpected road change')
    mapping = replace_terrain(bpy.data.objects['terrain'], repaired)
    # Keep original image path strings when the validated file is promoted.
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True, relative_remap=False)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({'foundationId': args.foundation_id, 'build': report,
                                      'uvMapping': mapping, 'roadsUnchanged': True}, indent=2) + '\n')


if __name__ == '__main__':
    main()
