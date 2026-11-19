"""Grade the south branch into the descending West 5 carriageway."""

from bisect import bisect_right

from geometry import Mesh


def junction_mesh(data, colors, terrain_height, road_height, bank_height):
    edge = data['mainEdge']
    xs = [p[0] for p in edge]
    south = data['south']

    def smooth(t):
        t = min(1, max(0, t))
        return t * t * (3 - 2 * t)

    def height(x, y, material, edge_distance=0):
        i = min(len(edge) - 2, max(0, bisect_right(xs, x) - 1))
        a, b = edge[i : i + 2]
        t = (x - a[0]) / (b[0] - a[0])
        edge_y = a[1] + t * (b[1] - a[1])
        entry_z = a[2] + t * (b[2] - a[2])
        depth = edge_y - y
        blend = smooth(depth / (edge_y - south))
        natural = terrain_height(x, y)
        # Existing road geometry is authoritative at the tie-in. Extend its
        # crossfall smoothly under the shoulders using the sampled terrain.
        target = road_height(x, y)
        asphalt = entry_z + (target - entry_z) * blend
        if material == 'asphalt':
            return asphalt
        lip = 0.125 * (1 - smooth((depth - 6) / 17))
        if material == 'curb':
            return asphalt + lip
        walk = asphalt + lip + 0.025 * (1 - blend)
        if material == 'pavingRed':
            return walk
        west, _, east, _ = data['cut']['bounds']
        side = 1 - smooth(min(x - west, east - x) / 4)
        soil = max(natural, bank_height(x, y))
        # At the cut sides match the original bridge bank; at the southern
        # seam match the incoming grass right up to the existing raised road.
        foot = walk + (soil - walk) * side
        foot += (natural - foot) * smooth((south + 4 - y) / 4)
        return foot + (soil - foot) * smooth(edge_distance / 3)

    mesh = Mesh()
    for layer in data['layers']:
        mat = layer['material']
        points = layer['vertices']
        distances = layer.get('edgeDistances', [0] * len(points))
        vertices = [
            (x, y, height(x, y, mat, d) + layer.get('zOffset', 0))
            for (x, y), d in zip(points, distances)
        ]
        indices = layer['triangles']
        for i in range(0, len(indices), 3):
            mesh.face([vertices[j] for j in indices[i : i + 3]], colors[mat])
    for key, lower, upper, material in (
        ('kerbs', 'asphalt', 'curb', 'curb'),
        ('walkEdges', 'pavingRed', 'grass', 'bridgeConcrete'),
    ):
        for line in data[key]:
            for a, b in zip(line, line[1:]):
                points = [
                    (*p, height(*p, mat))
                    for p, mat in ((a, lower), (a, upper), (b, upper), (b, lower))
                ]
                if (
                    max(
                        abs(points[0][2] - points[1][2]),
                        abs(points[2][2] - points[3][2]),
                    )
                    > 0.001
                ):
                    mesh.face(points, colors[material])
    return mesh


def cut_ground(mesh, cut):
    from road_display_cleanup import trim_mesh

    # Retain explicit loop UVs on previously graded plazas and service roads.
    if mesh.face_uvs:
        mesh.source_uvs = [
            mesh.face_uvs.get(i, [(0, 0)] * len(face)) for i, face in enumerate(mesh.f)
        ]
    result, _ = trim_mesh(mesh, [cut])
    if mesh.face_uvs:
        result.face_uvs = {
            i: result.source_uvs[i]
            for i, src in enumerate(result.source_face_indices)
            if src in mesh.face_uvs
        }
    return result
