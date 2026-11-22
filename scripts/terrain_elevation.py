"""Bilinear terrain elevation lookup shared across data preparation and Blender."""


def sample_elevation(terrain, x, y):
    cols, rows = terrain['cols'], terrain['rows']
    x0, y0, x1, y1 = terrain['bounds']
    u = max(0, min(cols - 1.001, (x - x0) / (x1 - x0) * (cols - 1)))
    v = max(0, min(rows - 1.001, (y - y0) / (y1 - y0) * (rows - 1)))
    i, j = int(u), int(v)
    a, b = u - i, v - j
    heights = terrain['heights']
    return (heights[j * cols + i] * (1 - a) + heights[j * cols + i + 1] * a) * (
        1 - b
    ) + (
        heights[(j + 1) * cols + i] * (1 - a) + heights[(j + 1) * cols + i + 1] * a
    ) * b


def make_elevation(terrain):
    return lambda x, y: sample_elevation(terrain, x, y)
