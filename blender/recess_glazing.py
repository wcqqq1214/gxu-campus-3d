"""Three glazed banks behind an open portico, shared by both detail levels."""
import math


def add_recess_glazing(mesh,entry,z,C):
    p=entry['recessGlazing'];x,y=entry['center'];angle=math.radians(entry['bearing'])
    nx,ny=math.sin(angle),math.cos(angle);theta=-angle
    floor=entry['platformHeight'];height=p['glazingHeight'];fw=p['frameWidth']
    central=entry['width'];side=(p['width']-central-2*p['bayGap'])/2
    side_center=central/2+p['bayGap']+side/2
    def box(u,depth,bottom,w,d,h,material):
        mesh.box(x+ny*u+nx*depth,y-nx*u+ny*depth,z+floor+bottom+h/2,w,d,h,C[material],theta)
    for center,width,columns in [(-side_center,side,p['sideColumns']),(0,central,1),(side_center,side,p['sideColumns'])]:
        box(center,.055,0,width,.05,height,'glass')
        for offset in (-width/2+fw/2,width/2-fw/2):
            box(center+offset,.12,0,fw,.08,height,'white')
        for bottom in (0,height-fw,p['transomHeight']-fw/2):
            box(center,.12,bottom,width,.08,fw,'white')
        for i in range(1,columns):
            u=center-width/2+fw+(width-2*fw)*i/columns
            box(u,.12,fw,fw,.08,height-2*fw,'white')
    # The central doorway is distinct from its surrounding fixed glazing.
    for u in (-p['doorWidth']/2,0,p['doorWidth']/2):
        box(u,.12,fw,fw,.08,p['doorHeight']-fw,'white')
    box(0,.12,p['doorHeight']-fw/2,p['doorWidth']+fw,.08,fw,'white')
