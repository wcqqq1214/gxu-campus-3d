"""Paired basketball LOD assets; incremental exports retain published ground bytes."""

import copy
import hashlib
import json

from preserve_glb_geometry import (
    compact_buffer_views,
    mesh_nodes_by_name,
    pack_glb,
    unpack,
)


def write_glb(path, doc, binary):
    path.write_bytes(pack_glb(doc, binary))


def extract_bank(raw, name, path):
    """Copy an untextured, static bank without decoding any of its primitives."""
    doc, binary = unpack(raw)
    node = copy.deepcopy(mesh_nodes_by_name(doc)[name])
    if set(node) - {'name', 'mesh', 'extras'}:
        raise ValueError('Expected an untransformed static basketball bank')
    mesh = copy.deepcopy(doc['meshes'][node['mesh']])
    materials, accessors = [], []
    for primitive in mesh['primitives']:
        if set(primitive) - {'mode', 'material', 'attributes', 'indices', 'extensions'}:
            raise ValueError('Unsupported basketball primitive')
        if set(primitive.get('extensions', {})) != {'KHR_draco_mesh_compression'}:
            raise ValueError('Expected compressed basketball geometry')
        material = doc['materials'][primitive['material']]
        # The current bank uses plain colours. Fail instead of dropping future maps.
        if 'Texture' in json.dumps(material) or material.get('extensions'):
            raise ValueError(
                'Textured or extended basketball materials need explicit handling'
            )
        primitive['material'] = len(materials)
        materials.append(material)
        for container, key in [
            (primitive, 'indices'),
            *[(primitive['attributes'], k) for k in primitive['attributes']],
        ]:
            accessor = doc['accessors'][container[key]]
            if 'bufferView' in accessor or 'sparse' in accessor:
                raise ValueError('Expected compressed-only bank accessors')
            container[key] = len(accessors)
            accessors.append(accessor)
    node['mesh'] = 0
    result = dict(
        asset=doc['asset'],
        scene=0,
        scenes=[{'nodes': [0]}],
        nodes=[node],
        meshes=[mesh],
        materials=materials,
        accessors=accessors,
        buffers=doc['buffers'],
        bufferViews=doc['bufferViews'],
        extensionsUsed=['KHR_draco_mesh_compression'],
        extensionsRequired=['KHR_draco_mesh_compression'],
    )
    write_glb(path, result, binary)
    compact_buffer_views(path)


def manifest_entries(data, directory):
    return [
        dict(
            id=bank['id'],
            url='models/' + bank['id'] + '.glb',
            bytes=(directory / (bank['id'] + '.glb')).stat().st_size,
            sha256=hashlib.sha256(
                (directory / (bank['id'] + '.glb')).read_bytes()
            ).hexdigest(),
            bounds=bank['bounds'],
        )
        for bank in data['banks']
    ]
