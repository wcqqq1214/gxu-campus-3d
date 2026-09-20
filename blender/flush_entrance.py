"""Shared low/near glazed portal and an optional photo-attributed head canopy."""
import math


def add_flush_entrance(mesh, entry, z, C):
    p=entry['flushEntrance'];x,y=entry['center'];angle=math.radians(entry['bearing'])
    nx,ny=math.sin(angle),math.cos(angle);theta=-angle
    width=entry['width'];bay=width/p['bays'];floor=p['floorHeight'];top=p['glazingHeight']
    pw,pd,fw=p['pierWidth'],p['pierDepth'],p['frameWidth']
    def box(u,depth,bottom,w,d,h,material):
        mesh.box(x+ny*u+nx*depth,y-nx*u+ny*depth,z+bottom+h/2,w,d,h,C[material],theta)
    for i in range(p['bays']):
        u=-width/2+(i+.5)*bay
        box(u,.055,floor,bay-pw,.05,top-floor,'glass')
        box(u,.095,p['splitHeight']-fw/2,bay-pw,.09,fw,'white')
        if i!=p['bays']//2:
            box(u,.095,floor,fw,.09,top-floor,'white')
    for i in range(p['bays']+1):
        # Outer piers stay inside the configured entrance width.
        u=-width/2+pw/2 if i==0 else width/2-pw/2 if i==p['bays'] else -width/2+i*bay
        box(u,pd/2-.03,floor,pw,pd,top-floor,'stone')
    box(0,.095,top-fw,width,.09,fw,'white')
    dh,dw=p['doorHeight'],p['doorWidth']
    for u in (-dw/2,dw/2,0):box(u,.13,floor,fw,.10,dh,'white')
    box(0,.13,floor+dh-fw/2,dw+fw,.10,fw,'white')
    if 'canopy' in p:
        canopy=p['canopy']
        box(0,canopy['depth']/2,top,canopy['width'],canopy['depth'],canopy['thickness'],'stone')


def flush_entrance_blocks_window(entry,x,y,nx,ny,bottom,top,width):
    if 'flushEntrance' not in entry:return False
    p=entry['flushEntrance'];a=math.radians(entry['bearing']);ex,ey=entry['center']
    en=(math.sin(a),math.cos(a));dx,dy=x-ex,y-ey
    return (nx*en[0]+ny*en[1]>.999 and abs(dx*en[0]+dy*en[1])<.3
            and abs(dx*en[1]-dy*en[0])<(entry['width']+width+.3)/2
            and bottom<p['glazingHeight'] and top>p['floorHeight'])
