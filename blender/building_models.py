"""Shared geometry dispatch for campus building chunks and their incremental updates."""

import campus_offices
import student_residences
from generic_buildings import ordinary_building


def building_mesh(b, z, colors, detail):
    if b['id'] in student_residences.IDS:
        return student_residences.build(b, z, colors, detail)
    if b['id'] in campus_offices.IDS:
        return campus_offices.build(b, z, colors, detail, ordinary_building)
    return ordinary_building(b, z, colors, detail)
