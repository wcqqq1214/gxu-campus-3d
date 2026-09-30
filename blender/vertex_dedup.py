"""Share identical export vertices without changing face corners or precision."""
import copy


def deduplicate_primitive_vertices(primitive):
    # Morph targets also carry per-vertex values; leave them to the exporter.
    if primitive.mode not in (None, 4) or primitive.targets or primitive.indices is None:
        return
    import numpy as np
    from io_scene_gltf2.io.exp.binary_data import BinaryData

    attributes = primitive.attributes
    if not attributes or attributes['POSITION'].buffer_view is None:
        return
    count = attributes['POSITION'].count
    if not count:
        return
    streams = []
    for accessor in attributes.values():
        if accessor.count != count or accessor.byte_offset or accessor.sparse:
            raise ValueError('Vertex deduplication requires dense, aligned attributes')
        streams.append(np.frombuffer(accessor.buffer_view.data, dtype=np.uint8).reshape(count, -1))
    # Include every attribute, not just position: UV seams and hard normals
    # remain separate. Compare bytes, with no welding distance or rounding.
    rows = np.ascontiguousarray(np.concatenate(streams, axis=1))
    _, first, inverse = np.unique(
        rows.view(np.dtype((np.void, rows.shape[1]))).ravel(),
        return_index=True, return_inverse=True)
    if len(first) == count:
        return
    index = primitive.indices
    if index.byte_offset or index.sparse:
        raise ValueError('Vertex deduplication requires dense, aligned indices')
    dtype = {5121: np.dtype('u1'), 5123: np.dtype('<u2'), 5125: np.dtype('<u4')}[index.component_type]
    old_indices = np.frombuffer(index.buffer_view.data, dtype=dtype)
    if len(old_indices) != index.count or (len(old_indices) and old_indices.max() >= count):
        raise ValueError('Vertex deduplication received invalid indices')
    mapped = inverse[old_indices].astype(dtype)
    # Accessors and their BinaryData may be shared with another primitive.
    # Publish fresh descriptors only after the complete remap succeeds.
    replacements = {}
    for (name, accessor), stream in zip(attributes.items(), streams):
        replacement = copy.copy(accessor)
        replacement.buffer_view = BinaryData(stream[first].tobytes(), accessor.buffer_view.bufferViewTarget)
        replacement.count = len(first)
        replacements[name] = replacement
    replacement_index = copy.copy(index)
    replacement_index.buffer_view = BinaryData(mapped.tobytes(), index.buffer_view.bufferViewTarget)
    if index.min is not None:
        replacement_index.min = [int(mapped.min())] if len(mapped) else []
    if index.max is not None:
        replacement_index.max = [int(mapped.max())] if len(mapped) else []
    primitive.attributes = replacements
    primitive.indices = replacement_index


def share_position_quantization_bounds(primitives):
    """Give Draco material primitives one domain using unreferenced extrema.

    The exporter does not expose Draco's explicit quantization-domain API.
    Its encoder includes attribute values in the domain, then drops vertices
    unused by faces. Borrow up to six actual mesh vertices as domain anchors;
    do not add indices or faces. Actual exported bounds remain the original
    primitive bounds, since the anchors are not part of the decoded mesh.
    """
    import numpy as np
    from io_scene_gltf2.io.exp.binary_data import BinaryData

    if len(primitives) < 2:
        return
    arrays = []
    for primitive in primitives:
        if primitive.mode not in (None, 4) or primitive.targets or primitive.indices is None:
            raise ValueError('Shared road quantization requires static indexed triangles')
        position = primitive.attributes['POSITION']
        if (position.component_type != 5126 or position.type != 'VEC3'
                or position.byte_offset or position.sparse or not position.count):
            raise ValueError('Shared road quantization requires dense Float32 positions')
        array = np.frombuffer(position.buffer_view.data, dtype='<f4').reshape(-1, 3)
        if len(array) != position.count:
            raise ValueError('Position buffer does not match its accessor count')
        arrays.append(array)
    positions = np.concatenate(arrays)
    if not np.isfinite(positions).all():
        raise ValueError('Non-finite road positions')
    indices = sorted(set(positions.argmin(axis=0).tolist() + positions.argmax(axis=0).tolist()))
    anchors = positions[indices]
    replacements = []
    for primitive in primitives:
        count = primitive.attributes['POSITION'].count
        attributes = {}
        for name, accessor in primitive.attributes.items():
            if accessor.count != count or accessor.byte_offset or accessor.sparse:
                raise ValueError('Shared road quantization requires dense, aligned attributes')
            raw = np.frombuffer(accessor.buffer_view.data, dtype=np.uint8).reshape(count, -1)
            padding = (anchors.view(np.uint8).reshape(len(anchors), -1) if name == 'POSITION'
                       else np.repeat(raw[:1], len(anchors), axis=0))
            replacement = copy.copy(accessor)
            replacement.buffer_view = BinaryData(np.concatenate([raw, padding]).tobytes(),
                                                 accessor.buffer_view.bufferViewTarget)
            replacement.count = count + len(anchors)
            # Keep the unpadded bounds used by runtime culling. Draco updates
            # accessor counts to the decoded (face-referenced) vertex count.
            attributes[name] = replacement
        replacements.append(attributes)
    for primitive, attributes in zip(primitives, replacements):
        primitive.attributes = attributes
        primitive.indices = copy.copy(primitive.indices)
