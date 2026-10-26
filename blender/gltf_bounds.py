"""Serialize typed FLOAT bounds compactly without changing a single Float32 bit."""
import json
import math
import struct


def compact_float_bounds(doc):
    # glTF 2.0 sections 5.1.7/5.1.8: min/max use accessor.componentType.
    # https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#accessor-max
    # Never decimal-round geometry or integer accessors to meet a byte budget.
    for accessor in doc.get('accessors', []):
        if accessor.get('componentType') != 5126:
            continue
        for key in ('min', 'max'):
            for index, value in enumerate(accessor.get(key, [])):
                if not math.isfinite(value):
                    raise ValueError('Non-finite glTF accessor bound')
                bits = struct.pack('<f', value)
                best = value
                for digits in range(1, 10):
                    candidate = float(format(value, f'.{digits}g'))
                    try:
                        same = struct.pack('<f', candidate) == bits
                    except OverflowError:
                        continue
                    if same:
                        if len(json.dumps(candidate)) < len(json.dumps(best)):
                            best = candidate
                        break
                accessor[key][index] = best


def compact_glb_float_bounds(path):
    from preserve_glb_geometry import unpack
    original = path.read_bytes()
    doc, binary = unpack(original)
    compact_float_bounds(doc)
    header = json.dumps(doc, separators=(',', ':')).encode()
    header += b' ' * (-len(header) % 4)
    packed = (struct.pack('<4sII', b'glTF', 2, 28+len(header)+len(binary))
              + struct.pack('<I4s', len(header), b'JSON') + header
              + struct.pack('<I4s', len(binary), b'BIN\0') + binary)
    if len(packed) < len(original):
        path.write_bytes(packed)
    return len(original) - min(len(original), len(packed))
