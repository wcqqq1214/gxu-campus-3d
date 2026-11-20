"""Retain a published procedural node during an unrelated bounded base rebuild.

Only compressed geometry and accessor metadata are copied. Materials, layers and
scene structure stay in the new export; no decode/re-encode loses precision.
"""

import copy
import json
import re
import shutil
import struct
import subprocess


def mesh_nodes_by_name(doc):
    """Full exports coexist with source objects and acquire Blender suffixes.

    Base-only exports do not. Resolve that naming difference without silently
    accepting two meshes for the same logical object.
    """
    result = {}
    for node in doc['nodes']:
        if 'mesh' not in node:
            continue
        name = re.sub(r'\.\d{3,}$', '', node['name'])
        if name in result:
            raise ValueError(f'Ambiguous logical GLB node: {name}')
        result[name] = node
    return result


def unpack(raw):
    size = struct.unpack_from('<I', raw, 12)[0]
    return json.loads(raw[20 : 20 + size]), raw[28 + size :]


def pack_glb(doc, binary, *, pad_binary=True, ensure_ascii=True):
    body = bytes(binary) + (b'\0' * (-len(binary) % 4) if pad_binary else b'')
    if pad_binary and doc.get('buffers'):
        doc['buffers'][0]['byteLength'] = len(body)
    header = json.dumps(doc, separators=(',', ':'), ensure_ascii=ensure_ascii).encode()
    header += b' ' * (-len(header) % 4)
    return (
        struct.pack('<4sII', b'glTF', 2, 28 + len(header) + len(body))
        + struct.pack('<I4s', len(header), b'JSON')
        + header
        + struct.pack('<I4s', len(body), b'BIN\0')
        + body
    )


def replace_compressed_node_parts(path, name, parts):
    """Replace one node with disjoint Draco parts using existing named materials.

    Donors must each contain one mesh with the same transform. Only geometry
    is imported; destination scene structure, materials and textures remain.
    """
    if not parts:
        raise ValueError('Missing compressed mesh parts')
    doc, raw = unpack(path.read_bytes())
    binary = bytearray(raw)
    node = mesh_nodes_by_name(doc)[name]
    primitives = []
    if sum(n.get('mesh') == node['mesh'] for n in doc['nodes']) != 1:
        raise ValueError('Cannot replace a mesh shared by multiple nodes')

    def accessor_ids(mesh):
        ids = set()
        for p in mesh['primitives']:
            ids.update(p.get('attributes', {}).values())
            if 'indices' in p:
                ids.add(p['indices'])
            for target in p.get('targets', []):
                ids.update(target.values())
        return ids

    retained = set()
    for i, mesh in enumerate(doc['meshes']):
        if i != node['mesh']:
            retained.update(accessor_ids(mesh))
    for skin in doc.get('skins', []):
        if 'inverseBindMatrices' in skin:
            retained.add(skin['inverseBindMatrices'])
    for animation in doc.get('animations', []):
        for sampler in animation['samplers']:
            retained.update([sampler['input'], sampler['output']])
    free = sorted(accessor_ids(doc['meshes'][node['mesh']]) - retained, reverse=True)
    transform = lambda n: {
        k: v for k, v in n.items() if k not in ('name', 'mesh', 'extras')
    }
    for part in parts:
        source, payload = unpack(part)
        nodes = list(mesh_nodes_by_name(source).values())
        if len(nodes) != 1 or transform(nodes[0]) != transform(node):
            raise ValueError('Compressed mesh part has an incompatible transform')
        for original in source['meshes'][nodes[0]['mesh']]['primitives']:
            if set(original) - {
                'mode',
                'material',
                'attributes',
                'indices',
                'extensions',
            }:
                raise ValueError('Unsupported compressed primitive fields')
            p = copy.deepcopy(original)
            if set(p.get('extensions', {})) != {'KHR_draco_mesh_compression'}:
                raise ValueError('Expected a Draco mesh part')
            ext = p['extensions']['KHR_draco_mesh_compression']
            view = source['bufferViews'][ext['bufferView']]
            offset = view.get('byteOffset', 0)
            if view['buffer'] != 0:
                raise ValueError('External mesh part buffer')
            binary.extend(b'\0' * (-len(binary) % 4))
            ext['bufferView'] = len(doc['bufferViews'])
            doc['bufferViews'].append(
                {
                    'buffer': 0,
                    'byteOffset': len(binary),
                    'byteLength': view['byteLength'],
                }
            )
            binary.extend(payload[offset : offset + view['byteLength']])
            for field in ['indices', *p['attributes']]:
                container = p if field == 'indices' else p['attributes']
                accessor = copy.deepcopy(source['accessors'][container[field]])
                if 'bufferView' in accessor or 'sparse' in accessor:
                    raise ValueError('Expected compressed-only accessors')
                if free:
                    index = free.pop()
                    doc['accessors'][index] = accessor
                else:
                    index = len(doc['accessors'])
                    doc['accessors'].append(accessor)
                container[field] = index
            material = source['materials'][p['material']]['name']
            matches = [
                i for i, m in enumerate(doc['materials']) if m['name'] == material
            ]
            if len(matches) != 1:
                raise ValueError('Missing or ambiguous mesh part material')
            p['material'] = matches[0]
            primitives.append(p)
    doc['meshes'][node['mesh']]['primitives'] = primitives
    path.write_bytes(pack_glb(doc, binary))


def compact_buffer_views(path, *, optimize_jpegs=False):
    """Pack live views, sharing exact duplicates without decoding geometry.

    Optional jpegtran Huffman optimization preserves DCT coefficients and all
    metadata markers. Only views exclusively referenced by JPEG images qualify.
    All processing finishes before the original file is overwritten.
    """
    doc, binary = unpack(path.read_bytes())
    if len(doc['buffers']) != 1 or doc['buffers'][0].get('uri'):
        raise ValueError('Expected one internal GLB buffer')
    references = []

    def collect(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == 'bufferView' and type(child) is int:
                    references.append((value, key, child))
                else:
                    collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(doc)
    used = sorted({index for _, _, index in references})
    if any(index < 0 or index >= len(doc['bufferViews']) for index in used):
        raise ValueError('Invalid buffer view reference')
    jpeg_images = {
        id(item)
        for item in doc.get('images', [])
        if item.get('mimeType') == 'image/jpeg'
    }
    jpeg_views = (
        {
            index
            for index in used
            if all(
                id(parent) in jpeg_images
                for parent, _, ref in references
                if ref == index
            )
        }
        if optimize_jpegs
        else set()
    )
    encoder = shutil.which('jpegtran') if jpeg_views else None
    if jpeg_views and not encoder:
        raise RuntimeError(
            'JPEG optimization requires jpegtran (libjpeg-turbo) on PATH'
        )
    packed = bytearray()
    views = []
    remap = {}
    shared = {}
    for index in used:
        view = copy.deepcopy(doc['bufferViews'][index])
        if view['buffer'] != 0:
            raise ValueError('Unexpected external buffer view')
        start = view.get('byteOffset', 0)
        end = start + view['byteLength']
        if start < 0 or end < start or end > len(binary):
            raise ValueError('Buffer view exceeds binary payload')
        payload = binary[start:end]
        if index in jpeg_views:
            candidate = subprocess.run(
                [encoder, '-copy', 'all', '-optimize', '-strict'],
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            ).stdout
            if len(candidate) < len(payload):
                payload = candidate
        view['byteLength'] = len(payload)
        metadata = {key: value for key, value in view.items() if key != 'byteOffset'}
        signature = (
            json.dumps(metadata, sort_keys=True, separators=(',', ':')),
            payload,
        )
        if signature in shared:
            remap[index] = shared[signature]
            continue
        packed.extend(b'\0' * (-len(packed) % 4))
        view['byteOffset'] = len(packed)
        packed.extend(payload)
        remap[index] = len(views)
        shared[signature] = len(views)
        views.append(view)
    for parent, key, index in references:
        parent[key] = remap[index]
    doc['bufferViews'] = views
    path.write_bytes(pack_glb(doc, packed))


def preserve_geometry(previous, path, names, materials=None):
    old, oldbin = unpack(previous)
    new, newbin = unpack(path.read_bytes())
    binary = bytearray(newbin)
    old_nodes = mesh_nodes_by_name(old)
    new_nodes = mesh_nodes_by_name(new)
    for name in names:
        a = old_nodes[name]
        b = new_nodes[name]
        before = old['meshes'][a['mesh']]['primitives']
        after = new['meshes'][b['mesh']]['primitives']
        if materials is None:
            assert len(before) == len(after)
            pairs = list(zip(before, after))
        else:
            # A bounded update may export only changed material primitives.
            # Match by material name so omitted primitives remain byte-exact.
            pairs = []
            present = {old['materials'][p['material']]['name'] for p in before}
            for material in materials & present:
                (p,) = [
                    p
                    for p in before
                    if old['materials'][p['material']]['name'] == material
                ]
                (q,) = [
                    q
                    for q in after
                    if new['materials'][q['material']]['name'] == material
                ]
                pairs.append((p, q))
        for p, q in pairs:
            assert (
                old['materials'][p['material']]['name']
                == new['materials'][q['material']]['name']
            )
            ext = copy.deepcopy(p['extensions']['KHR_draco_mesh_compression'])
            view = old['bufferViews'][ext['bufferView']]
            offset = view.get('byteOffset', 0)
            blob = oldbin[offset : offset + view['byteLength']]
            current = new['bufferViews'][
                q['extensions']['KHR_draco_mesh_compression']['bufferView']
            ]
            start = current.get('byteOffset', 0)
            if blob == binary[start : start + current['byteLength']]:
                continue
            binary.extend(b'\0' * ((-len(binary)) % 4))
            ext['bufferView'] = len(new['bufferViews'])
            new['bufferViews'].append(
                {'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(blob)}
            )
            binary.extend(blob)
            q['extensions']['KHR_draco_mesh_compression'] = ext
            restored_attributes = {}
            for attr, index in p['attributes'].items():
                metadata = copy.deepcopy(old['accessors'][index])
                assert 'bufferView' not in metadata
                target = q['attributes'].get(attr)
                if target is None:
                    target = len(new['accessors'])
                    new['accessors'].append(metadata)
                else:
                    new['accessors'][target] = metadata
                restored_attributes[attr] = target
            q['attributes'] = restored_attributes
            if 'indices' in p:
                metadata = copy.deepcopy(old['accessors'][p['indices']])
                assert 'bufferView' not in metadata
                new['accessors'][q['indices']] = metadata
    path.write_bytes(pack_glb(new, binary))


def replace_node_geometry(raw, path, name):
    """Allow this node's material set to grow, keeping other payloads verbatim."""
    src, payload = unpack(raw)
    dst, old_payload = unpack(path.read_bytes())
    binary = bytearray(old_payload)
    source = mesh_nodes_by_name(src)[name]
    target = mesh_nodes_by_name(dst)[name]
    byname = {m['name']: i for i, m in enumerate(dst['materials'])}
    primitives = []
    for primitive in src['meshes'][source['mesh']]['primitives']:
        p = copy.deepcopy(primitive)
        mat = src['materials'][p['material']]
        matname = mat['name']
        if matname not in byname:
            assert 'Texture' not in json.dumps(mat), (
                'New textured material needs explicit texture remapping'
            )
            byname[matname] = len(dst['materials'])
            dst['materials'].append(copy.deepcopy(mat))
        p['material'] = byname[matname]
        ext = p['extensions']['KHR_draco_mesh_compression']
        view = src['bufferViews'][ext['bufferView']]
        binary.extend(b'\0' * (-len(binary) % 4))
        offset = len(binary)
        start = view.get('byteOffset', 0)
        binary.extend(payload[start : start + view['byteLength']])
        ext['bufferView'] = len(dst['bufferViews'])
        dst['bufferViews'].append(
            {'buffer': 0, 'byteOffset': offset, 'byteLength': view['byteLength']}
        )
        for field, index in list(p['attributes'].items()) + [('indices', p['indices'])]:
            a = copy.deepcopy(src['accessors'][index])
            assert 'bufferView' not in a
            if field == 'indices':
                p[field] = len(dst['accessors'])
            else:
                p['attributes'][field] = len(dst['accessors'])
            dst['accessors'].append(a)
        primitives.append(p)
    dst['meshes'][target['mesh']]['primitives'] = primitives
    path.write_bytes(pack_glb(dst, binary))


def compact_static_accessors(path):
    """Drop orphaned metadata from repeated bounded static-mesh replacements."""
    doc, binary = unpack(path.read_bytes())
    assert not doc.get('animations') and not doc.get('skins')
    refs = []
    for mesh in doc['meshes']:
        for p in mesh['primitives']:
            refs.extend((p['attributes'], key) for key in p['attributes'])
            if 'indices' in p:
                refs.append((p, 'indices'))
            for target in p.get('targets', []):
                refs.extend((target, key) for key in target)
    live = sorted({obj[key] for obj, key in refs})
    remap = {old: new for new, old in enumerate(live)}
    for obj, key in refs:
        obj[key] = remap[obj[key]]
    doc['accessors'] = [doc['accessors'][i] for i in live]
    path.write_bytes(pack_glb(doc, binary))
