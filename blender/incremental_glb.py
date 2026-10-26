"""Splice selected static campus nodes without re-encoding retained resources."""
import copy
import hashlib
import json
import struct
from preserve_glb_geometry import unpack, mesh_nodes_by_name


def _check(doc):
    if (doc.get('animations') or doc.get('skins') or len(doc['scenes']) != 1
            or set(doc['scenes'][0]['nodes']) != set(range(len(doc['nodes'])))
            or any('children' in n or 'mesh' not in n for n in doc['nodes'])
            or set(doc.get('extensionsUsed', [])) - {'KHR_draco_mesh_compression'}):
        raise ValueError('Incremental campus export requires flat static Draco nodes')
    mesh_nodes_by_name(doc)  # Reject ambiguous logical names.


def pack(doc, binary):
    binary = bytes(binary) + b'\0' * (-len(binary) % 4)
    doc['buffers'] = [{'byteLength': len(binary)}]
    header = json.dumps(doc, separators=(',', ':'), ensure_ascii=False).encode()
    header += b' ' * (-len(header) % 4)
    return (struct.pack('<4sII', b'glTF', 2, 28 + len(header) + len(binary))
            + struct.pack('<I4s', len(header), b'JSON') + header
            + struct.pack('<I4s', len(binary), b'BIN\0') + binary)


def splice_nodes(previous, candidate, selected):
    """Use candidate versions of selected names; retain all other old nodes.

    Rebuild only reference tables. Compressed geometry, accessor metadata,
    transforms, extras and texture bytes are copied from the chosen source.
    Selected nodes may be added/removed; unselected candidate nodes are ignored.
    """
    sources = [unpack(previous), unpack(candidate)]
    for doc, _ in sources:
        _check(doc)
    old, new = [mesh_nodes_by_name(doc) for doc, _ in sources]
    selected = set(selected)
    output = copy.deepcopy(sources[0][0])
    tables = ('nodes', 'meshes', 'accessors', 'bufferViews', 'materials', 'textures', 'images', 'samplers')
    for table in tables:
        output[table] = []
    binary = bytearray()
    memo = {}
    unique = {table: {} for table in tables}

    def transfer(source, table, index):
        key = (source, table, index)
        if key in memo:
            return memo[key]
        doc, payload = sources[source]
        value = copy.deepcopy(doc[table][index])
        if table == 'bufferViews':
            start = value.get('byteOffset', 0)
            if value['buffer'] != 0 or start < 0 or start + value['byteLength'] > len(payload):
                raise ValueError('Invalid internal buffer view')
            data = payload[start:start + value['byteLength']]
            value.pop('byteOffset', None)
            signature = (json.dumps(value, sort_keys=True), data)
            if signature not in unique[table]:
                binary.extend(b'\0' * (-len(binary) % 4))
                value['byteOffset'] = len(binary)
                binary.extend(data)
                unique[table][signature] = len(output[table])
                output[table].append(value)
            memo[key] = unique[table][signature]
            return memo[key]
        if table == 'meshes':
            for p in value['primitives']:
                if set(p) - {'mode', 'material', 'attributes', 'indices', 'extensions'}:
                    raise ValueError('Unsupported incremental primitive')
                if set(p.get('extensions', {})) != {'KHR_draco_mesh_compression'}:
                    raise ValueError('Expected Draco primitive')
                ext = p['extensions']['KHR_draco_mesh_compression']
                ext['bufferView'] = transfer(source, 'bufferViews', ext['bufferView'])
                p['attributes'] = {k: transfer(source, 'accessors', v) for k, v in p['attributes'].items()}
                if 'indices' in p:
                    p['indices'] = transfer(source, 'accessors', p['indices'])
                if 'material' in p:
                    p['material'] = transfer(source, 'materials', p['material'])
        elif table == 'accessors':
            if 'bufferView' in value or 'sparse' in value:
                raise ValueError('Expected compressed-only accessor')
        elif table == 'materials':
            if value.get('extensions'):
                raise ValueError('Unsupported incremental material extensions')
            for container in (value, value.get('pbrMetallicRoughness', {})):
                for field, info in container.items():
                    if field.endswith('Texture'):
                        info['index'] = transfer(source, 'textures', info['index'])
        elif table == 'textures':
            if value.get('extensions'):
                raise ValueError('Unsupported incremental texture extensions')
            value['source'] = transfer(source, 'images', value['source'])
            if 'sampler' in value:
                value['sampler'] = transfer(source, 'samplers', value['sampler'])
        elif table == 'images':
            if 'uri' in value:
                raise ValueError('Expected embedded image')
            value['bufferView'] = transfer(source, 'bufferViews', value['bufferView'])
        signature = json.dumps(value, sort_keys=True)
        if signature not in unique[table]:
            unique[table][signature] = len(output[table])
            output[table].append(value)
        memo[key] = unique[table][signature]
        return memo[key]

    order = list(old) + [name for name in new if name not in old and name in selected]
    for name in order:
        source = int(name in selected)
        nodes = new if source else old
        if name not in nodes:
            continue
        node = copy.deepcopy(nodes[name])
        node['mesh'] = transfer(source, 'meshes', node['mesh'])
        output['nodes'].append(node)
    output['scenes'][0]['nodes'] = list(range(len(output['nodes'])))
    return pack(output, binary)


def node_signatures(raw):
    """Semantic resource closure including exact encoded payloads, independent of indices."""
    doc, binary = unpack(raw)
    _check(doc)
    def resolve(value):
        if isinstance(value, list):
            return [resolve(v) for v in value]
        if not isinstance(value, dict):
            return value
        result = {}
        for k, v in value.items():
            if k == 'bufferView':
                view = doc['bufferViews'][v]; start = view.get('byteOffset', 0)
                result[k] = [
                    {key: val for key, val in view.items() if key not in ('buffer', 'byteOffset')},
                    hashlib.sha256(binary[start:start + view['byteLength']]).hexdigest()]
            elif k in ('mesh', 'material', 'sampler', 'source', 'indices'):
                table = {'mesh':'meshes', 'material':'materials', 'sampler':'samplers', 'source':'images', 'indices':'accessors'}[k]
                result[k] = resolve(doc[table][v])
            elif k == 'attributes' and 'bufferView' not in value:
                result[k] = {name: resolve(doc['accessors'][index]) for name, index in v.items()}
            elif k.endswith('Texture'):
                result[k] = {**v, 'index': resolve(doc['textures'][v['index']])}
            else:
                result[k] = resolve(v)
        return result
    return {name: resolve(node) for name, node in mesh_nodes_by_name(doc).items()}


def validate_retained(previous, candidate, selected):
    old, new = node_signatures(previous), node_signatures(candidate)
    unexpected = [name for name in old if name not in selected and old[name] != new.get(name)]
    unexpected += [name for name in new if name not in old and name not in selected]
    if unexpected:
        raise ValueError(f'Unrelated base nodes changed: {unexpected}')
    return len(set(old) - set(selected))
