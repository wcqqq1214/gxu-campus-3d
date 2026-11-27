"""Mesh operations shared by the Alumni Hall and Security Office."""

from bisect import bisect_left

from geometry import material


def pigment(C, name, hexcolor):
    key = 'GXU B ' + name
    if key not in C:
        srgb = [int(hexcolor[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        C[key] = material(
            key,
            [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in srgb],
        )
    return C[key]


def remove_faces(mesh, predicate):
    keep = [
        i
        for i, f in enumerate(mesh.f)
        if not predicate([mesh.v[j] for j in f], mesh.m[i])
    ]
    used = sorted({j for i in keep for j in mesh.f[i]})
    indices = {v: i for i, v in enumerate(used)}
    mesh.v = [mesh.v[j] for j in used]
    mesh.f = [tuple(indices[j] for j in mesh.f[i]) for i in keep]
    mesh.m = [mesh.m[i] for i in keep]
    mesh.face_uvs = {
        j: mesh.face_uvs[i] for j, i in enumerate(keep) if i in mesh.face_uvs
    }
    mesh.parts = [
        (n, bisect_left(used, a), bisect_left(used, b)) for n, a, b in mesh.parts
    ]
