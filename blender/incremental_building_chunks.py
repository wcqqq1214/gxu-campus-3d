"""Replace surveyed buildings inside joined, static campus GLB chunks."""

import numpy as np
from mathutils.kdtree import KDTree

from campus_draco import decode, encode
from college_chunk_budget import DRACO, view_bytes
from incremental_glb import pack, splice_nodes
from preserve_glb_geometry import mesh_nodes_by_name, unpack


def single_node(raw, name):
    doc, buffer = unpack(raw)
    node = mesh_nodes_by_name(doc)[name]
    doc['nodes'] = [node]
    doc['scenes'][0]['nodes'] = [0]
    selected = pack(doc, buffer)
    return splice_nodes(selected, selected, {name})


def corner_signature(attrs, faces):
    """Sort exact oriented triangle corners, including every decoded attribute."""
    values = np.column_stack([attrs[key] for key in sorted(attrs)])
    tris = np.ascontiguousarray(values[faces])
    corners = tris.view(f'V{tris.strides[1]}').reshape(-1, 3)
    rotations = [
        np.ascontiguousarray(np.roll(corners, i, axis=1)).view(f'V{tris.strides[0]}')
        for i in range(3)
    ]
    return np.sort(np.sort(np.column_stack(rotations), axis=1)[:, 0])


def same_triangles(before, faces, after, triangles):
    if len(faces) != len(triangles):
        return False
    keys = sorted(before)
    tolerances = {'POSITION': 0.0006, 'NORMAL': 0.0006, 'TEXCOORD_0': 0.00015}
    a = np.column_stack([before[k].astype(float) / tolerances[k] for k in keys])[faces]
    b = np.column_stack([after[k].astype(float) / tolerances[k] for k in keys])[
        triangles
    ]
    index = KDTree(len(faces))
    for i, center in enumerate(before['POSITION'][faces].mean(axis=1)):
        index.insert(center, i)
    index.balance()
    used = set()
    for tri, center in zip(b, after['POSITION'][triangles].mean(axis=1)):
        for _, i, _ in index.find_range(center, 0.0013):
            if i not in used and any(
                np.max(np.abs(tri - a[i][roll])) <= 1
                for roll in ([0, 1, 2], [1, 2, 0], [2, 0, 1])
            ):
                used.add(i)
                break
        else:
            return False
    return True


def retained_primitive(doc, buf, prim, attrs, faces, far):
    reference = corner_signature(attrs, faces)
    # Try the standard and historical encoder grids before lossless float coding.
    settings = [
        (15, 6, 12) if far else (16, 10, 12),
        (18, 10, 16),
        (20, 14, 18),
        (21, 14, 21),
        (24, 16, 24),
        (0, 0, 0),
    ]
    for setting in settings:
        blob, ids, count, index_count = encode(attrs, faces, *setting)
        after, tris = decode(blob, ids)
        if np.array_equal(reference, corner_signature(after, tris)):
            break
        # When original quantization bounds are unavailable, certify the
        # entire oriented corner multiset to half a millimetre in each axis.
        if same_triangles(attrs, faces, after, tris):
            break
    else:
        raise ValueError('Could not preserve oriented corners of neighbouring geometry')
    buf.extend(b'\0' * (-len(buf) % 4))
    index = len(doc['bufferViews'])
    doc['bufferViews'].append(dict(buffer=0, byteOffset=len(buf), byteLength=len(blob)))
    buf.extend(blob)
    prim['extensions'][DRACO] = dict(bufferView=index, attributes=ids)
    for key, array in after.items():
        accessor = dict(doc['accessors'][prim['attributes'][key]], count=count)
        if 'min' in accessor:
            accessor.update(
                min=array.min(axis=0).tolist(), max=array.max(axis=0).tolist()
            )
        prim['attributes'][key] = len(doc['accessors'])
        doc['accessors'].append(accessor)
    accessor = dict(doc['accessors'][prim['indices']], count=index_count)
    accessor.pop('min', None)
    accessor.pop('max', None)
    if count >= 65536:
        accessor['componentType'] = 5125
    prim['indices'] = len(doc['accessors'])
    doc['accessors'].append(accessor)


def inside_hull(points, hull):
    edges = np.roll(hull, -1, axis=0) - hull
    direction = np.sign(np.sum(hull[:, 0] * edges[:, 1] - hull[:, 1] * edges[:, 0]))
    mask = np.ones(len(points), dtype=bool)
    for a, edge in zip(hull, edges):
        delta = points - a
        mask &= direction * (
            edge[0] * delta[:, 1] - edge[1] * delta[:, 0]
        ) >= -0.15 * np.linalg.norm(edge)
    return mask


def replace_in_chunk(original, name, footprints, addition, *, far):
    """Cut only isolated old building bounds, then fold new parts into the zone node.

    Each hull is in Blender world XY, verified against the editable neighbours
    by the caller. A triangle crossing its boundary fails the update.
    """
    doc, raw = unpack(single_node(original, name))
    node = doc['nodes'][0]
    if any(key in node for key in ('matrix', 'translation', 'rotation', 'scale')):
        raise ValueError(f'{name} has a node transform')
    buf = bytearray(raw)
    mesh = doc['meshes'][node['mesh']]
    retained = []
    stats = dict(unchangedPrimitives=0, splitPrimitives=0, retainedTriangles=0)
    removed = dict.fromkeys(footprints, 0)
    for primitive in mesh['primitives']:
        ext = primitive['extensions'][DRACO]
        attrs, faces = decode(view_bytes(doc, raw, primitive), ext['attributes'])
        x, _, south = attrs['POSITION'].T
        selected = np.zeros(len(faces), dtype=bool)
        for fid, (hull, tree) in footprints.items():
            inside = inside_hull(np.column_stack((x, -south)), hull)
            if tree is not None:
                for i in np.flatnonzero(inside):
                    px, pz, ms = attrs['POSITION'][i]
                    _, label, _ = tree.find((px, -ms, pz))
                    inside[i] = label
            inside = inside[faces]
            hit = inside.any(axis=1)
            if np.any(hit != inside.all(axis=1)) or np.any(hit & selected):
                raise ValueError(f'{name}: ambiguous triangle membership for {fid}')
            removed[fid] += int(hit.sum())
            selected |= hit
        stats['retainedTriangles'] += int((~selected).sum())
        if selected.all():
            continue
        if selected.any():
            retained_primitive(doc, buf, primitive, attrs, faces[~selected], far)
            stats['splitPrimitives'] += 1
        else:
            stats['unchangedPrimitives'] += 1
        retained.append(primitive)
    if not all(removed.values()):
        raise ValueError(f'{name}: missing prior building geometry: {removed}')
    stats['removedTriangles'] = removed
    mesh['primitives'] = retained
    result = pack(doc, buf)
    if addition:
        add_doc, _ = unpack(addition)
        (part,) = mesh_nodes_by_name(add_doc)
        if part == name:
            raise ValueError('Expected a separate building part')
        merged, buf = unpack(splice_nodes(result, addition, {part}))
        nodes = mesh_nodes_by_name(merged)
        shell = merged['meshes'][nodes[name]['mesh']]
        shell['primitives'] += merged['meshes'][nodes[part]['mesh']]['primitives']
        result = pack(merged, buf)
    return single_node(result, name), stats
