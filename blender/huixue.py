"""Huixue Hall from GXU's official film, built photos and the SCAD project drawings.

Dimensions are a proportional reconstruction within the mapped footprint, not a survey.
The unobserved rear remains approximate. Local front is -Y, rotated onto east.
"""
import math
from geometry import Mesh, material
from south_gate import inscription


def huixue(l, b, z, C, detail=True):
    # A local finish keeps the gray metal roof seen in the official daylight
    # film separate from the shared green slate used by other campus roofs.
    if 'huixueRoof' not in C:
        rgb=[int('75868c'[i:i+2],16)/255 for i in (0,2,4)]
        C['huixueRoof']=material('huixueRoof',
            [((c+.055)/1.055)**2.4 if c>.04045 else c/12.92 for c in rgb],.72,.18)
    m = Mesh()
    xmin, ymin, xmax, ymax = l['bounds']
    cx, cy = (xmin+xmax)/2, (ymin+ymax)/2
    w, d = ymax-ymin, xmax-xmin
    front = -d*.46
    back = d*.44
    half = w*.47
    wall, trim, glass = C['stone'], C['white'], C['glass']
    dark, roof, wood = C['dark'], C['huixueRoof'], C['wood']

    def box(x, y, zz, width, depth, height, mat):
        m.box(cx+x, cy+y, z+zz, width, depth, height, mat)

    def face(points,mat):
        m.face([(cx+xx,cy+yy,z+zz) for xx,yy,zz in points],mat)

    def column(x, y, base, pitch, angle=0):
        """Six-sided stone pier with a splayed head; angle turns its outward face."""
        c,s=math.cos(angle),math.sin(angle)
        # Two chamfered outer corners create the faceted light/shadow pattern
        # visible in the architect's built column close-up.
        def ring(width,depth,height):
            profile=[(-width/2,-depth*.25),(-width*.23,-depth/2),
                     (width*.23,-depth/2),(width/2,-depth*.25),
                     (width/2,depth/2),(-width/2,depth/2)]
            return [(x+u*c-v*s,y+u*s+v*c,height) for u,v in profile]
        rings=[ring(1.45,2.0,base),ring(1.45,2.0,17.4),
               ring(min(pitch-.25,2.9),2.45,18.3)]
        face(rings[0][::-1],trim)
        for lower,upper in zip(rings,rings[1:]):
            for i in range(6):
                j=(i+1)%6
                face([lower[i],lower[j],upper[j],upper[i]],trim)
        face(rings[-1],trim)

    # A raised podium carries open perimeter galleries. The 2021 official
    # aerial shows open light wells behind both front colonnades.
    podium = 3.0
    gallery = 4.0
    opening = w*.215
    portal = w*.395
    recess = 4.2
    hall_front = front+15
    # Built long-side photos show the high platform ending before the rear.
    # Keep the central plinth, but expose the low rear gallery and its stair.
    platform_end=front+(back-front)*.64
    box(0,(front+back)/2,1.5,2*half-2*gallery,back-front,3,dark)
    box(0,(front+platform_end)/2,1.5,2*half,platform_end-front,3,dark)
    box(0,(front+platform_end)/2,3.04,2*half+.2,platform_end-front,.08,trim)
    for side in [-1,1]:
        box(side*(half+1.25),(front+platform_end)/2,1.5,
            4.5,platform_end-front,3,dark)
        box(side*(half+1.25),(front+platform_end)/2,3.04,
            4.5,platform_end-front,.08,trim)
        box(side*(half-gallery/2),(platform_end+back)/2,.10,
            gallery,back-platform_end,.20,C['path'])
        box(side*(half+1.25),(platform_end+back)/2,.10,
            4.5,back-platform_end,.20,C['path'])
    box(0,(hall_front+back)/2,12.1,2*half-2*gallery,
        back-hall_front,18.2,wall)
    # Lobby core is narrower than the flanking courts; do not fill the wells.
    box(0,(front+recess+hall_front)/2,10.8,portal-1,
        hall_front-front-recess,15.6,trim)
    # Perimeter roof beams close onto corner piers while galleries stay open.
    box(0,front+1,18.7,2*half,2,2.0,trim)
    for side in [-1,1]:
        box(side*(half-1), (front+back)/2,18.7,2,back-front,2,trim)
        box(side*(half-gallery/2), (front+back)/2,18.0,gallery,back-front,.25,trim)
    box(0,back-1,18.7,2*half,2,2,trim)

    # Broad shallow auditorium roof with a rear raised stage volume.
    # The 00:08.5 official aerial constrains its extent, slope and front setback.
    roof_half=w*.445; rf=hall_front-3; rb=back+1
    top_half=w*.24; tf=back-27; tb=back-7
    lower=[(-roof_half,rf,22.0),(roof_half,rf,22.0),
           (roof_half,rb,22.0),(-roof_half,rb,22.0)]
    upper=[(-top_half,tf,25),(top_half,tf,25),
           (top_half,tb,25),(-top_half,tb,25)]
    for i in range(4):
        j=(i+1)%4;face([lower[i],lower[j],upper[j],upper[i]],roof)
    face(upper,roof)
    box(0,(tf+tb)/2,25.7,2*top_half,tb-tf,1.4,dark)
    box(0,(tf+tb)/2,26.45,2*top_half+.3,tb-tf+.3,.15,wall)
    for side in [-1,1]:
        box(side*(roof_half-1.5),(rf+rb)/2,21.25,1.2,rb-rf,1.5,dark)
    box(0,rf+.4,21.45,2*roof_half,.8,1.1,dark)
    # Omit subpixel seam rods on the main roof: their self-shadows produced
    # severe moire at ordinary map zoom. Retain its observed eave supports.
    for side in [-1,1]:
        for i in range(17):
            yy=rf+(rb-rf)*i/16
            aa=(cx+side*(half-gallery),cy+yy,z+20.8)
            bb=(cx+side*roof_half,cy+yy,z+21.85)
            m.line(aa,bb,.07,dark,4)

    # The 2020 engineering-consultant front photo resolves the steep upper
    # entry pitch rising above the main front eave. This is a proportional
    # reconstruction, not acceptance of either disputed total-height figure.
    # Two roof pitches above the entry, not a single pyramid.
    ef=front-1.4; mid=front+6; rear=rf+1
    a=portal/2+1.5; narrow=portal*.335
    face([(-a,ef,18.2),(a,ef,18.2),(narrow,mid,20.0),(-narrow,mid,20.0)],roof)
    face([(-narrow,mid,20.0),(narrow,mid,20.0),(narrow,rear,24.2),(-narrow,rear,24.2)],roof)
    # Close the raised entry roof onto the main eave; the hidden junction is
    # a simplified enclosure, not a claimed reconstruction of its framing.
    face([(-narrow,rear,24.2),(narrow,rear,24.2),
          (narrow,rear,22.0),(-narrow,rear,22.0)],roof)
    for side in [-1,1]:
        points=[(side*a,ef,18.2),(side*narrow,mid,20.0),
                (side*narrow,rear,24.2),(side*a,rear,18.2)]
        # This return is not planar. Explicit triangles avoid exporter-dependent
        # tessellation, and both sides must face outward.
        for triangle in [[points[0],points[1],points[2]],
                         [points[0],points[2],points[3]]]:
            face(triangle[::-1] if side<0 else triangle,roof)
    box(0,ef,18.0,2*a,.45,.42,C['red'])
    pier = (portal-opening)/2
    for side in [-1, 1]:
        box(side*(opening/2+pier/2), front+recess/2,10.5,pier,recess,15.0,trim)
        # Warm taller walls sit behind the narrow vertical louver panels.
        lx=side*(portal/2+1.6)
        box(lx,front+2.5,12.1,3.2,5,18.2,wall)
        box(lx,front-.05,10.8,2.9,.16,15.6,dark)
        count=62 if detail else 31
        for i in range(count):
            box(lx,front-.18,3.15+i*15.3/count,2.9,.35,.10 if detail else .16,trim)
    box(0,front+recess/2,16.55,opening,recess,2.5,dark)
    box(0,front-.40,16.5,opening+1.2,.45,2.6,wood)
    if detail:
        for i in range(91):box(-opening/2+i*opening/90,front-.64,16.5,.025,.035,2.5,dark)
    for dx,glyph in [(-4.3,'堂'),(0,'学'),(4.3,'汇')]:
        m.extend(inscription(glyph,cx+dx,cy+front-.7,z+16.55,1.65,1.65,trim,detail))
    # Seven door bays visible in the official 00:12 close-up; upper panels follow the
    # visible wood grille rather than a solid brown rectangle.
    door_y = front+recess-.12
    box(0, door_y, 9.3, opening, .16, 12.6, wood)
    bays = 7
    bw = opening/bays
    for i in range(bays):
        xx = (i-(bays-1)/2)*bw
        for side in [-1, 1]:
            dx = xx+side*bw*.23
            box(dx, door_y-.11, 5.25, bw*.40, .08, 4.3, dark)
            box(dx, door_y-.18, 5.25, .10, .08, 4.4, C['metal'])
        box(xx, door_y-.1, 11.8, bw-.28, .08, 7.4, glass)
        if detail:
            for k in range(7):
                box(xx-bw*.43+k*bw*.143, door_y-.20, 11.8, .07, .10, 7.4, wood)
            for k in range(12):
                box(xx, door_y-.21, 8.1+k*.66, bw-.25, .10, .07, wood)
            for k in range(3):
                for row in range(7):
                    gx=xx+(k-1)*bw*.285; gz=8.45+row*.95
                    box(gx,door_y-.22,gz,.55,.08,.065,wood)
                    box(gx+.24,door_y-.22,gz+.22,.065,.08,.5,wood)
        box(xx-bw/2,door_y-.22,9.3,.18,.22,12.6,wood)
    # Five open column bays per front wing, with splayed heads. Their dark
    # gaps are gallery voids, not giant panes of glass (2023 FPV at 00:15).
    inner=portal/2+3.4
    wing=half-1-inner
    pitch=wing/5
    for side in [-1,1]:
        for i in range(6):
            xx=side*(inner+i*pitch)
            column(xx,front+1,podium,pitch)
        # Back wall of each court remains set back, visibly behind the columns.
        box(side*(inner+wing/2),hall_front,10.4,wing,1,14.8,trim)
        for i in range(5):
            xx=side*(inner+(i+.5)*pitch)
            box(xx,hall_front-.53,9.3,1.6,.08,10.4,glass)
            for zz in [6.3,10.2,13.8]:
                box(xx,hall_front-.59,zz,1.6,.06,.12,dark)
    # Long side columns and windows are not one repeated glass curtain wall.
    # SCAD's built side photograph resolves 26 bays; the 2022 walk shows solid
    # walls with separate floor windows in the rear portion.
    side_pitch=(back-front-2)/26
    for side in [-1,1]:
        for i in range(1,27):  # the front corner is already in the front colonnade
            yy=front+1+i*side_pitch
            base=podium if yy<platform_end else .2
            column(side*(half-1),yy,base,side_pitch,side*math.pi/2)
        for i in range(26):
            yy=front+1+(i+.5)*side_pitch
            if yy<hall_front+1:
                continue  # open front light well, not a glazed exterior wall
            xx=side*(half-gallery+.04)
            if yy<front+(back-front)*.57:
                # Built photos show substantial stone spandrels between floors,
                # not a twelve-metre glass strip with thin applied crossbars.
                for zz in [5.1,9.3,13.5]:
                    box(xx,yy,zz,.08,2.35,2.9,glass)
                    box(xx+side*.06,yy,zz,.08,2.35,.10,dark)
            else:
                for zz in [5.1,9.3,13.5]:
                    box(xx,yy,zz,.08,1.05,2.55,glass)
                    box(xx+side*.06,yy,zz,.08,1.05,.10,dark)
        # The front side plinth has narrow ground-level openings, separated
        # by stone mullions. Rear ground-level doors remain unplaced until
        # their position is confirmed; do not mirror the unlocated canopy.
        n=46
        for i in range(n):
            yy=front+3+(platform_end-front-6)*(i+.5)/n
            box(side*(half+3.55),yy,1.50,.10,.48,1.55,glass)
        rail_x=side*(half+3.25)
        for zz in [3.65,4.1]:
            box(rail_x,(front+platform_end)/2,zz,.06,platform_end-front,.06,C['metal'])
        for i in range(18):
            yy=front+i*(platform_end-front)/17
            box(rail_x,yy,3.57,.07,.07,1.14,C['metal'])
        # Rear-to-front flight onto the side platform, seen in the long-side
        # aerial and at 01:05 in BV1Y841147kG. Solid risers reach the floor.
        stair_center=side*(half+1.8)
        for i in range(18):
            length=9*(18-i)/18
            box(stair_center,platform_end+length/2,(i+1)*3/18/2,
                3.2,length,(i+1)*3/18,wall)
        for offset in [-1.5,1.5]:
            for i in range(7):
                yy=platform_end+i*9/6;level=3*(1-i/6)
                box(stair_center+offset,yy,level+.55,.08,.08,1.1,C['metal'])
            m.line((cx+stair_center+offset,cy+platform_end,z+4.1),
                   (cx+stair_center+offset,cy+platform_end+9,z+1.1),.055,C['metal'],4)
    # Broad stepped entrance and solid side retaining cheeks, not floating treads.
    n=20; stair_w=portal+3; depth=12; rise=podium
    landing=2.0; tread=(depth-landing)/n
    for i in range(n):
        start=front-depth+i*tread+(landing if i>=n//2 else 0)
        length=front-start
        box(0,(start+front)/2,(i+1)*rise/n/2,
            stair_w,length,(i+1)*rise/n,wall)
    for side in [-1,1]:
        box(side*(stair_w/2+.8),front-4,1.5,1.6,8,3,trim)
    # Forecourt and raised side gardens, bounded to the landmark approach.
    box(0,front-depth-1,-.04,2*half+1,4,.22,C['path'])
    for side in [-1,1]:
        box(side*(stair_w/2+2),front-4,1.6,2.3,7.8,3.2,wall)
        box(side*(stair_w/2+2),front-4,3.22,1.7,7.1,.08,C['green'])
    m.rotate_z(cx,cy,math.pi/2)
    return m
