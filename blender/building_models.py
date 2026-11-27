"""Shared geometry dispatch for campus building chunks and their incremental updates."""

import campus_offices
import east_north_buildings
import faculty_residences
import student_residences
import teaching_classrooms
from generic_buildings import ordinary_building

SURVEYED = {
    fid: module.build
    for module in (teaching_classrooms, east_north_buildings, faculty_residences)
    for fid in module.IDS
}


def building_mesh(b, z, colors, detail):
    if b['id'] in SURVEYED:
        return SURVEYED[b['id']](b, z, colors, detail)
    if b['id'] in student_residences.IDS:
        return student_residences.build(b, z, colors, detail)
    if b['id'] in campus_offices.IDS:
        return campus_offices.build(b, z, colors, detail, ordinary_building)
    return ordinary_building(b, z, colors, detail)
