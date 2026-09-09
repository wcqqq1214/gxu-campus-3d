"""Library architectural study: mapped courtyard and axis, 2026 front reference.
Unseen north elevations and tier heights are estimates, not a measured survey.
"""
import math
from geometry import Mesh
from south_gate import inscription


def edge_frame(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
    return length,math.atan2(dy,dx),dx/length,dy/length


def outline_edges(part):
    for poly in part['polygons']:
        area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly[0],poly[0][1:]))
        sign=1 if area>0 else -1
        for ring in poly:
            for a,b in zip(ring,ring[1:]):
                ln,angle,dx,dy=edge_frame(a,b)
                if ln>.6:yield a,b,ln,angle,sign*dy,-sign*dx


def library(l,b,z,C,detail):
    m=Mesh();envelope=b['architecture'];stone=C['libraryStone'];trim=C['libraryTrim'];glass=C['libraryGlass'];metal=C['libraryMullion']
    body=Mesh();windows=Mesh();bands=Mesh();frames=Mesh();pergolas=Mesh();entrance=Mesh();stairs=Mesh()
    for part in envelope['parts']:
        h=part['height'];body.extrude(part['polygons'],part['triangles'],z,h,stone,C['paleRoof'])
        floors=round(h/3.6)
        for a,bb,ln,angle,nx,ny in outline_edges(part):
            dx=(bb[0]-a[0])/ln;dy=(bb[1]-a[1])/ln
            def box_at(t,out,zz,w,depth,hh,mat,target=windows):
                target.box(a[0]+dx*t+nx*out,a[1]+dy*t+ny*out,z+zz,w,depth,hh,mat,angle)
            # Geometric sill lines and a parapet follow every mapped recess / inner ring.
            box_at(ln/2,.03,h+.42,ln,.34,.84,stone,bands)
            box_at(ln/2,.04,h+.88,ln+.22,.55,.12,trim,bands)
            for f in range(floors):
                zz=.6+(f+.5)*(h-.9)/floors;fh=(h-.9)/floors
                box_at(ln/2,.10,zz,ln-.45,.12,fh*.62,glass)
                box_at(ln/2,.20,zz+fh*.36,ln,.32,.20,trim,bands)
                count=max(1,round(ln/(1.35 if detail else 4.2)))
                for j in range(count+1):
                    box_at(.25+(ln-.5)*j/count,.20,zz,.065 if detail else .10,.12,fh*.65,metal)
                if detail:
                    box_at(ln/2,.22,zz+.12,ln-.5,.13,.055,metal)
                    # Top-floor grouped square openings interrupt the continuous glazing.
                    if f==floors-1:
                        for j in range(max(1,int(ln/4.2))):box_at((j+.5)*ln/max(1,int(ln/4.2)),.30,zz,.5,.30,fh*.73,stone)
                    # Abstract meander frieze, real geometry above the alternating window bands.
                    if f%2==0 and ln>4:
                        for j in range(int(ln/2.4)):
                            t=(j+.5)*ln/int(ln/2.4);zz2=zz+fh*.5
                            for dz in [-.22,.22]:box_at(t,.24,zz2+dz,2.1,.07,.06,trim,bands)
                            for dt in [-1.02,1.02]:box_at(t+dt,.24,zz2,.06,.07,.44,trim,bands)
                            box_at(t,.24,zz2,1.25,.07,.06,trim,bands)
    # South entrance wall: central tall curtain wall with two pale rectangular motifs.
    front=-35.25
    windows.box(1.8,front-.12,z+14.7,53,.18,16.2,glass)
    for xx in range(-24,29,2):windows.box(xx,front-.24,z+14.7,.08,.14,16.2,metal)
    for zz in range(7,24):windows.box(1.8,front-.24,z+zz,53,.14,.065,metal)
    for xx in [-12.4,15.7]:
        for sx in [-1,1]:frames.box(xx+sx*9.8,front-.38,z+17.2,1.1,.35,6.0,trim)
        for zz in [14.2,17.2,20.2]:frames.box(xx,front-.38,z+zz,20.5,.35,.75,trim)
    # Open roof frames have genuine air beneath beams, including sloping cantilever edges.
    def pergola(cx,cy,width,depth,roof_z):
        for sx in [-1,1]:
            for sy in [-1,1]:
                pergolas.box(cx+sx*(width/2-2),cy+sy*(depth/2-1.8),z+roof_z+1.9,.65,.65,3.8,trim)
                if detail:pergolas.box(cx+sx*(width/2-1.3),cy+sy*(depth/2-1.8),z+roof_z+1.9,.22,.55,3.8,trim)
        for sy in [-1,1]:
            pergolas.box(cx,cy+sy*depth/2,z+roof_z+4.1,width+3,1.4,.50,trim)
            pergolas.box(cx,cy+sy*(depth/2+.45),z+roof_z+4.43,width+4,.55,.14,trim)
        for sx in [-1,1]:pergolas.box(cx+sx*width/2,cy,z+roof_z+4.1,1.4,depth,.50,trim)
        for xx in range(max(2,round(width/7))):
            px=cx-width/2+1+xx*(width-2)/(max(2,round(width/7))-1)
            pergolas.box(px,cy,z+roof_z+3.95,.35,depth,.4,trim)
    pergola(1.8,-24.5,61,11,23.5)
    for xx in [-44,44.5]:pergola(xx,-17.5,22,20,27)
    for xx in [-25.5,24.6]:pergola(xx,27,24,16,36)
    pergola(0,14.8,48,9,36)
    # Six columns stand proud of the entrance; no wall closes the colonnade.
    entrance.box(1.8,front-2.9,z+10.7,43,6.6,.85,stone)
    entrance.box(1.8,front-3.2,z+11.22,45,7.4,.25,trim)
    entrance.box(1.8,front-4.7,z+12.5,29,1.25,2.55,stone)
    entrance.box(1.8,front-4.85,z+13.9,32,2.4,.25,trim)
    for j in range(6):
        xx=1.8+(j-2.5)*7.5
        entrance.cylinder(xx,front-4.7,z+5.9,.57,8.8,trim,24 if detail else 12,topr=.49)
        for hh,rr in [(1.5,.78),(10.2,.7)]:entrance.cylinder(xx,front-4.7,z+hh,rr,.27,stone,20 if detail else 10)
    for j in range(5):
        xx=1.8+(j-2)*2.8;windows.box(xx,front-.31,z+3.2,2.6,.18,4.0,glass)
        if detail:frames.box(xx,front-.48,z+3.2,.07,.1,4.0,metal)
    for j in range(12):stairs.box(1.8,front-7.2+j*.22,z+.06*(j+1),44,5.7-j*.44,.12*(j+1),stone)
    if detail:
        for xx in [-19,1.8,22.6]:
            a=(xx,front-9.5,z+1.05);bb=(xx,front-4.5,z+2.3)
            stairs.line(a,bb,.045,metal,8)
            for t in [0,.25,.5,.75,1]:
                yy=a[1]+(bb[1]-a[1])*t;hh=1.05+1.25*t;stairs.line((xx,yy,z+hh-.85),(xx,yy,z+hh),.035,metal,6)
    for name,part in [('01_真实轮廓与内院',body),('02_分格玻璃幕墙',windows),('03_层间腰线与回纹',bands),('04_幕墙框架',frames),('05_镂空檐架',pergolas),('06_六柱入口',entrance),('07_台阶与扶手',stairs)]:m.add_part(name,part)
    m.add_part('08_立体馆名',inscription('图 书 馆',1.8,front-5.39,z+12.55,16,1.75,C['libraryInk'],False))
    # Local axes are derived from the OSM edge, never a north-aligned bounding box.
    m.rotate_z(0,0,envelope['angle']);ox,oy=envelope['origin'];m.v=[(x+ox,y+oy,zz) for x,y,zz in m.v]
    return m
