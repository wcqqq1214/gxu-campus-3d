"""Spatial grid used by the building catalogue and model exporter."""

import math

CHUNK_METERS = 360


def grid_chunk(x, y):
    def label(coordinate):
        cell = math.floor(coordinate / CHUNK_METERS)
        return ('p' if cell >= 0 else 'n') + str(abs(cell))

    return f'chunk-{label(x)}-{label(y)}'
