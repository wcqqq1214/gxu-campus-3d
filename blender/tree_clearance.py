"""Reject trees crossing surfaces or contained in closed building components.

Both building and tree LODs participate. Road overhang is deliberately not a
building collision. This is one final exclusion rule, not a whole-site audit.
"""
import math
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from vegetation_layout import tree_rotation
from mesh_volumes import MeshVolumes

CLEARANCE_METERS = .03  # Model/export allowance, not a surveyed tree setback.


def bounds(vertices):
    return tuple(tuple(fn(v[i] for v in vertices) for i in range(3)) for fn in (min, max))


def overlaps(a, b, margin=CLEARANCE_METERS):
    return all(a[0][i] <= b[1][i]+margin and a[1][i]+margin >= b[0][i] for i in range(3))


def triangulate(vertices, faces):
    mesh = bpy.data.meshes.new('tree-clearance-temporary')
    try:
        mesh.from_pydata(vertices, [], faces)
        mesh.calc_loop_triangles()
        return [v.co.copy() for v in mesh.vertices], [tuple(t.vertices) for t in mesh.loop_triangles]
    finally:
        bpy.data.meshes.remove(mesh)


def filter_building_collisions(rows, templates, obstacles):
    """Inputs: grounded rows, {LOD: template objects}, (ID, LOD, Mesh) tuples.

    Deterministic survivor subset; neither a shared RNG nor a tree index is used.
    Only candidates with overlapping 3D bounds require triangle construction.
    """
    prepared = []
    for ident, lod, mesh in obstacles:
        if mesh.v and mesh.f:
            prepared.append(dict(id=ident, lod=lod, mesh=mesh, bounds=bounds(mesh.v), bvh=None, volumes=None))
    crowns = {}
    for lod, objects in templates.items():
        for typ, obj in enumerate(objects):
            obj.data.calc_loop_triangles()
            vertices = [v.co.copy() for v in obj.data.vertices]
            triangles = [tuple(t.vertices) for t in obj.data.loop_triangles]
            crowns[lod, typ] = (vertices, triangles, bounds(vertices), MeshVolumes(vertices, triangles))
    kept, removed = [], []
    checked = 0
    for row in rows:
        if len(row) < 5 or not all(math.isfinite(v) for v in row):
            raise ValueError('Building clearance requires finite final tree elevations')
        x, y, h, typ, z = row[:5]
        transform = Matrix.Translation((x, y, z)) @ Matrix.Rotation(tree_rotation(x,y), 4, 'Z') @ Matrix.Scale(h/9, 4)
        hit = None
        for (tree_lod, tree_type), (vertices, triangles, box, tree_volumes) in crowns.items():
            if tree_type != typ:
                continue
            corners = [transform @ Vector((a,b,c)) for a in (box[0][0],box[1][0])
                       for b in (box[0][1],box[1][1]) for c in (box[0][2],box[1][2])]
            candidate_bounds = bounds(corners)
            nearby = [o for o in prepared if overlaps(candidate_bounds,o['bounds'])]
            if not nearby:
                continue
            world = [transform @ v for v in vertices]
            tree_bvh = BVHTree.FromPolygons(world, triangles, all_triangles=True, epsilon=CLEARANCE_METERS/2)
            inverse = transform.inverted()
            tree_points = [transform @ Vector(point) for point in tree_volumes.representatives]
            for obstacle in nearby:
                if obstacle['bvh'] is None:
                    vs, ts = triangulate(obstacle['mesh'].v, obstacle['mesh'].f)
                    obstacle['bvh'] = BVHTree.FromPolygons(vs, ts, all_triangles=True, epsilon=CLEARANCE_METERS/2)
                    obstacle['volumes'] = MeshVolumes(vs, ts)
                checked += 1
                pairs = tree_bvh.overlap(obstacle['bvh'])
                kind, witness = 'surface-intersection', None
                if not pairs:
                    witness = obstacle['volumes'].witness_inside(tree_points)
                    kind = 'tree-component-inside-building'
                    if witness is None and tree_volumes.shells:
                        local_points = (inverse @ Vector(point) for point in obstacle['volumes'].representatives_in_bounds(candidate_bounds))
                        local = tree_volumes.witness_inside(local_points)
                        if local is not None:
                            witness = tuple(transform @ Vector(local))
                            kind = 'building-component-inside-tree'
                if pairs or witness is not None:
                    hit = dict(tree=list(row), buildingId=obstacle['id'], buildingLOD=obstacle['lod'],
                               treeLOD=tree_lod, trianglePairs=len(pairs), collisionKind=kind,
                               containmentWitness=witness)
                    break
            if hit:
                break
        if hit:
            removed.append(hit)
        else:
            kept.append(row)
    return kept, dict(inputTrees=len(rows), retainedTrees=len(kept), removed=removed,
                      testedPairs=checked, clearanceMeters=CLEARANCE_METERS,
                      treeLODs=list(templates), buildingLODs=sorted({x['lod'] for x in prepared}),
                      testedClosedBuildingComponents=sum(len(o['volumes'].shells) for o in prepared if o['volumes'] is not None),
                      testedOpenBuildingComponents=sum(o['volumes'].open_components for o in prepared if o['volumes'] is not None),
                      method='Final grounded trees versus buildings in both LODs: 3D AABB, BVH surface overlap, then bidirectional containment in closed orientable components.',
                      limitations='Open/non-manifold components are not capped; containment is only established for detected closed shells. Does not replace sourced no-tree masks or final road/sports/water/entrance exclusions.')
