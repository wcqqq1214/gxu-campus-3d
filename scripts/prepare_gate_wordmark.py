"""Trace the official GXU wordmark into reusable, triangulated glyph outlines.

Usage: work/venv/bin/python scripts/prepare_gate_wordmark.py reference.jpg
The source image is a build input only; the website ships raised mesh lettering.
"""
import argparse
import hashlib
import json
from pathlib import Path

import mapbox_earcut
import numpy as np
from PIL import Image
from shapely.geometry import box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://www.gxu.edu.cn/__local/2/07/A9/943E1057E746C4E92A28353C75B_04DB7951_2FCED.jpg?e=.jpg'


def trace(image, bounds):
    ink = np.asarray(image.crop(bounds).convert('L')) < 160
    runs = []
    for y, row in enumerate(ink):
        edges = np.flatnonzero(np.diff(np.pad(row.astype(np.int8), (1, 1))))
        runs.extend(box(int(a), y, int(b), y + 1) for a, b in zip(edges[::2], edges[1::2]))
    shape = unary_union(runs)
    pieces = [p.simplify(2.0, preserve_topology=True) for p in shape.geoms if p.area >= 6]
    x0, y0, x1, y1 = unary_union(pieces).bounds
    scale = y1 - y0
    outlines = []
    for polygon in pieces:
        # Flip image Y into upward model Z, then orient all outlines consistently.
        from shapely.geometry import Polygon
        rings = [[((x - (x0 + x1) / 2) / scale, ((y0 + y1) / 2 - y) / scale)
                  for x, y in ring.coords[:-1]] for ring in [polygon.exterior, *polygon.interiors]]
        polygon = orient(Polygon(rings[0], rings[1:]), sign=1)
        rings = [[[round(v, 6) for v in p] for p in ring.coords[:-1]]
                 for ring in [polygon.exterior, *polygon.interiors]]
        vertices = np.array([p for ring in rings for p in ring], dtype=np.float64)
        ends = np.cumsum([len(ring) for ring in rings], dtype=np.uint32)
        triangles = mapbox_earcut.triangulate_float64(vertices, ends).tolist()
        assert len(triangles) >= 3 and polygon.is_valid
        outlines.append({'rings': rings, 'triangles': triangles})
    return outlines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    args = parser.parse_args()
    image = Image.open(args.reference)
    if image.size != (2000, 1600):
        raise ValueError('Expected the official 2000 × 1600 emblem image')
    # Separate handwritten characters below the circular seal, above the Latin name.
    bounds = [(185, 825, 600, 1355), (680, 825, 950, 1355),
              (1040, 825, 1380, 1355), (1460, 825, 1810, 1355)]
    result = {'sourcePage': 'https://www.gxu.edu.cn/xdgl1/xxbs1.htm',
              'sourceImage': SOURCE, 'sourceSha256': hashlib.sha256(args.reference.read_bytes()).hexdigest(),
              'method': 'Luminance < 160; components >= 6 px²; topology-preserving 2 px simplification; per-glyph unit height.',
              'glyphs': [{'character': c, 'sourceBounds': b, 'outlines': trace(image, b)}
                         for c, b in zip('广西大学', bounds)]}
    target = ROOT / 'blender/fonts/gxu-wordmark.json'
    target.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('Saved', target, target.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
