"""Export-only terrain retriangulation with fixed boundaries and plane bounds.

Run after quantized zero-area cleanup. Nothing moves: only almost coplanar,
upward, globally XY/4-textured connected patches can be retriangulated. The
editable mesh is restored even if the caller's export fails.
"""
from collections import Counter, defaultdict
from contextlib import contextmanager
import math

import bmesh
import bpy
from mathutils import Matrix
import numpy as np

PLANE_ERROR = .0001  # metres; two surfaces can differ by at most twice this
NORMAL_ERROR = .0006  # reserve room within .001 for Blender's split-normal storage
POSITION_BITS = 18


def quantized_positions(vertices, triangles):
    """Mirror existing terrain cleanup's Float32 Y-up Draco position domain."""
    xyz = vertices.astype(np.float32)[:, [0, 2, 1]].copy()
    xyz[:, 2] *= -1
    used = xyz[np.unique(triangles)]
    minimum, maximum = used.min(axis=0), used.max(axis=0)
    extent = np.float32((maximum-minimum).max())
    maximum_value = (1 << POSITION_BITS)-1
    grid = np.floor((xyz-minimum)*np.float32(maximum_value/float(extent)) + np.float32(.5))
    decoded = (grid*np.float32(float(extent)/maximum_value)+minimum).astype(np.float64)
    decoded = decoded[:, [0, 2, 1]]
    decoded[:, 1] *= -1
    return decoded


def boundary_chain(faces):
    chain = Counter()
    for face in faces:
        for a, b in zip(face, (*face[1:], face[0])):
            if a != b:
                chain[min(a, b), max(a, b)] += 1 if a < b else -1
    return {edge: count for edge, count in chain.items() if count}


def read_mesh(mesh):
    mesh.calc_loop_triangles()
    loops = np.array([tuple(t.loops) for t in mesh.loop_triangles])
    return {
        'vertices': np.array([tuple(v.co) for v in mesh.vertices]),
        'triangles': np.array([tuple(t.vertices) for t in mesh.loop_triangles]),
        'uvs': np.array([tuple(d.uv) for d in mesh.uv_layers.active.data])[loops],
        'normals': np.array([tuple(d.vector) for d in mesh.corner_normals])[loops],
        'materials': np.array([mesh.polygons[t.polygon_index].material_index
                               for t in mesh.loop_triangles]),
        'polygon_ids': np.array([t.polygon_index for t in mesh.loop_triangles]),
    }


def simplify_mesh_arrays(source):
    unique, canonical, vertex_map = {}, [], []
    for point in source['vertices']:
        key = tuple(point)
        if key not in unique:
            unique[key] = len(canonical)
            canonical.append(key)
        vertex_map.append(unique[key])
    xyz = np.array(canonical)
    faces = np.array(vertex_map)[source['triangles']]
    uv, normals, materials = (source[k] for k in ('uvs', 'normals', 'materials'))
    points = xyz[faces]
    decoded = quantized_positions(xyz, faces)
    decoded_points = decoded[faces]
    decoded_cross = np.cross(decoded_points[:, 1]-decoded_points[:, 0], decoded_points[:, 2]-decoded_points[:, 0])
    cross = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
    area = cross[:, 2] / 2
    eligible = ((cross[:, 2] > .99 * np.linalg.norm(cross, axis=1))
                & (area > 1e-12)
                & (decoded_cross[:, 2] > 0)
                & np.all(uv == points[:, :, :2] / 4, axis=(1, 2)))
    incidence = defaultdict(list)
    for i, face in enumerate(faces):
        for a, b in zip(face, np.roll(face, -1)):
            incidence[tuple(sorted((int(a), int(b))))].append(i)
    edges = [tuple(ids) for ids in incidence.values()
             if len(ids) == 2 and all(eligible[i] for i in ids)
             and materials[ids[0]] == materials[ids[1]]]
    edges.sort(key=lambda ids: (-max(area[list(ids)]), ids))
    parent = list(range(len(faces)))
    members = {i: set(map(int, f)) for i, f in enumerate(faces) if eligible[i]}
    normal_min, normal_max = normals.min(axis=1), normals.max(axis=1)
    slopes = -cross[:, :2] / np.where(cross[:, 2:] != 0, cross[:, 2:], 1)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in edges:
        a, b = find(i), find(j)
        if a == b:
            continue
        # The root is always the largest original triangle, never an averaged
        # plane that could drift during successive merges.
        if area[b] > area[a]:
            a, b = b, a
        q, p = xyz[sorted(members[b])], points[a, 0]
        residual = q[:, 2] - p[2] - (q[:, :2] - p[:2]) @ slopes[a]
        if np.max(np.abs(residual)) > PLANE_ERROR:
            continue
        lo = np.minimum(normal_min[a], normal_min[b])
        hi = np.maximum(normal_max[a], normal_max[b])
        n = normals[a, 0]
        if np.linalg.norm(np.maximum(np.abs(lo - n), np.abs(hi - n))) > NORMAL_ERROR:
            continue
        parent[b] = a
        members[a].update(members.pop(b))
        normal_min[a], normal_max[a] = lo, hi

    groups = defaultdict(list)
    for i in range(len(faces)):
        groups[find(i)].append(i)
    polygon_faces = defaultdict(set)
    for i, polygon in enumerate(source['polygon_ids']):
        polygon_faces[int(polygon)].add(i)
    patches = []
    output, out_uv, out_normal, out_material, records = [], [], [], [], []
    for root, ids in groups.items():
        original, replacement = faces[ids], None
        id_set = set(ids)
        complete_polygons = all(polygon_faces[int(source['polygon_ids'][i])] <= id_set for i in ids)
        if len(ids) >= 3 and eligible[root] and complete_polygons:
            bm = bmesh.new()
            try:
                verts = {i: bm.verts.new(xyz[i]) for i in sorted(members[root])}
                valid = True
                try:
                    for face in original:
                        bm.faces.new([verts[int(i)] for i in face])
                except ValueError:
                    valid = False  # duplicated faces are retained, not repaired
                if valid:
                    bm.normal_update()
                    protected = {i for i, v in verts.items() if v.is_boundary}
                    bmesh.ops.dissolve_limit(
                        bm, angle_limit=math.pi / 2, use_dissolve_boundaries=False,
                        verts=[v for v in bm.verts if not v.is_boundary and v.is_manifold],
                        edges=[e for e in bm.edges if e.is_manifold], delimit=set())
                    bmesh.ops.triangulate(bm, faces=list(bm.faces))
                    candidate = [[unique[tuple(v.co)] for v in f.verts] for f in bm.faces]
                    if (len(candidate) < len(original)
                            and boundary_chain(candidate) == boundary_chain(original.tolist())
                            and protected <= {i for f in candidate for i in f}):
                        p = xyz[np.array(candidate)]
                        c = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
                        q = decoded[np.array(candidate)]
                        quantized_cross = np.cross(q[:, 1]-q[:, 0], q[:, 2]-q[:, 0])
                        if np.all(c[:, 2] > 0) and np.all(quantized_cross[:, 2] > 0):
                            replacement = candidate
            finally:
                bm.free()
        if replacement is None:
            output.extend(original.tolist())
            out_uv.extend(uv[ids].tolist())
            out_normal.extend(normals[ids].tolist())
            out_material.extend(materials[ids].tolist())
        else:
            output.extend(replacement)
            out_uv.extend((xyz[np.array(replacement), :2] / 4).tolist())
            out_normal.extend([[normals[root, 0].tolist()] * 3 for _ in replacement])
            out_material.extend([int(materials[root])] * len(replacement))
            records.append({'oldFaces': len(ids), 'newFaces': len(replacement), 'seed': root})
            patches.append({'polygons': sorted(set(map(int, source['polygon_ids'][ids]))),
                            'faces': replacement, 'material': int(materials[root]),
                            'normal': normals[root, 0].tolist(),
                            'normalMin': normal_min[root], 'normalMax': normal_max[root]})

    triangles = np.array(output)
    old_used, new_used = points.reshape(-1, 3), xyz[triangles].reshape(-1, 3)
    if not (np.array_equal(old_used.min(axis=0), new_used.min(axis=0))
            and np.array_equal(old_used.max(axis=0), new_used.max(axis=0))):
        raise ValueError('Terrain position bounds changed; reject candidate')
    result = dict(vertices=xyz, triangles=triangles, uvs=np.array(out_uv),
                  normals=np.array(out_normal), materials=np.array(out_material))
    report = {'originalFaces': len(faces), 'candidateFaces': len(output),
              'removedFaces': len(faces) - len(output),
              'optimizedComponents': len(records), 'components': records,
              'planeErrorMetres': PLANE_ERROR, 'normalError': NORMAL_ERROR,
              'positionBoundsPreserved': True}
    result['patches'] = patches
    return result, report


@contextmanager
def planar_terrain_candidate(obj, *, dump_directory=None):
    original = obj.data
    if (obj.get('layer') != 'terrain' or obj.matrix_world != Matrix.Identity(4)
            or original.shape_keys or obj.modifiers or obj.vertex_groups
            or original.has_custom_normals or any(p.use_smooth for p in original.polygons)
            or len(original.uv_layers) != 1 or original.color_attributes):
        raise ValueError('Candidate requires plain, untransformed, flat terrain with one UV layer')
    supported = {'position', '.edge_verts', '.corner_vert', '.corner_edge',
                 'material_index', 'sharp_face', 'sharp_edge', original.uv_layers.active.name}
    if any(a.name not in supported and not a.name.startswith('.') for a in original.attributes):
        raise ValueError('Unsupported terrain attributes must be preserved explicitly')
    source = read_mesh(original)
    if len(set(source['materials'])) != 1:
        raise ValueError('Terrain quantization domain requires one material')
    result, report = simplify_mesh_arrays(source)
    temporary = bpy.data.meshes.new('terrain-planar-candidate')
    try:
        # Preserve original polygons, including nonplanar quads and their flat
        # normals. Rebuilding all original triangles with custom split normals
        # can change export shading at slender faces outside accepted patches.
        removed = {p for patch in result['patches'] for p in patch['polygons']}
        vertices = source['vertices'].tolist()
        faces, uvs, materials, smooth, normals = [], [], [], [], []
        for polygon in original.polygons:
            if polygon.index not in removed:
                faces.append(list(polygon.vertices))
                uvs.extend(tuple(original.uv_layers.active.data[i].uv) for i in polygon.loop_indices)
                materials.append(polygon.material_index)
                smooth.append(False)
                # A zero custom normal preserves Blender's automatic polygon
                # normal on unchanged faces, including original quads.
                normals.extend([(0, 0, 0)] * len(polygon.vertices))
        for patch in result['patches']:
            patch['loopStart'] = len(normals)
            for face in patch['faces']:
                points = result['vertices'][face]
                at = len(vertices)
                vertices.extend(points.tolist())
                faces.append([at, at+1, at+2])
                uvs.extend((points[:, :2]/4).tolist())
                materials.append(patch['material'])
                smooth.append(True)
                normals.extend([patch['normal']] * 3)
            patch['loopEnd'] = len(normals)
        temporary.from_pydata(vertices, [], faces)
        for material in original.materials:
            temporary.materials.append(material)
        temporary.polygons.foreach_set('material_index', materials)
        temporary.polygons.foreach_set('use_smooth', smooth)
        layer = temporary.uv_layers.new(name=original.uv_layers.active.name)
        layer.data.foreach_set('uv', np.array(uvs).ravel())
        temporary.normals_split_custom_set(normals)
        temporary.update()
        actual_normals = np.array([tuple(n.vector) for n in temporary.corner_normals])
        maximum_stored_error = 0.
        for patch in result['patches']:
            actual = actual_normals[patch['loopStart']:patch['loopEnd']]
            error = np.linalg.norm(np.maximum(np.abs(actual-patch['normalMin']),
                                             np.abs(actual-patch['normalMax'])), axis=1).max()
            maximum_stored_error = max(maximum_stored_error, float(error))
        # This pairs every new corner with an entire component's normal box,
        # including distant faces that never overlap. Keep it diagnostic; the
        # independent overlap checker enforces .001 at corresponding positions.
        report['maximumStoredNormalEnvelope'] = maximum_stored_error
        actual_uv = np.array(uvs)
        old_uv = source['uvs'].reshape(-1, 2)
        if not (np.array_equal(actual_uv.min(axis=0), old_uv.min(axis=0))
                and np.array_equal(actual_uv.max(axis=0), old_uv.max(axis=0))):
            raise ValueError('Terrain UV quantization domain changed')
        report['uvBoundsPreserved'] = True
        if dump_directory is not None:
            dump_directory.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(dump_directory / 'original.npz', **source)
            np.savez_compressed(dump_directory / 'candidate.npz', **read_mesh(temporary))
        obj.data = temporary
        yield report
    finally:
        obj.data = original
        bpy.data.meshes.remove(temporary)
