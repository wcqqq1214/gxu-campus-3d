"""Planar strips shared by derived road geometry and final planting masks."""
from shapely.geometry import Polygon
from shapely.ops import unary_union


def strip_shape(path,axes,sections,left=2,right=3,extra=0):
    if len(path) < 2 or len(path) != len(axes) or len(path) != len(sections):
        raise ValueError('Road footprint requires matching path, frames and sections')
    edges=[]
    for p,(ux,uy),section in zip(path,axes,sections):
        edges.append([(p[0]-uy*off,p[1]+ux*off) for off in [section[left]-extra,section[right]+extra]])
    return unary_union([Polygon([a[0],b[0],b[1],a[1]]) for a,b in zip(edges,edges[1:])])
