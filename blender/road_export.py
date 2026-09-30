"""Conform clipped-road T junctions only in temporary export geometry."""
from shore_geometry import conform_edges


def conform_foundation_road_exports(groups, records):
    result = dict(groups)
    for record in records:
        margin = record.get('roadExportConformMargin')
        if margin is None:
            continue
        road = result['roads']
        if road.parts:
            raise ValueError('Aggregated export roads must not contain named vertex parts')
        x0, y0, x1, y1 = record['bounds']
        conformed = conform_edges(road, (x0-margin, y0-margin, x1+margin, y1+margin),
                                  epsilon=1e-4, preserve_vertical_faces=True)
        conformed.ground_uv_bounds = list(road.ground_uv_bounds)
        conformed.xy_uv_materials = set(road.xy_uv_materials)
        result['roads'] = conformed
    return result
