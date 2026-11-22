"""Share exactly matching decoded terrain corners when the aggregate exceeds its budget."""

import os
import subprocess
import tempfile
from hashlib import sha256
from pathlib import Path

import numpy as np

from campus_draco import decode, encode
from incremental_glb import validate_retained
from initial_model_budget import load_model_budget
from preserve_glb_geometry import mesh_nodes_by_name, pack_glb, unpack

BUDGET = load_model_budget()['baseLayerLimitBytes']['terrain']
DRACO = 'KHR_draco_mesh_compression'


def corner_rows(attributes):
    # Compare the bits of all eight float32 components, including signed zero.
    return np.column_stack(
        [attributes[key] for key in ('POSITION', 'NORMAL', 'TEXCOORD_0')]
    ).view(np.uint32)


def triangle_digest(attributes, faces):
    # Keep winding, multiplicity, UV seams and hard normals, independent of Draco's
    # vertex numbering, triangle order and cyclic choice of first corner.
    rows, inverse = np.unique(corner_rows(attributes), axis=0, return_inverse=True)
    triples = inverse.ravel()[faces]
    a, b, c = triples.T
    first = np.where((a <= b) & (a <= c), 0, np.where(b <= c, 1, 2))
    # Where the minimum occurs twice, choose the rotation starting with both minima.
    first[(c == a) & (a < b)] = 2
    rotated = np.take_along_axis(triples, (first[:, None] + np.arange(3)) % 3, axis=1)
    ordered = rotated[np.lexsort(rotated.T[::-1])]
    digest = sha256(rows.astype('<u4').tobytes())
    digest.update(ordered.astype('<u4').tobytes())
    return digest.hexdigest()


def compact_global(payload, ids):
    attrs, faces = decode(payload, ids)
    _, first, inverse = np.unique(
        corner_rows(attrs), axis=0, return_index=True, return_inverse=True
    )
    mapped = inverse.ravel()[faces]
    # Draco drops repeated-index faces. Give these existing collapsed triangles
    # distinct indices so their decoded corners and multiplicity survive.
    collapsed = np.any(mapped == np.roll(mapped, 1, axis=1), axis=1)
    extra = faces[collapsed].ravel()
    mapped[collapsed] = np.arange(len(first), len(first) + len(extra)).reshape(-1, 3)
    indices = np.concatenate((first, extra))
    merged = {
        key: np.ascontiguousarray(values[indices]) for key, values in attrs.items()
    }
    encoded, attr_ids, count, index_count = encode(
        merged, mapped, pos=18, norm=6, uv=18
    )
    result, output_faces = decode(encoded, attr_ids)
    before = triangle_digest(attrs, faces)
    after = triangle_digest(result, output_faces)
    if (
        before != after
        or faces.shape != output_faces.shape
        or count != len(result['POSITION'])
        or index_count != output_faces.size
    ):
        raise ValueError('Re-encoded terrain changed decoded oriented triangle corners')
    return (
        encoded,
        attr_ids,
        {
            'oldVertices': len(attrs['POSITION']),
            'newVertices': len(result['POSITION']),
            'triangles': len(faces),
            'protectedCollapsedTriangles': int(collapsed.sum()),
            'beforeTriangleSha256': before,
            'afterTriangleSha256': after,
        },
    )


def _draco_prefix():
    # A standard Draco installation or the intact header/archive pair from a
    # pinned wheel. uv caches this environment across independent build trees.
    if prefix := os.environ.get('GXU_DRACO_PREFIX'):
        return Path(prefix)
    query = (
        'from importlib.metadata import distribution; '
        'print(next(f.locate().resolve().parents[1] for f in '
        "distribution('DracoPy').files if f.name == 'libdraco.a').resolve())"
    )
    return Path(
        subprocess.check_output(
            [
                'uv',
                'run',
                '--no-project',
                '--python',
                '3.12',
                '--with',
                'DracoPy==1.7.0',
                'python',
                '-c',
                query,
            ],
            text=True,
        ).strip()
    )


def _compact_connectivity(payload, ids):
    """Share independent vertex attributes, protecting collapsed triangles."""
    with tempfile.TemporaryDirectory(prefix='gxu-terrain-codec-') as tmp:
        folder = Path(tmp)
        exe = folder / 'terrain-connectivity'
        prefix = _draco_prefix()
        subprocess.run(
            [
                os.environ.get('CXX', 'c++'),
                '-std=c++17',
                '-O2',
                '-I' + str(prefix / 'include'),
                str(Path(__file__).with_name('terrain_connectivity.cpp')),
                str(prefix / 'lib' / 'libdraco.a'),
                '-o',
                str(exe),
            ],
            check=True,
        )
        src, dst = folder / 'input.drc', folder / 'output.drc'
        src.write_bytes(payload)
        subprocess.run([str(exe), str(src), str(dst)], check=True)
        encoded = dst.read_bytes()
    before, faces = decode(payload, ids)
    after, new_faces = decode(encoded, ids)
    old_hash = triangle_digest(before, faces)
    new_hash = triangle_digest(after, new_faces)
    if old_hash != new_hash or faces.shape != new_faces.shape:
        raise ValueError('Independent Draco attribute sharing changed terrain corners')
    return (
        encoded,
        ids,
        {
            'oldVertices': len(before['POSITION']),
            'newVertices': len(after['POSITION']),
            'triangles': len(faces),
            'beforeTriangleSha256': old_hash,
            'afterTriangleSha256': new_hash,
            'method': 'Draco independent attribute maps on original quantization grids',
        },
    )


def fit_terrain_budget(raw):
    """Return a verified base or the identical bytes when already within budget."""
    doc, binary = unpack(raw)
    node = mesh_nodes_by_name(doc)['terrain']
    if node.get('extras', {}).get('layer') != 'terrain':
        raise ValueError('Expected the logical terrain mesh in the terrain layer')
    parts = doc['meshes'][node['mesh']]['primitives']
    views = doc['bufferViews']
    sizes = [views[p['extensions'][DRACO]['bufferView']]['byteLength'] for p in parts]
    report = {
        'node': node['name'],
        'beforeBytes': sizes,
        'afterBytes': sizes,
        'byteLimit': BUDGET,
    }
    if sum(sizes) <= BUDGET:
        return raw, report

    # terrain_precision emits global first (18 bits), then optional local (26).
    p = parts[0]
    if (
        p.get('mode', 4) != 4
        or set(p.get('extensions', {})) != {DRACO}
        or set(p['attributes']) != {'POSITION', 'NORMAL', 'TEXCOORD_0'}
    ):
        raise ValueError('Unsupported terrain primitive layout')
    attrs = [doc['accessors'][i] for i in p['attributes'].values()]
    if any(
        a['componentType'] != 5126
        or a.get('normalized')
        or 'bufferView' in a
        or 'sparse' in a
        for a in attrs
    ):
        raise ValueError('Expected dense float Draco terrain attributes')
    ext = p['extensions'][DRACO]
    if set(ext['attributes']) != set(p['attributes']) or any(
        doc['accessors'][i]['type'] != ('VEC2' if key == 'TEXCOORD_0' else 'VEC3')
        for key, i in p['attributes'].items()
    ):
        raise ValueError('Terrain attribute declarations do not match the stream')
    for local in parts[1:]:
        if ext['bufferView'] == local['extensions'][DRACO]['bufferView'] or (
            set(p['attributes'].values()) & set(local['attributes'].values())
        ):
            raise ValueError('Global and local terrain resources must be distinct')
    view = views[ext['bufferView']]
    start = view.get('byteOffset', 0)
    end = start + sizes[0]
    payload, ids, checks = compact_global(binary[start:end], ext['attributes'])
    if len(payload) + sum(sizes[1:]) > BUDGET:
        payload, ids, checks = _compact_connectivity(
            binary[start:end], ext['attributes']
        )
    index = doc['accessors'][p['indices']]
    if index['count'] != 3 * checks['triangles'] or any(
        a['count'] != checks['oldVertices'] for a in attrs
    ):
        raise ValueError('Terrain accessor counts do not match its decoded mesh')
    max_index = checks['newVertices'] - 1
    if max_index >= {5121: 256, 5123: 65536, 5125: 2**32}[index['componentType']]:
        index['componentType'] = 5125
    if 'max' in index:
        index['max'] = [max_index]
    if 'min' in index:
        index['min'] = [0]
    new_sizes = [len(payload), *sizes[1:]]
    if sum(new_sizes) > BUDGET:
        raise ValueError(f'Compressed terrain still exceeds {BUDGET} bytes')
    # Replace this aligned range only. Existing material, texture and accessor
    # references survive. Detect aliases or overlaps before accepting the result.
    aligned_end = (end + 3) & ~3
    new_chunk = payload + bytes(-len(payload) % 4)
    shift = len(new_chunk) - (aligned_end - start)
    for other in views:
        if other is view:
            continue
        offset = other.get('byteOffset', 0)
        if offset >= aligned_end:
            other['byteOffset'] = offset + shift
        elif offset + other['byteLength'] > start:
            raise ValueError('Overlapping terrain buffer view')
    view['byteLength'] = len(payload)
    ext['attributes'] = ids
    for a in attrs:
        a['count'] = checks['newVertices']
    candidate = pack_glb(
        doc, binary[:start] + new_chunk + binary[aligned_end:], ensure_ascii=False
    )
    untouched = validate_retained(raw, candidate, {'terrain'})
    return candidate, {
        **report,
        **checks,
        'afterBytes': new_sizes,
        'unchangedOtherNodes': untouched,
    }
