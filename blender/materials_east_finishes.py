"""Photo-located surface boundaries between the materials side stair and north lane."""

from entry_forecourt_geometry import _split_finish
from geometry import Mesh

# W increases southwards and D westwards. The three panorama intersections
# constrain both ends of the transverse walk. The rounded kerb is interpolated.
FRONT_LAWN = [
    (-25.39, -11.91),
    (-20.45, -12.24),
    (-19.32, -7.59),
    (-22.94, -7.02),
    (-23.63, -7.02),
    (-24.22, -7.21),
    (-24.74, -7.57),
    (-25.11, -8.06),
    (-25.31, -8.67),
]
BACK_LAWN = [
    (-17, -12.45),
    (-13.05, -12.45),
    (-13.05, -9.26),
    (-13.45, -8.10),
    (-16.57, -7.47),
]
WALK = [(-20.15, -14.47), (-17, -14.47), (-17, -12.45), (-20.45, -12.24)]
WALK_WEST = [(-20.45, -12.24), (-17, -12.45), (-16.57, -7.47), (-19.32, -7.59)]
PARKING = [
    (-25.39, -19.75),
    (-20.15, -19.75),
    (-20.15, -14.47),
    (-20.45, -12.24),
    (-25.39, -11.91),
]


def signed_area(poly):
    return sum(p[0] * q[1] - p[1] * q[0] for p, q in zip(poly, poly[1:] + poly[:1]))


def zones():
    # Inset from each edge in metres, including around the rounded corner.
    from mathutils import Vector
    from mathutils.geometry import intersect_line_line_2d

    def bed(poly):
        if signed_area(poly) < 0:
            poly = poly[::-1]
        lines = []
        for a, b in zip(poly, poly[1:] + poly[:1]):
            a, b = Vector(a), Vector(b)
            vec = b - a
            offset = Vector((-vec.y, vec.x)).normalized() * 0.11
            lines.append((a + offset, b + offset))
        # Blender's helper intersects bounded segments, hence extend each line.
        lines = [(a - (b - a), b + (b - a)) for a, b in lines]
        inner = [
            tuple(intersect_line_line_2d(*lines[i - 1], *line))
            for i, line in enumerate(lines)
        ]
        return [(inner, 'grass'), (poly, 'curb')]

    return [
        *bed(FRONT_LAWN),
        *bed(BACK_LAWN),
        (WALK, 'stone'),
        (WALK_WEST, 'stone'),
        (PARKING, 'materialsGrassPaver'),
        # Two convex pieces follow the bend alongside the walk.
        (
            [(-25.39, -11.91), (-19.32, -7.59), (-19.32, -4.0), (-25.39, -3.9)],
            'asphalt',
        ),
        (
            [
                (-19.32, -7.59),
                (-16.57, -7.47),
                (-16.57, -4.15),
                (-19.32, -4),
            ],
            'asphalt',
        ),
        (
            [(-16.57, -7.47), (-13.45, -8.10), (-13.45, -4.35), (-16.57, -4.15)],
            'asphalt',
        ),
    ]


def apply_finishes(mesh, first, point, local, colors):
    """Inlay the measured shapes in existing triangles at their actual grade.

    The parking changes ownership at the existing road seam. Both owners use
    identical boundaries; fragments keep their original heights and exterior UVs.
    """
    from geometry import tile_material

    tile_material(
        colors,
        'materialsGrassPaver',
        'materials-parking-course.jpg',
        (0.44, 0.48, 0.38),
    )
    masks = [(p if signed_area(p) > 0 else p[::-1], mat) for p, mat in zones()]
    _partition(mesh, first, point, local, masks, colors)


# The terrain-derived parking profile forms a crest immediately in front of the
# photographed stone face. Ease that crest between the accepted road surface
# at the outer kerb and the fixed wall foot. The other three boundaries also
# have zero offset; the rear parking-to-road connection is outside this area.
GRADE_W = (-27.1, -26.1, -25.39, -24.1, -22.4, -21.0, -20.16, -19.32, -18, -17, -16)
GRADE_D = (
    -29,
    -26,
    -23,
    -21,
    -20,
    -19.75,
    -18.9,
    -17,
    -14.47,
    -12.45,
    -10,
    -8.4,
    -7.47,
    -6,
    -4.0,
)


def grade_apron(mesh, first, point, local, *, soil=False):
    # Lower the inherited road and bedding before setting the observed lawn grade.
    from materials_north_road import lower_north_street

    lower_north_street(mesh, first, point, local)

    masks = []
    for a, b in zip(GRADE_W, GRADE_W[1:]):
        for l, r in zip(GRADE_D, GRADE_D[1:]):
            east_shoulder = r <= -17
            if not east_shoulder and (
                a >= -20.16 and r <= -14.47 or a >= -17 and r <= -12.45
            ):
                continue

            def vertex(w, d):
                end = -20.16 + 0.84 * min(1, max(0, (d + 12.24) / 4.65))
                t = min(1, max(0, (end - w) / (end + 25.39)))
                toe = 2.71 + 0.025 * min(1, max(0, (d + 12.45) / 4.98))
                # Keep the street-side lawn corner 0.251 m below the wall foot.
                height = toe - (toe - 2.459) * t
                weight = min(1, (w + 27.1) / 1.0, (d + 29) / 9.25, (-4 - d) / 1.8)
                if east_shoulder and a >= -20.16:
                    # Wrap the low parking grade around the existing wall end;
                    # the raised terrace takes over behind the masonry.
                    weight *= min(1, (-17 - d) / 2.75) * min(1, (-16 - w) / 4.16)
                if w >= -17:
                    weight *= max(0, -16 - w)
                return w, d, height, max(0, weight)

            q = [
                vertex(a, l),
                vertex(b, l),
                vertex(b, r),
                vertex(a, r),
            ]
            for tri in [q[:3], [q[0], q[2], q[3]]]:
                x, y, z = tri
                det = signed_area(tri)

                def coefficients(k):
                    sx = (
                        (y[k] - x[k]) * (z[1] - x[1]) - (z[k] - x[k]) * (y[1] - x[1])
                    ) / det
                    sy = (
                        (y[0] - x[0]) * (z[k] - x[k]) - (z[0] - x[0]) * (y[k] - x[k])
                    ) / det
                    return sx, sy, x[k] - sx * x[0] - sy * x[1]

                masks.append((tri, (coefficients(2), coefficients(3))))
    _partition(mesh, first, point, local, masks, None, soil=soil)


def _partition(mesh, first, point, local, masks, colors, *, soil=False):
    extent = [point(w, d, 0) for w in (-27.11, -9.39) for d in (-29.01, -0.27)]
    xmin, xmax = min(p[0] for p in extent), max(p[0] for p in extent)
    ymin, ymax = min(p[1] for p in extent), max(p[1] for p in extent)
    detail = Mesh()
    kept = []
    mats = []
    uvmap = {}
    decorative = {
        colors[k]
        for k in ('green', 'roadWhite', 'roadYellow')
        if colors and k in colors
    }
    original_uv = mesh.face_uvs
    for i, (face, mat) in enumerate(zip(mesh.f, mesh.m)):
        pts = [mesh.v[j] for j in face]
        if i >= first and not (
            all(p[0] < xmin for p in pts)
            or all(p[0] > xmax for p in pts)
            or all(p[1] < ymin for p in pts)
            or all(p[1] > ymax for p in pts)
        ):
            polygon = [local(p) for p in pts]
            # Local frame reverses handedness. Skip sides, undersides and rails.
            area = signed_area(polygon)
            if soil and abs(area) <= 1e-7:
                # Razor-thin skirts from the old terrain cut can change winding
                # on float32 export. Seat their vertices below the new finish.
                moved = []
                for w, d, h in polygon:
                    for tri, (plane, weight) in masks:
                        if all(
                            (b[0] - a[0]) * (d - a[1]) - (b[1] - a[1]) * (w - a[0])
                            >= -1e-8
                            for a, b in zip(tri, tri[1:] + tri[:1])
                        ):
                            t = min(
                                1, max(0, weight[0] * w + weight[1] * d + weight[2])
                            )
                            target = plane[0] * w + plane[1] * d + plane[2] - 0.060
                            h = min(h, h + t * (target - h))
                            break
                    moved.append(point(w, d, h))
                detail.face(moved, mat, original_uv.get(i))
                continue
            if area < -1e-7 or soil and area > 1e-7:
                rest = [polygon]
                inside = []
                for mask, name in masks:
                    nxt = []
                    for part in rest:
                        a, b = _split_finish(part, mask)
                        if a:
                            inside.append((a, name))
                            nxt.extend(b)
                        else:
                            nxt.append(part)
                    rest = nxt
                if inside:
                    uv = original_uv.get(i)
                    if uv and (rest or colors is None):
                        # Faces here are planar; affine interpolation preserves original mapping.
                        a = polygon[0]
                        j, k = max(
                            (
                                (j, k)
                                for j in range(1, len(polygon) - 1)
                                for k in range(j + 1, len(polygon))
                            ),
                            key=lambda jk: abs(
                                signed_area([a, polygon[jk[0]], polygon[jk[1]]])
                            ),
                        )
                        b, c = polygon[j], polygon[k]
                        det = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (
                            c[0] - a[0]
                        )

                        def texture(p):
                            u = (
                                (p[0] - a[0]) * (c[1] - a[1])
                                - (p[1] - a[1]) * (c[0] - a[0])
                            ) / det
                            v = (
                                (b[0] - a[0]) * (p[1] - a[1])
                                - (b[1] - a[1]) * (p[0] - a[0])
                            ) / det
                            return tuple(
                                uv[0][t]
                                + u * (uv[j][t] - uv[0][t])
                                + v * (uv[k][t] - uv[0][t])
                                for t in (0, 1)
                            )

                    for part in rest:
                        detail.face(
                            [point(*p) for p in part],
                            mat,
                            [texture(p) for p in part] if uv else None,
                        )
                    if mat not in decorative:
                        for part, name in inside:
                            if colors is None:
                                height, weight = name
                                coords = []
                                for w, d, h in part:
                                    target = (
                                        height[0] * w
                                        + height[1] * d
                                        + height[2]
                                        - (
                                            (0.060 if area > 0 else 0.045)
                                            if soil
                                            else 0
                                        )
                                    )
                                    t = min(
                                        1,
                                        max(
                                            0, weight[0] * w + weight[1] * d + weight[2]
                                        ),
                                    )
                                    coords.append(point(w, d, h + t * (target - h)))
                                detail.face(
                                    coords,
                                    mat,
                                    [texture(p) for p in part] if uv else None,
                                )
                                continue
                            if name is None:
                                continue
                            if name == 'materialsGrassPaver':
                                uv = [
                                    (
                                        (w + 25.39) / 0.21,
                                        (d + 11.91 + 0.067 * (w + 25.39) + 0.105)
                                        / (12 * 0.21),
                                    )
                                    for w, d, _ in part
                                ]
                            else:
                                uv = [(w / 2.6, d / 2.6) for w, d, _ in part]
                            detail.face(
                                [point(*p) for p in part],
                                colors[name],
                                uv,
                            )
                    continue
        if i in original_uv:
            uvmap[len(kept)] = original_uv[i]
        kept.append(face)
        mats.append(mat)
    mesh.f, mesh.m, mesh.face_uvs = kept, mats, uvmap
    mesh.extend(detail)


def cut_parking_seam(roads, entry, point, local, colors):
    patch = next(
        p
        for p in entry['recessedStairEntry']['landscape']['groundPatches']
        if p['id'] == 'north-parking'
    )
    edge = sorted((d, w) for w, d in patch['boundary'] if w < -21)
    masks = []
    for (l, a), (r, b) in zip(edge, edge[1:]):
        if l >= -4 or r <= -20 or r == l:
            continue
        end = min(-4, r)
        wb = a + (b - a) * (end - l) / (r - l)
        ring = [(a - 0.09, l), (a + 0.015, l), (wb + 0.015, end), (wb - 0.09, end)]
        masks.append((ring, None))
    _partition(roads, 0, point, local, masks, colors)


def seat_passage_floor(terrain, bed, point, local):
    """Raise or cut the source soil to the same graded first-bay floor."""
    masks = []
    for face in bed.f[bed.passage_start :]:
        a, b, c = [local(bed.v[i]) for i in face]
        tri = [a, b, c]
        det = signed_area(tri)
        sx = ((b[2] - a[2]) * (c[1] - a[1]) - (c[2] - a[2]) * (b[1] - a[1])) / det
        sy = ((b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])) / det
        plane = (sx, sy, a[2] - sx * a[0] - sy * a[1])
        masks.append((tri if det > 0 else tri[::-1], (plane, (0, 0, 1))))
    _partition(terrain, 0, point, local, masks, None, soil=True)
