"""Shared glazing planes and shallow octagonal screens on solid backing walls.

Screen holes reveal a dark backing plane. This is an exterior approximation,
not a cut-out building interior or a surveyed reproduction of floral tracery.
"""
import math
from facade_bands import frame


def add_panels(mesh, facade, z, C):
    length, u, n, theta, point = frame(facade)
    for p in facade['rule'].get('panels', []):
        w = (p['to']-p['from'])*length; h = p['top']-p['bottom']; fw = p['frameWidth']
        x, y = point((p['from']+p['to'])/2, .025)
        mesh.box(x, y, z+(p['bottom']+p['top'])/2, w, .03, h,
                 C['glass'] if p['type']=='glazing' else C['dark'], theta)

        def bar(a, b, width):
            ds, dh = b[0]-a[0], b[1]-a[1]; size = math.hypot(ds, dh)
            vs, vh = -dh/size*width/2, ds/size*width/2
            corners = [(a[0]-vs, a[1]-vh), (b[0]-vs, b[1]-vh),
                       (b[0]+vs, b[1]+vh), (a[0]+vs, a[1]+vh)]
            if u[1]*n[0]-u[0]*n[1] < 0:
                corners.reverse()
            def at(s, up, depth):
                px, py = point(p['from']+s/length, depth)
                return (px, py, z+p['bottom']+up)
            front = [at(s, up, .05+p['depth']) for s, up in corners]
            back = [at(s, up, .05) for s, up in corners]
            mesh.face(front, C['white']); mesh.face(back[::-1], C['white'])
            for i in range(4):
                j = (i+1)%4
                mesh.face([front[j], front[i], back[i], back[j]], C['white'])

        # Frames are entirely contained by the configured outer rectangle.
        bar((fw/2, 0), (fw/2, h), fw)
        bar((w-fw/2, 0), (w-fw/2, h), fw)
        bar((fw, fw/2), (w-fw, fw/2), fw)
        bar((fw, h-fw/2), (w-fw, h-fw/2), fw)
        cw = (w-2*fw)/p['columns']; ch = (h-2*fw)/p['rows']
        if p['type']=='glazing':
            for col in range(1, p['columns']):
                s = fw+col*cw; bar((s, fw), (s, h-fw), fw*.65)
            for row in range(1, p['rows']):
                up = fw+row*ch; bar((fw, up), (w-fw, up), fw*.65)
            continue
        # Adjacent octagons share straight edges. Deduplicate these bars;
        # the small corner diamonds remain open like the reference screen.
        edges = set()
        for row in range(p['rows']):
            for col in range(p['columns']):
                s = fw+col*cw; up = fw+row*ch
                octagon = [(s+cw*dx, up+ch*dy) for dx, dy in
                           [(0,.3),(.3,0),(.7,0),(1,.3),(1,.7),(.7,1),(.3,1),(0,.7)]]
                for a, b in zip(octagon, octagon[1:]+octagon[:1]):
                    key = tuple(sorted(tuple(round(v, 8) for v in q) for q in (a, b)))
                    if key not in edges:
                        edges.add(key); bar(a, b, fw*.55)


def panel_replaces_window(facade, fraction, width, center_height, height):
    """Remove intersecting default windows, including the larger near frame."""
    length = math.dist(facade['start'], facade['end'])
    rectangle = (fraction*length-(width+.30)/2, fraction*length+(width+.30)/2,
                 center_height-(height+.30)/2, center_height+(height+.30)/2)
    return any(rectangle[0] < p['to']*length and rectangle[1] > p['from']*length
               and rectangle[2] < p['top'] and rectangle[3] > p['bottom']
               for p in facade['rule'].get('panels', []))
