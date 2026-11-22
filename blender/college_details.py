"""Exterior details shared by the photo-based college buildings (campus metres)."""

import math

from geometry import Mesh


def flight(mesh, x, wall_y, z, width, count, tread, rise, material, north=False):
    """Solid adjacent treads, highest against the landing; z is the foot elevation."""
    outward = 1 if north else -1
    for i in range(count):
        height = (count - i) * rise
        y = wall_y + outward * (i + 0.5) * tread
        mesh.box(x, y, z + height / 2, width, tread, height, material)


def pane(mesh, x, y, z, width, height, normal, C, detail, glass=None):
    """A complete window including frame and mullions, mounted to the wall plane."""
    nx, ny = normal
    angle = math.atan2(nx, -ny)
    mesh.box(
        x + nx * 0.075,
        y + ny * 0.075,
        z,
        width + 0.15,
        0.15,
        height + 0.15,
        C['gateTrim'],
        angle,
    )
    mesh.box(
        x + nx * 0.17,
        y + ny * 0.17,
        z,
        width,
        0.07,
        height,
        C['glass'] if glass is None else glass,
        angle,
    )
    if detail:
        mesh.box(
            x + nx * 0.22, y + ny * 0.22, z, 0.065, 0.05, height, C['metal'], angle
        )
        mesh.box(
            x + nx * 0.22,
            y + ny * 0.22,
            z + height * 0.23,
            width,
            0.05,
            0.06,
            C['metal'],
            angle,
        )


def sign(mesh, text, x, y, z, width, height, finish, normal_angle):
    from south_gate import inscription

    letters = inscription(
        text, x, y, z, width, height, finish, True, flat=True, curve_resolution=2
    )
    letters.rotate_z(x, y, normal_angle)
    mesh.extend(letters)


def ellipse(mesh, x, y, z, w, h, normal, mat):
    nx, ny = normal
    points = [
        (
            x - ny * w * 0.5 * math.cos(a * math.tau / 24),
            y + nx * w * 0.5 * math.cos(a * math.tau / 24),
            z + h * 0.5 * math.sin(a * math.tau / 24),
        )
        for a in range(24)
    ]
    mesh.face(points, mat)


def shell(b, z, height, wall, cap):
    body = Mesh()
    body.extrude(b['polygons'], b['roofTriangles'], z - 0.5, height + 0.5, wall, cap)
    return body
