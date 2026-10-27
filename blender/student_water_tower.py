"""Historic tower beside the student centre, from visible south-facing evidence.

GXU gallery + BV1US4y1V7dg 00:31 establish brick shaft / wider dark tank.
Dimensions are photo-scaled estimates; the mapped circle anchors tank width.
Unseen rear openings are not duplicated from the visible south elevation.
"""
import math
from geometry import Mesh, MATERIALS, material

TOWER_ID = 'way/955987491'


def water_tower(b, z, C, detail):
    for name, colour in [('studentTowerBrick', (.50, .22, .105)),
                         ('studentTowerTank', (.22, .205, .18))]:
        if name not in C:
            C[name] = next((i for i, m in enumerate(MATERIALS) if m.name == name), None)
            if C[name] is None:
                C[name] = material(name, colour)
    m = Mesh(); x, y = b['center']; h = b['height']
    radius = min(b['bounds'][2]-b['bounds'][0], b['bounds'][3]-b['bounds'][1])/2
    shaft = radius*.65; neck = h*.84; tank_bottom = h*.865
    brick = C['studentTowerBrick']; tank = C['studentTowerTank']
    n = 48 if detail else 24
    m.cylinder(x,y,z+neck/2,shaft,neck,brick,n)
    m.cylinder(x,y,z+(neck+tank_bottom)/2,shaft,tank_bottom-neck,tank,n,topr=radius)
    m.cylinder(x,y,z+(tank_bottom+h)/2,radius,h-tank_bottom,tank,n)
    for level in (tank_bottom,h-.10):
        m.cylinder(x,y,z+level,radius+.10,.20,tank,n)
    # Four narrow openings visible on the near/south shaft, not generic floors.
    for fraction in (.205,.39,.575,.76):
        m.box(x,y-shaft-.015,z+h*fraction,.52,.07,1.35,C['dark'])
        if detail:
            for side in (-1,1):
                m.box(x+side*.30,y-shaft-.06,z+h*fraction,.09,.12,1.53,C['stone'])
    # Gallery photo shows rooftop telecom rods; simplified, not a surveyed array.
    m.cylinder(x,y,z+h+.7,.18,1.4,C['metal'],12)
    for angle in (0,math.tau/3,math.tau*2/3):
        ax=x+.48*math.cos(angle); ay=y+.48*math.sin(angle)
        m.line((x,y,z+h+.35),(ax,ay,z+h+1.2),.045,C['metal'])
        m.box(ax,ay,z+h+2,.16,.20,1.3,C['white'],angle)
    # Low circular guard visible at the one-storey platform; no slab over void.
    ring=radius+.43; deck=4.4
    for i in range(n):
        a=math.tau*i/n; c=math.tau*(i+1)/n
        m.line((x+ring*math.cos(a),y+ring*math.sin(a),z+deck+.95),
               (x+ring*math.cos(c),y+ring*math.sin(c),z+deck+.95),.04,C['metal'])
        if i % (2 if detail else 1) == 0:
            m.cylinder(x+ring*math.cos(a),y+ring*math.sin(a),z+deck+.475,.035,.95,C['metal'],6)
    return m
