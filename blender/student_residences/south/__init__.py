"""Eight West Campus South student residences, in Blender campus metres."""

from geometry import Mesh

from . import elevations, primary

IDS = frozenset(primary.SPECS)


def refine(b, z, C, detail, baseline):
    number = primary.SPECS[b['id']][0]
    paint = primary.finishes(C)
    palette = elevations.palette(C, number)
    top = z + b['height']
    ring = b['polygons'][0][0]
    sides = {s for n, s in (*elevations.BAYS, *elevations.ENDS) if n == number}
    walls = []
    for a, c in zip(ring, ring[1:]):
        side = elevations.edge_side(a, c, b['bounds'], number)
        if side in sides:
            walls.append((a, c, side))
    rebuilt = {frozenset((tuple(a[:2]), tuple(c[:2]))) for a, c, _ in walls}

    mesh = Mesh()
    i = 0
    for name, _, end in baseline.parts:
        group = Mesh()
        shell = name.startswith('01_')
        replaced = name.startswith(('02_', '04_'))
        while i < len(baseline.f) and baseline.f[i][0] < end:
            f = baseline.f[i]
            index = i
            i += 1
            if replaced:
                continue
            points = [baseline.v[j] for j in f]
            mat = baseline.m[index]
            if shell:
                if min(v[2] for v in points) < top - 0.0001:
                    if frozenset(tuple(v[:2]) for v in points) in rebuilt:
                        continue
                    mat = paint['sand' if number in (3, 5, 10) else 'buff']
                elif number in (3, 4, 5, 10):
                    mat = paint['slate' if number in (3, 4) else 'gravel']
            group.face(points, mat, baseline.face_uvs.get(index))
        if group.f:
            mesh.add_part(name, group)
    roof = Mesh()
    primary.roof(roof, b, top, paint, number)
    mesh.add_part('南区_照片屋缘', roof)
    if number != 7:
        facade = Mesh()
        primary.primary_wall(facade, b, z, paint, detail)
        mesh.add_part('南区_实拍立面', facade)
    for a, c, side in walls:
        group = Mesh()
        wall = elevations.Wall(a, c, side[-1], z, palette, group)
        elevations.elevation(wall, number, side, b, detail)
        mesh.add_part('南区立面_' + side, group)
    return mesh
