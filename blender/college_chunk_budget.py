"""Optimize only the four reviewed building chunks, after ordinary GLB export."""

import copy
import math
from pathlib import Path

import numpy as np

from campus_draco import decode, encode
from gltf_bounds import compact_glb_float_bounds
from preserve_glb_geometry import (
    compact_buffer_views,
    compact_static_accessors,
    mesh_nodes_by_name,
    pack_glb,
    unpack,
)

NEAR = {'chunk-n2-n3', 'chunk-p0-n3'}
FAR = {'chunk-n2-n3', 'chunk-p0-n2'}
DRACO = 'KHR_draco_mesh_compression'


def view_bytes(doc, binary, primitive):
    view = doc['bufferViews'][primitive['extensions'][DRACO]['bufferView']]
    offset = view.get('byteOffset', 0)
    return binary[offset : offset + view['byteLength']]


def node_size(doc, node):
    views = {
        p['extensions'][DRACO]['bufferView']
        for p in doc['meshes'][node['mesh']]['primitives']
    }
    return sum(doc['bufferViews'][v]['byteLength'] for v in views)


def simple_finish(material):
    # Unknown material extensions can consume UVs even without a texture slot.
    from io_scene_gltf2.io.com.gltf2_io import Material

    from export_attributes import needs_texcoords

    return not material.get('extensions') and not needs_texcoords(
        Material.from_dict(material)
    )


def canonical_triangles(xyz, faces, reference):
    # Map decoded corners onto the nearest original coordinate per axis. The
    # original Draco position grid spaces neighboring levels far beyond roundoff.
    ids = []
    coordinates = []
    for axis, levels in enumerate(reference):
        q = xyz[:, axis]
        right = np.minimum(np.searchsorted(levels, q), len(levels) - 1)
        left = np.maximum(right - 1, 0)
        k = np.where(np.abs(q - levels[left]) < np.abs(q - levels[right]), left, right)
        ids.append(k)
        coordinates.append(levels[k])
    ids = np.ravel_multi_index(ids, [len(v) for v in reference])
    err = np.linalg.norm(xyz - np.column_stack(coordinates), axis=1)
    t = ids[faces]
    # Lexicographically least cyclic rotation retains winding, even for
    # repeated corners in a zero-area source triangle.
    order = np.zeros(len(t), dtype=int)
    best = t.copy()
    for n in (1, 2):
        cand = np.roll(t, -n, axis=1)
        less = (cand[:, 0] < best[:, 0]) | (
            (cand[:, 0] == best[:, 0])
            & (
                (cand[:, 1] < best[:, 1])
                | ((cand[:, 1] == best[:, 1]) & (cand[:, 2] < best[:, 2]))
            )
        )
        best[less] = cand[less]
        order[less] = n
    perm = np.lexsort((best[:, 2], best[:, 1], best[:, 0]))
    return best[perm], perm, order, float(err.max(initial=0))


def face_normals(xyz, faces):
    t = xyz[faces].astype(np.float64)
    cross = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    length = np.linalg.norm(cross, axis=1)
    return cross / np.maximum(length[:, None], 1e-20), length


def certify(before, old_faces, after, new_faces, *, exact=False):
    # Compare every oriented triangle in this material/normal group, then its
    # three corner normals. Ambiguous coincident triangles retain the original
    # primitive whenever this conservative matching cannot prove equivalence.
    ref = [np.unique(before['POSITION'][:, i]) for i in range(3)]
    old, oi, rot, _ = canonical_triangles(before['POSITION'], old_faces, ref)
    new, ni, nrot, error = canonical_triangles(after['POSITION'], new_faces, ref)
    if not np.array_equal(old, new) or error > 0.00075:
        return None

    def ordered(a, f, p, r):
        return a[f[np.arange(len(f))[:, None], (np.arange(3) + r[:, None]) % 3]][p]

    if exact:
        # Match every authored corner of the oriented triangles, including
        # normals on coincident faces and any UV seams. Ambiguity rejects.
        if before.keys() != after.keys() or any(
            not np.array_equal(
                ordered(before[key], old_faces, oi, rot),
                ordered(after[key], new_faces, ni, nrot),
            )
            for key in before
        ):
            return None
    original = ordered(before['NORMAL'], old_faces, oi, rot)
    if 'NORMAL' in after:
        current = ordered(after['NORMAL'], new_faces, ni, nrot)
        # Co-located degenerate triangles can have ambiguous corner order. A
        # failed validation falls back to the unmodified compressed primitive.
    else:
        norm, length = face_normals(after['POSITION'], new_faces)
        if np.any(length < 1e-9):
            return None
        current = norm[ni, None, :]
    dot = (original * current).sum(axis=2)
    dot /= np.maximum(
        np.linalg.norm(original, axis=2) * np.linalg.norm(current, axis=2), 1e-12
    )
    angle = float(np.degrees(np.arccos(np.clip(dot.min(), -1, 1))))
    if angle > (2.05 if 'NORMAL' not in after else 0.10):
        return None
    return error, angle


def encode_faces(attrs, faces, flat, far, *, keep_corners=False):
    keys = (
        list(attrs)
        if keep_corners
        else (['POSITION'] if flat else ['POSITION', 'NORMAL'])
    )
    # Weld only identical retained attributes. Include unused source extrema
    # for the position domain, as in vertex_dedup.share_position_quantization_bounds.
    used, local = np.unique(faces, return_inverse=True)
    data = np.column_stack([attrs[k][used] for k in keys])
    _, first, inverse = np.unique(
        data.view('V' + str(data.strides[0])).ravel(),
        return_index=True,
        return_inverse=True,
    )
    indices = used[first]
    ix = inverse[local].reshape(-1, 3)
    if keep_corners:
        # Draco drops repeated-index triangles. Give each corner of such a
        # source triangle its own index, retaining identical attribute values.
        collapsed = np.any(ix == np.roll(ix, 1, axis=1), axis=1)
        extra = faces[collapsed].ravel()
        ix[collapsed] = np.arange(len(indices), len(indices) + len(extra)).reshape(
            -1, 3
        )
        indices = np.concatenate((indices, extra))
    anchors = np.r_[attrs['POSITION'].argmin(axis=0), attrs['POSITION'].argmax(axis=0)]
    indices = np.concatenate((indices, anchors))
    compact = {k: np.ascontiguousarray(attrs[k][indices]) for k in keys}
    blob, ids, _, _ = encode(compact, ix, 15 if far else 16, 6 if far else 10, 12)
    after, triangles = decode(blob, ids)
    verified = certify(attrs, faces, after, triangles, exact=keep_corners)
    return (blob, ids, after, triangles.size, verified) if verified else None


def optimize_node(doc, binary, node, far, *, retry_before_view=None, textured=False):
    mesh = doc['meshes'][node['mesh']]
    output = []
    changes = []
    for prim in mesh['primitives']:
        material = doc['materials'][prim['material']]
        name = material['name']
        ext = prim['extensions'][DRACO]
        keys = set(prim['attributes'])
        if retry_before_view is not None and ext['bufferView'] >= retry_before_view:
            output.append(prim)
            continue
        original = view_bytes(doc, binary, prim)
        # Finished signs and every sampled image stay byte-identical in near
        # chunks. Geometry that uses a custom attribute or extension stays intact.
        protected = not far and any(
            t in name.lower()
            for t in ('shaw', 'letter', 'plaque', 'sign', 'glyph', 'board')
        )
        eligible_material = simple_finish(material)
        if textured:
            eligible_material = not material.get('extensions') and keys == {
                'POSITION',
                'NORMAL',
                'TEXCOORD_0',
            }
        eligible = (
            eligible_material
            and not protected
            and keys in ({'POSITION', 'NORMAL'}, {'POSITION', 'NORMAL', 'TEXCOORD_0'})
            and set(prim.get('extensions', {})) == {DRACO}
            and not prim.get('targets')
            and prim.get('mode', 4) == 4
        )
        if not eligible or len(original) < 512:
            output.append(prim)
            continue
        attrs, faces = decode(original, ext['attributes'])
        retry = retry_before_view is not None
        if retry:
            groups = [(faces, False)]
        elif far:
            fn, area = face_normals(attrs['POSITION'], faces)
            normals = attrs['NORMAL'][faces]
            # Flat derivatives exactly follow the triangle plane in GLTFLoader.
            # Curves, narrow bevels and authored smooth normals keep NORMAL.
            flat = (
                (area > 1e-8)
                & (
                    np.min((normals * fn[:, None, :]).sum(axis=2), axis=1)
                    > math.cos(math.radians(2))
                )
                & np.all(normals == normals[:, :1, :], axis=(1, 2))
            )
            groups = [(faces[flat], True), (faces[~flat], False)]
        else:
            groups = [(faces, False)]
        parts = [
            encode_faces(attrs, subset, flat, far, keep_corners=retry)
            for subset, flat in groups
            if len(subset)
        ]
        if any(part is None for part in parts) or sum(
            len(part[0]) for part in parts
        ) >= len(original):
            output.append(prim)
            continue
        for blob, ids, decoded, count, _ in parts:
            binary.extend(b'\0' * (-len(binary) % 4))
            idx = len(doc['bufferViews'])
            doc['bufferViews'].append(
                dict(buffer=0, byteOffset=len(binary), byteLength=len(blob))
            )
            binary.extend(blob)
            q = copy.deepcopy(prim)
            q['extensions'][DRACO] = dict(bufferView=idx, attributes=ids)
            q['attributes'] = {}
            for k, a in decoded.items():
                ac = copy.deepcopy(doc['accessors'][prim['attributes'][k]])
                ac['count'] = len(a)
                if 'min' in ac:
                    ac['min'] = a.min(axis=0).tolist()
                if 'max' in ac:
                    ac['max'] = a.max(axis=0).tolist()
                q['attributes'][k] = len(doc['accessors'])
                doc['accessors'].append(ac)
            ac = copy.deepcopy(doc['accessors'][prim['indices']])
            ac['count'] = count
            ac.pop('min', None)
            ac.pop('max', None)
            q['indices'] = len(doc['accessors'])
            doc['accessors'].append(ac)
            output.append(q)
        changes.append(
            dict(
                material=name,
                before=len(original),
                after=sum(len(t[0]) for t in parts),
                triangles=len(faces),
                maxPositionMeters=max(t[4][0] for t in parts),
                maxNormalDegrees=max(t[4][1] for t in parts),
            )
        )
    mesh['primitives'] = output
    return changes


def optimize_export(path):
    path = Path(path)
    far = path.name == 'base.glb'
    if not far and path.stem not in NEAR:
        return {}
    raw = path.read_bytes()
    if not far and len(raw) < 2_000_000:
        return {}
    doc, binary = unpack(raw)
    binary = bytearray(binary)
    out = {}
    if doc.get('skins') or doc.get('animations'):
        raise ValueError('Expected static campus chunks')
    nodes = mesh_nodes_by_name(doc)
    for name in sorted(FAR if far else {path.stem}):
        if name not in nodes:
            continue
        node = nodes[name]
        size = node_size(doc, node)
        if far and size <= 300_000:
            continue
        original_view_count = len(doc['bufferViews'])
        changes = optimize_node(doc, binary, node, far)
        if far and node_size(doc, node) > 300_000:
            # The existing split has already run. Retry only primitives still
            # using their source payload and keep all of their authored corners.
            changes.extend(
                optimize_node(
                    doc, binary, node, far, retry_before_view=original_view_count
                )
            )
        if far and node_size(doc, node) > 300_000:
            # Exact corner comparison includes all UVs, so sampled textures,
            # normals and seam duplicates survive this last budget pass.
            changes.extend(
                optimize_node(
                    doc,
                    binary,
                    node,
                    far,
                    retry_before_view=original_view_count,
                    textured=True,
                )
            )
        result = node_size(doc, node)
        out[name] = dict(before=size, after=result, changes=changes)
        if far and result > 300_000:
            raise ValueError(f'{name}: {result} > 300000')
    if not out:
        return {}
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix='.college-chunks-', dir=path.parent) as temp:
        target = Path(temp) / path.name
        target.write_bytes(pack_glb(doc, binary))
        compact_static_accessors(target)
        compact_buffer_views(target)
        compact_glb_float_bounds(target)
        if not far and target.stat().st_size >= 2_000_000:
            raise ValueError(f'{path.name}: {target.stat().st_size} >= 2000000')
        if far:
            from incremental_glb import validate_retained

            validate_retained(raw, target.read_bytes(), set(out))
        target.replace(path)
    return out
