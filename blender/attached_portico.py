"""Shared external entrance silhouette: platform, four supports and open parapet."""
import math


def add_attached_portico(mesh, entrance, z, colors):
    p = entrance['attachedPortico']; angle = math.radians(entrance['bearing'])
    nx, ny = math.sin(angle), math.cos(angle)
    tx, ty = ny, -nx
    x, y = entrance['center']; theta = -angle
    w, d, floor, soffit = (p[k] for k in ('width', 'depth', 'platformHeight', 'clearHeight'))
    def box(u, v, height, width, depth, thickness, material):
        mesh.box(x+tx*u+nx*v, y+ty*u+ny*v, z+height,
                 width, depth, thickness, colors[material], theta)
    box(0, d/2, (floor-.15)/2, w, d, floor+.15, 'stone')
    for i in range(p['steps']):
        height = p['stepBaseHeight']+(floor-p['stepBaseHeight'])*(p['steps']-i)/p['steps']
        box(0, d+(i+.5)*p['tread'], (height-.15)/2, w,
            p['tread']+.01, height+.15, 'stone')
    for cx, cy in p['columns']:
        mesh.box(cx, cy, z+(floor+soffit)/2, p['columnWidth'], p['columnWidth'],
                 soffit-floor, colors['white'], theta)
    box(0, d/2, soffit+p['slabThickness']/2, w, d, p['slabThickness'], 'white')
    roof = soffit+p['slabThickness']; rail = .12; ph = p['parapetHeight']
    # Two open rows on the front and sides. The attachment against the body
    # has no duplicate rail. Spacing is a declared simplification, not a survey.
    if ph:
        for height in (roof+rail/2, roof+ph/2, roof+ph-rail/2):
            box(0, d-.10, height, w, .20, rail, 'white')
            for u in (-w/2+.10, w/2-.10):
                box(u, d/2, height, .20, d, rail, 'white')
        bays = max(2, math.ceil(w/2.2))
        for i in range(bays+1):
            box(-w/2+.10+(w-.20)*i/bays, d-.10, roof+ph/2, .20, .20, ph, 'white')
        for u in (-w/2+.10, w/2-.10):
            box(u, d/2, roof+ph/2, .20, .20, ph, 'white')
    box(0, .04, floor+1.4, entrance['width'], .10, 2.8, 'glass')
    box(0, .06, floor+2.83, entrance['width']+.2, .14, .12, 'white')
