"""Static triangle primitives through Blender's bundled Draco bridge."""

import ctypes as c

import numpy as np
from io_scene_gltf2.io.com.library import dll_path

dll = c.CDLL(str(dll_path('bf_intern_draco_bridge', 'Draco')))
P, U, S, B, T = c.c_void_p, c.c_uint32, c.c_size_t, c.c_bool, c.c_char_p


def fn(name, ret, *args):
    f = getattr(dll, name)
    f.restype = ret
    f.argtypes = list(args)
    return f


newdec = fn('decoderCreate', P)
freedec = fn('decoderRelease', None, P)
decodebuf = fn('decoderDecode', B, P, P, S)
readattr = fn('decoderReadAttribute', B, P, U, S, T)
attrbytes = fn('decoderGetAttributeByteLength', S, P, U)
copyattr = fn('decoderCopyAttribute', None, P, U, P)
readidx = fn('decoderReadIndices', B, P, S)
idxbytes = fn('decoderGetIndicesByteLength', S, P)
copyidx = fn('decoderCopyIndices', None, P, P)
nv = fn('decoderGetVertexCount', U, P)
ni = fn('decoderGetIndexCount', U, P)
newenc = fn('encoderCreate', P, U)
freeenc = fn('encoderRelease', None, P)
setattr_ = fn('encoderSetAttribute', U, P, T, S, T, P, B)
setidx = fn('encoderSetIndices', None, P, S, U, P)
level = fn('encoderSetCompressionLevel', None, P, U)
bits = fn('encoderSetQuantizationBits', None, P, U, U, U, U, U)
encodebuf = fn('encoderEncode', B, P, c.c_uint8)
bufsize = fn('encoderGetByteLength', c.c_uint64, P)
encpoints = fn('encoderGetEncodedVertexCount', U, P)
encindices = fn('encoderGetEncodedIndexCount', U, P)
copybuf = fn('encoderCopy', None, P, P)


def decode(data, attribute_ids):
    """Return contiguous float32 position/normal/UV arrays and uint32 triangles."""
    data = bytes(data)
    decoder = newdec()
    try:
        if not decodebuf(decoder, data, len(data)):
            raise ValueError('Invalid Draco payload')
        arr = {}
        for key, id_ in attribute_ids.items():
            dims = {'POSITION': 3, 'NORMAL': 3, 'TEXCOORD_0': 2}[key]
            a = np.empty((nv(decoder), dims), dtype=np.float32)
            if not readattr(decoder, id_, 5126, f'VEC{dims}'.encode()):
                raise ValueError(key)
            if attrbytes(decoder, id_) != a.nbytes:
                raise ValueError(f'Unexpected byte length for {key}')
            copyattr(decoder, id_, a.ctypes.data)
            arr[key] = a
        faces = np.empty(ni(decoder), dtype=np.uint32)
        if not readidx(decoder, 5125):
            raise ValueError('Invalid Draco indices')
        if idxbytes(decoder) != faces.nbytes or len(faces) % 3:
            raise ValueError('Invalid triangle payload')
        copyidx(decoder, faces.ctypes.data)
        return arr, faces.reshape(-1, 3)
    finally:
        freedec(decoder)


def encode(attributes, faces, pos=18, norm=10, uv=16):
    """Return payload, semantic IDs, encoded vertex count and encoded index count."""
    arr = {k: np.ascontiguousarray(a, dtype=np.float32) for k, a in attributes.items()}
    dims = {'POSITION': 3, 'NORMAL': 3, 'TEXCOORD_0': 2}
    count = len(arr['POSITION'])
    if not count or any(
        k not in dims or a.shape != (count, dims[k]) or not np.isfinite(a).all()
        for k, a in arr.items()
    ):
        raise ValueError('Incompatible static vertex attribute arrays')
    faces = np.asarray(faces)
    if (
        faces.size == 0
        or faces.ndim != 2
        or faces.shape[1] != 3
        or faces.dtype.kind not in 'iu'
        or faces.min() < 0
        or faces.max() >= count
    ):
        raise ValueError('Expected M×3 triangle indices into the vertex arrays')
    if not all(1 <= v <= 30 for v in (pos, norm, uv)):
        raise ValueError('Invalid Draco quantization bits')
    faces = np.ascontiguousarray(faces, np.uint32)
    enc = newenc(len(arr['POSITION']))
    try:
        ids = {
            k: setattr_(
                enc, k.encode(), 5126, f'VEC{a.shape[1]}'.encode(), a.ctypes.data, False
            )
            for k, a in arr.items()
        }
        setidx(enc, 5125, faces.size, faces.ctypes.data)
        level(enc, 10)
        bits(enc, pos, norm, uv, 10, 10)
        if not encodebuf(enc, 0):
            raise ValueError('Draco encode failed')
        out = c.create_string_buffer(bufsize(enc))
        copybuf(enc, out)
        return out.raw, ids, encpoints(enc), encindices(enc)
    finally:
        freeenc(enc)
