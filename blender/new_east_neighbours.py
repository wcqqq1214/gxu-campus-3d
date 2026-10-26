"""Photo-informed finishes for the buildings adjoining 新东园门.

newEastTour2025 / newEastRoute2026 show ochre render, white floor bands,
slender frames and East 25 window guards. Dimensions, window spacing and
hidden elevations remain estimates; mapped forms and floor counts stay intact.
newEastExterior2021 supplements the street-side upper window proportions only.
"""
import math
import json
from pathlib import Path
from functools import lru_cache
import bpy
import geometry
from geometry import Mesh

EAST_25 = 'way/1501460952'
WEST_SHOPS = 'way/1501460953'
SHOP_BUILDINGS = frozenset((EAST_25, WEST_SHOPS))
BUILDING_IDS = frozenset((EAST_25, 'way/1501460937', WEST_SHOPS))
SHOP_START, SHOP_BAYS, SHOP_PITCH = 1.40, 4, 3.90


@lru_cache(maxsize=1)
def paving_terrain():
    return json.loads((Path(__file__).resolve().parents[1]/'public/data/terrain.json').read_text())


def paving_height(x, y):
    t = paving_terrain()
    x0, y0, x1, y1 = t['bounds']
    cols, rows = t['cols'], t['rows']
    u = max(0, min(cols-1.001, (x-x0)/(x1-x0)*(cols-1)))
    v = max(0, min(rows-1.001, (y-y0)/(y1-y0)*(rows-1)))
    i, j = int(u), int(v)
    a, b, h = u-i, v-j, t['heights']
    return ((h[j*cols+i]*(1-a)+h[j*cols+i+1]*a)*(1-b)
            +(h[(j+1)*cols+i]*(1-a)+h[(j+1)*cols+i+1]*a)*b)+.035


def ensure_materials(C, *, refresh=False):
    palette = [
        ('eastNeighbourOchre', (.63, .52, .34), .92, 0),
        ('eastNeighbourCream', (.69, .67, .57), .92, 0),
        ('eastNeighbourWhite', (.80, .81, .76), .80, 0),
        ('eastNeighbourSpandrel', (.73, .68, .53), .92, 0),
        ('eastNeighbourGlass', (.095, .145, .155), .36, .12),
        ('eastNeighbourShade', (.052, .078, .080), .42, .10),
        ('eastShopRed', (.42, .025, .020), .82, 0),
        ('eastShopNeutral', (.24, .27, .26), .82, 0),
        ('eastShopFrame', (.075, .085, .080), .46, .25),
        ('eastShopPaving', (.40, .41, .38), .96, 0),
        ('eastShopPavingJoint', (.26, .28, .26), .98, 0),
        ('eastShopDisplayGlass', (.17, .22, .20), .30, .15),
        ('eastShopReflectGlass', (.23, .29, .28), .32, .12),
        ('eastShopMetal', (.36, .38, .36), .68, .22),
    ]
    for name, color, roughness, metallic in palette:
        if name not in C:
            existing = bpy.data.materials.get(name)
            if existing:
                C[name] = len(geometry.MATERIALS)
                geometry.MATERIALS.append(existing)
            else:
                C[name] = geometry.material(name, color, roughness, metallic)
        if refresh:
            mat = geometry.MATERIALS[C[name]]
            mat.diffuse_color = (*color, 1)
            bs = mat.node_tree.nodes['Principled BSDF']
            bs.inputs['Base Color'].default_value = (*color, 1)
            bs.inputs['Roughness'].default_value = roughness
            bs.inputs['Metallic'].default_value = metallic


def wall_finish(b, C):
    ensure_materials(C)
    return C['eastNeighbourOchre' if b['id'] == EAST_25 else 'eastNeighbourCream']


def shop_layout(b, facade):
    """Only street-facing frontage; the East 25 location is user-confirmed.

    East-side bay count, neutral sign panels and opening sizes are estimates,
    not a recovered tenant layout. Keep clear of the gate-facing corner.
    """
    length = math.dist(facade['start'], facade['end'])
    if b['id'] not in SHOP_BUILDINGS or facade['normal'][1] >= -.99 or length <= 60:
        return None
    if b['id'] == WEST_SHOPS:
        return SHOP_START, SHOP_BAYS, SHOP_PITCH
    return length-1.8-5*3.9, 5, 3.9


def facade_details(b, z, C, detail, facades):
    m = Mesh()
    trim = C['eastNeighbourWhite']
    east = b['id'] == EAST_25
    for facade_index, facade in enumerate(facades):
        a, c = facade['start'], facade['end']
        length = math.dist(a, c)
        if length < .5:
            continue
        tx, ty = (c[0]-a[0])/length, (c[1]-a[1])/length
        nx, ny = facade['normal']
        angle = math.atan2(ty, tx)
        h, levels = facade['height'], max(1, round(facade['levels']))
        floor = h/levels

        def box(u, height, width, depth, tall, material, offset):
            m.box(a[0]+tx*u+nx*offset, a[1]+ty*u+ny*offset,
                  z+height, width, depth, tall, material, angle)

        # The same bands, corner strips and sills survive the near/base swap.
        for level in range(1, levels):
            box(length/2, level*floor, length, .06, .22, trim, .045)
        for u in (.12, length-.12):
            box(u, h/2, .24, .055, h, trim, .035)
        if length < 2:
            continue
        count = max(1, int(length/4))
        width = min(2.1, length/count*.60)
        shops = shop_layout(b, facade)
        street_side = b['id'] == WEST_SHOPS and shops is not None
        for level in range(levels):
            # The historical street view shows taller upper-storey openings
            # and pale warm panels below them; unseen elevations stay unchanged.
            street_upper = street_side and level > 0
            tall = min(2.1, floor*.64) if street_upper else min(1.65, floor*.50)
            center_z = (level+.56)*floor
            for column in range(count):
                u = (column+.5)*length/count
                if level == 0 and shops:
                    shop_start, bays, pitch = shops
                    if u+width/2 > shop_start and u-width/2 < shop_start+bays*pitch:
                        continue
                x, y = a[0]+tx*u, a[1]+ty*u
                # Keep even estimated existing entrances unobstructed.
                if level == 0 and any(
                    abs((x-e['center'][0])*nx+(y-e['center'][1])*ny) < .25
                    and abs((x-e['center'][0])*tx+(y-e['center'][1])*ty) < (width+e['width'])/2+.10
                    for e in b['form']['entrances']
                ):
                    continue
                if street_upper:
                    box(u, level*floor+.40, width+.14, .018, .54,
                        C['eastNeighbourSpandrel'], .012)
                glass = C['eastNeighbourShade' if (column+level*3+facade_index)%7 < 2 else 'eastNeighbourGlass']
                box(u, center_z, width+.14, .04, tall+.14, C['eastNeighbourShade'], .025)
                box(u, center_z, width, .012, tall, glass, .065)
                for side in (-1, 1):
                    box(u+side*(width+.065)/2, center_z, .065, .06, tall+.13, trim, .095)
                    box(u, center_z+side*(tall+.065)/2, width, .06, .065, trim, .095)
                # A closed sloped sill meets the bottom frame and sheds outwards.
                # Keep its maximum projection at the existing 15 cm clearance.
                sill_top = center_z-tall/2-.065
                def sill_point(along, offset, height):
                    return (a[0]+tx*along+nx*offset, a[1]+ty*along+ny*offset, z+height)
                top_points = [sill_point(u+side*(width+.24)/2, offset, sill_top-drop)
                              for side, offset, drop in ((-1,0,0),(1,0,0),(1,.15,.03),(-1,.15,.03))]
                vertices = top_points+[(x,y,h-.045) for x,y,h in top_points]
                for face in ((0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)):
                    m.face([vertices[i] for i in face], trim)
                # The normal viewing distance must retain the window identity.
                # Stop mullions at the transom instead of overlapping coplanar faces.
                cross_z, bar = center_z+tall*.23, .035
                for division in (-1, 1):
                    for lo, hi in ((center_z-tall/2, cross_z-bar/2),
                                   (cross_z+bar/2, center_z+tall/2)):
                        box(u+division*width/6, (lo+hi)/2, bar, .04, hi-lo, trim, .095)
                box(u, cross_z, width, .04, bar, trim, .095)
                if not detail:
                    continue
                # Small guards are confined to East 25's lower visible floors.
                if east and level < 3:
                    for bar in range(1, 10):
                        box(u-width/2+width*bar/10, center_z, .016, .012, tall, trim, .145)
                    for row in (-.32, .32):
                        box(u, center_z+tall*row, width, .012, .018, trim, .145)
        # The pipe is on the gate-facing west wall, inside the existing clearance.
        if east and nx < -.99 and length > 10:
            u = length-.42
            m.cylinder(a[0]+tx*u+nx*.115, a[1]+ty*u+ny*.115,
                       z+h/2, .03, h, trim, n=8)
    return m


def shopfront_details(b, z, C, detail, facades):
    """Bounded street frontage: west photo-informed, east user-located.

    Bays are modeling divisions, not confirmed tenants. East 25 uses neutral
    blank sign panels because its current shop finishes are not verified.
    """
    m = Mesh()
    for facade in facades:
        layout = shop_layout(b, facade)
        if layout is None:
            continue
        start, bays, pitch = layout
        end = start+bays*pitch
        east = b['id'] == EAST_25
        a, c = facade['start'], facade['end']
        length = math.dist(a, c)
        tx, ty = (c[0]-a[0])/length, (c[1]-a[1])/length
        nx, ny = facade['normal']
        angle = math.atan2(ty, tx)

        def box(u, height, width, depth, tall, material, offset):
            m.box(a[0]+tx*u+nx*offset, a[1]+ty*u+ny*offset,
                  z+height, width, depth, tall, C[material], angle)

        middle, span = (start+end)/2, end-start
        # A modest paved apron follows the existing terrain. It stops before
        # the mapped street and before the adjoining building's shared corner.
        u_cuts = {start-.15+(span+.30)*cell/16 for cell in range(17)}
        joints = [start+i*pitch for i in range(1,bays)] if east else []
        for joint in joints:
            u_cuts.update((joint-.006,joint+.006))
        u_cuts = sorted(u_cuts)
        offsets = [0,1,1.494,1.506,2,3] if east else [0,1,2,3]
        for u0,u1 in zip(u_cuts,u_cuts[1:]):
            for v0,v1 in zip(offsets,offsets[1:]):
                points = []
                for u, offset in ((u0,v0),(u1,v0),(u1,v1),(u0,v1)):
                    x, y = a[0]+tx*u+nx*offset, a[1]+ty*u+ny*offset
                    points.append((x, y, paving_height(x, y)))
                if tx*ny-ty*nx < 0:
                    points.reverse()
                # Partition the paving itself: no floating or coplanar overlay lines.
                in_joint = east and (1.494 < (v0+v1)/2 < 1.506 or
                                     any(abs((u0+u1)/2-joint) < .006 for joint in joints))
                m.face(points, C['eastShopPavingJoint' if in_joint else 'eastShopPaving'])
        if east:
            for bay in range(bays):
                box(start+(bay+.5)*pitch, 2.91, pitch-.16, .12, .68, 'eastShopNeutral', .08)
            box(middle, 3.29, span+.08, .18, .06, 'eastNeighbourWhite', .10)
        else:
            box(middle, 3.01, span, .16, .85, 'eastShopRed', .10)
            box(middle, 3.465, span+.08, .20, .06, 'eastNeighbourWhite', .10)
        def point(u, offset, height):
            return (a[0]+tx*u+nx*offset, a[1]+ty*u+ny*offset, z+height)

        # A shallow straight eave. The west follows the broad filmed treatment;
        # the east is a restrained architectural estimate, not a verified canopy.
        projection, edge_top = (.48, 2.62) if east else (.72, 2.57)
        top_points = [point(start,.18,2.67), point(end,.18,2.67),
                      point(end,projection,edge_top), point(start,projection,edge_top)]
        vertices = top_points+[(x,y,h-.035) for x,y,h in top_points]
        for face in ((0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)):
            m.face([vertices[i] for i in face], C['eastNeighbourWhite'])
        box(middle, edge_top-.07, span, .03, .07, 'eastShopMetal', projection-.015)

        for bay in range(bays):
            u = start+(bay+.5)*pitch
            width, bottom, top = pitch-.32, .18, 2.52
            center, tall = (bottom+top)/2, top-bottom
            # A wide display window and a narrower recessed door read as a
            # shop even at the gate overview scale, without painted lettering.
            door_width = .94
            split = u+width/2-door_width
            display_width = width-door_width-.075
            display_u = u-width/2+display_width/2
            door_u = u+width/2-door_width/2
            # Differently toned panes and thin transoms replace one opaque-looking
            # sheet. Keep these readable divisions in both shipping LODs.
            pane_width = (display_width-.035)/2
            for side in (-1, 1):
                pane_u = display_u+side*(pane_width+.035)/2
                box(pane_u, 1.23, pane_width, .018, 1.86,
                    'eastShopReflectGlass' if side == -1 else 'eastShopDisplayGlass', .20)
                box(pane_u, 2.36, pane_width, .018, .32, 'eastShopReflectGlass', .20)
            box(display_u, 1.23, .035, .035, 1.86, 'eastShopMetal', .23)
            box(display_u, 2.36, .035, .035, .32, 'eastShopMetal', .23)
            box(display_u, 2.18, display_width, .035, .04, 'eastShopMetal', .23)
            box(door_u, center, door_width, .018, tall,
                'eastNeighbourGlass' if east else 'eastNeighbourShade', .065)
            leaf_width = door_width-.06 if east else door_width
            box(door_u, .28, leaf_width, .035, .20, 'eastShopMetal', .09)
            if east:
                # Thin leaf stiles sit behind the deeper opening frame. Rails butt
                # into the stiles instead of layering bright faces at the corners.
                for side in (-1,1):
                    box(door_u+side*(door_width-.03)/2, center, .03, .04, tall,
                        'eastShopMetal', .09)
                for height in (bottom+.015,top-.015):
                    box(door_u, height, leaf_width, .04, .03, 'eastShopMetal', .09)
            for side in (-1, 1):
                box(u+side*(width+.06)/2, center, .06, .23, tall+.12, 'eastShopFrame', .13)
                box(u, center+side*(tall+.06)/2, width, .23, .06, 'eastShopFrame', .13)
            box(split-.0375, center, .075, .23, tall, 'eastShopFrame', .13)
            box(door_u, 2.18, door_width, .055, .05, 'eastShopFrame', .105)
            box(display_u, .24, display_width, .08, .12, 'eastShopMetal', .20)
            # Both steps extend down to the existing foundation: no thin slabs
            # suspended above the sloping street-side terrain.
            if east:
                # Seat the sill below the opening frame, without coincident top faces.
                # The shallow threshold has a closed 20 mm bevel at its outer lip.
                profile = [(0,-.50),(.32,-.50),(.32,.10),(.30,.12),(0,.12)]
                ends = [[point(u+side*(width+.20)/2,offset,height)
                         for offset,height in profile] for side in (-1,1)]
                for i in range(len(profile)):
                    j = (i+1)%len(profile)
                    m.face([ends[0][i],ends[0][j],ends[1][j],ends[1][i]], C['eastNeighbourWhite'])
                m.face(ends[0][::-1], C['eastNeighbourWhite'])
                m.face(ends[1], C['eastNeighbourWhite'])
            else:
                box(u, -.16, width+.20, .32, .68, 'eastNeighbourWhite', .16)
            if not east:
                box(u, -.27, width+.20, .30, .46, 'eastNeighbourWhite', .47)
            handle_u = split+.15
            box(handle_u, 1.20, .035, .035, .40, 'eastNeighbourWhite', .18)
            for height in (1.03, 1.37):
                box(handle_u, height, .035, .10, .025, 'eastNeighbourWhite', .13)
            if detail:
                for side in (-1, 1):
                    bracket_u = u+side*(width/2-.12)
                    m.line(point(bracket_u,.18,2.22), point(bracket_u,projection-.06,edge_top-.03), .012, C['eastShopFrame'])
        for divider in range(bays+1):
            u = start+divider*pitch
            box(u, 1.36, .20, .12, 2.52, 'eastNeighbourWhite' if east else 'eastShopRed', .065)
    return m
