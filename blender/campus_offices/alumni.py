"""West 6A courtyard, stepped wings and recessed entrance."""

from .alumni_east import east_body, refine_alumni
from .alumni_elevations import replace_walls
from .alumni_gallery import add_gallery, west_form
from .alumni_walls import finishes
from .civic import build as civic_build


def build(b, datum, C, detail, ordinary):
    b = west_form(b)
    b = east_body(b)
    mesh = refine_alumni(
        civic_build(b, datum, C, detail, ordinary), b, datum, C, detail
    )
    colors = finishes(C)
    replace_walls(mesh, datum, C, colors, detail)
    add_gallery(mesh, datum, colors, detail, b, C)
    return mesh
