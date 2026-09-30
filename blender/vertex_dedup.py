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
