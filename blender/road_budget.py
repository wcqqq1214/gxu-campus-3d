"""Fit the aggregate road using the existing path triangles and their full corners."""

import copy
import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from campus_draco import decode, encode
from incremental_glb import splice_nodes, validate_retained
from initial_model_budget import load_model_budget
from preserve_glb_geometry import mesh_nodes_by_name, pack_glb, unpack
from terrain_budget import triangle_digest

DRACO = 'KHR_draco_mesh_compression'
LIMIT = load_model_budget()['baseLayerLimitBytes']['roads']


def road_domain(path, root):
    return json.loads(
        subprocess.check_output(
            [
                'node',
                str(root / 'scripts/road-position-domain.mjs'),
                str(path.resolve()),
            ],
            cwd=root,
        )
    )


def _repack_material(raw, path, root, material):
    doc, binary = unpack(raw)
    node = mesh_nodes_by_name(doc)['roads']
    parts = doc['meshes'][node['mesh']]['primitives']
    views = doc['bufferViews']
    view_ids = [p['extensions'][DRACO]['bufferView'] for p in parts]
    before_size = sum(views[i]['byteLength'] for i in set(view_ids))
    if before_size <= LIMIT:
        return raw, before_size
    (part,) = [p for p in parts if doc['materials'][p['material']]['name'] == material]
    ext = part['extensions'][DRACO]
    if (
        part.get('mode', 4) != 4
        or part.get('targets')
        or set(part['extensions']) != {DRACO}
        or set(part['attributes']) != {'POSITION', 'NORMAL', 'TEXCOORD_0'}
        or set(ext['attributes']) != set(part['attributes'])
        or view_ids.count(ext['bufferView']) != 1
    ):
        raise ValueError('Expected a distinct static textured road primitive')
    view = views[ext['bufferView']]
    start = view.get('byteOffset', 0)
    attrs, faces = decode(binary[start : start + view['byteLength']], ext['attributes'])
    for key, idx in part['attributes'].items():
        a = doc['accessors'][idx]
        if (
            a['componentType'] != 5126
            or a['count'] != len(attrs[key])
            or 'sparse' in a
            or 'bufferView' in a
            or a.get('normalized')
        ):
            raise ValueError(f'Unsupported road attribute: {key}')

    rows = np.ascontiguousarray(np.column_stack([attrs[k] for k in sorted(attrs)]))
    _, first, inverse = np.unique(
        rows.view(np.uint32), axis=0, return_index=True, return_inverse=True
    )
    mapped = inverse.reshape(-1)[faces]
    collapsed = (mapped == np.roll(mapped, 1, axis=1)).any(axis=1)
    extra = faces[collapsed].ravel()
    mapped[collapsed] = np.arange(len(first), len(first) + len(extra)).reshape(-1, 3)
    selected = np.concatenate((first, extra))
    # Draco derives the grid from all positions and discards unreferenced points.
    # Restore the exact source grid even if this material spans only part of it.
    domain = road_domain(path, root)
    origin = np.asarray(domain['origin'], dtype=np.float32)
    anchors = np.stack(
        [origin, origin + np.array([0, 0, domain['range']], dtype=np.float32)]
    )
    merged = {}
    for key, values in attrs.items():
        padding = anchors if key == 'POSITION' else np.repeat(values[:1], 2, axis=0)
        merged[key] = np.ascontiguousarray(np.concatenate((values[selected], padding)))
    payload, ids, count, index_count = encode(merged, mapped, pos=18, norm=6, uv=12)
    check, out_faces = decode(payload, ids)
    if (
        index_count != faces.size
        or out_faces.shape != faces.shape
        or count != len(check['POSITION'])
        or triangle_digest(attrs, faces) != triangle_digest(check, out_faces)
    ):
        raise ValueError('Decoded road material changed oriented triangle corners')
    size = before_size - view['byteLength'] + len(payload)
    if size >= before_size:
        return raw, before_size

    # Shared descriptors can also belong to another node. Give this part fresh
    # descriptors before using the existing splicer to discard superseded data.
    aligned = binary + bytes(-len(binary) % 4)
    ext.update(bufferView=len(views), attributes=ids)
    views.append(dict(buffer=0, byteOffset=len(aligned), byteLength=len(payload)))
    accessors = doc['accessors']
    for key, idx in list(part['attributes'].items()):
        entry = dict(accessors[idx], count=count)
        part['attributes'][key] = len(accessors)
        accessors.append(entry)
    index = copy.copy(accessors[part['indices']])
    if index['count'] != index_count:
        raise ValueError('Road path index accessor does not match its triangles')
    if (
        int(out_faces.max())
        >= {5121: 256, 5123: 65536, 5125: 2**32}[index['componentType']]
    ):
        index['componentType'] = 5125
    if 'min' in index:
        index['min'] = [int(out_faces.min())]
    if 'max' in index:
        index['max'] = [int(out_faces.max())]
    part['indices'] = len(accessors)
    accessors.append(index)
    result = splice_nodes(raw, pack_glb(doc, aligned + payload), {'roads'})
    validate_retained(raw, result, {'roads'})
    print(
        f'Road {material}: {view["byteLength"]} -> {len(payload)} bytes; roads: {before_size} -> {size}'
    )
    return result, size


def fit_road_budget(path, root=None):
    """Pack only as many road materials as needed. Publish after verifying the complete result."""
    path = Path(path)
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    raw = path.read_bytes()
    candidate = raw
    for material in ('path', 'asphalt', 'road'):
        candidate, size = _repack_material(candidate, path, root, material)
        if size <= LIMIT:
            break
    else:
        raise ValueError(f'Road geometry still exceeds budget: {size}')
    if candidate is raw:
        return
    validate_retained(raw, candidate, {'roads'})
    with tempfile.TemporaryDirectory(dir=path.parent) as scratch:
        checked = Path(scratch) / 'candidate.glb'
        checked.write_bytes(candidate)
        if road_domain(checked, root) != road_domain(path, root):
            raise ValueError('Road material position domains changed')
        os.replace(checked, path)
