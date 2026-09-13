"""Low continuous hedge geometry; no tree template, trunk or invented planter."""
import math
import bpy
from geometry import Mesh
from tree_layout import ground_tree_rows


def hedge_mesh(item, terrain_vertices, terrain_faces, colors):
    a, b = item['line']
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    n = max(2, math.ceil(length / .8))
    # Rounded shoulder above a full low foliage base; all dimensions stay
    # within the explicitly checked planting footprint and height envelope.
    profile = [(-.5, 0), (.5, 0), (.5, .64), (.35, .90),
               (0, 1), (-.35, .90), (-.5, .64)]
    xy, rises = [], []
    for i in range(n + 1):
        fraction = i / n
        taper = .86 if i in (0, n) else 1
        crown = .9 if i in (0, n) else 1 - .035 * math.sin(i * .73) ** 2
        for side, top in profile:
            offset = side * item['widthMeters'] * taper
            xy.append([a[0] + dx * fraction - uy * offset,
                       a[1] + dy * fraction + ux * offset, 1, 0])
            rises.append(-.03 if top == 0 else top * item['heightMeters'] * crown)
    grounded = ground_tree_rows(xy, terrain_vertices, terrain_faces)
    mesh = Mesh()
    vertices = [(p[0], p[1], p[4] + rise) for p, rise in zip(grounded, rises)]
    count = len(profile)
    for i in range(n):
        for j in range(count):
            k = (j + 1) % count
            mesh.face([vertices[i*count+j], vertices[i*count+k],
                       vertices[(i+1)*count+k], vertices[(i+1)*count+j]],
                      colors['leaf2'])
    # A single material keeps all boundary vertices in one Draco primitive.
    # Separate shade materials quantize the shared seam independently and
    # leave the decoded shell open. The profile supplies geometric shading.
    mesh.face(vertices[:count][::-1], colors['leaf2'])
    mesh.face(vertices[-count:], colors['leaf2'])
    mesh.parts = [('独立低矮绿篱 · 贴地叶团', 0, len(mesh.v))]
    return mesh


def sync_source_low_planting(base):
    """Keep low foliage grounded when incremental road/terrain work changes it."""
    collection = bpy.data.objects['terrain'].users_collection[0]
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith('vegetation-low-'):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data.users == 0: bpy.data.meshes.remove(data)
    for key, mesh in base.items():
        if key.startswith('vegetation-low-'):
            mesh.object(key, collection, {'layer': 'vegetation', 'plantingId': key.removeprefix('vegetation-low-')})
