"""Build one office Mesh in campus metres using the scene's ordinary-building callback."""

from .facades import measured, palette, relief, shape_body, structures
from .forms import animal, civic_front, graduate, security
from .structure import full_details

MODEL_IDS = tuple(
    f'relation/{key}' if key == '11564704' else f'way/{key}' for key in measured()
)


def build(b, datum, C, detail, ordinary):
    """Return a complete world-space Mesh for the requested near (True) or base (False) LOD."""
    key = b['id'].split('/')[-1]
    palette(C)
    if key == '1501460942':
        b = graduate(b)
    elif key == '11564704':
        b = animal(b)

    elif key == '759096563':
        b = security(b)
    elif key in {'759337787', '759147086'}:
        b = civic_front(b)

    ordinary_colors = C
    if key in {'759337787', '759096563', '759147086', '11564704'}:
        ordinary_colors = {
            **C,
            'glass': C['Office opening'],
            'shadeGlass': C['Office deep'],
        }
    mesh = ordinary(b, datum, ordinary_colors, detail)
    shape_body(mesh, b, C, datum)
    mesh.add_part('实拍入口、屋面及阳台', structures(key, datum, C, detail))
    mesh.add_part('实拍可见立面', relief(key, datum, C, detail))
    if key in {'759337787', '759147086', '759096563', '11564704', '1501460942'}:
        mesh.add_part('多角度屋体、窗框与门厅', full_details(key, datum, C, detail))
    return mesh
