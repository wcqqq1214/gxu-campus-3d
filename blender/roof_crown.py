"""Raised curtain mass and tapered white roof screen, identical in both LODs."""
from facade_panels import add_panels


def side_wall_blocks_window(c, x, y, nx, ny, width, bottom, top):
    """Suppress complete default windows intersecting the tapered white wall."""
    if 'sideWall' not in c:
        return False
    a,v=c['corner'],c['v'];en=(v[1],-v[0])
    # Orient outward on either winding of the mapped corner.
    if en[0]*c['u'][0]+en[1]*c['u'][1]>0:
        en=(-en[0],-en[1])
    dx,dy=x-a[0],y-a[1]
    if nx*en[0]+ny*en[1]<.999 or abs(dx*en[0]+dy*en[1])>.3:
        return False
    low=max(bottom,c['sideWall']['baseHeight']);high=c['baseHeight']+c['screenRise']
    if low>=min(top,high):
        return False
    rear=c['screenTopDepth']+(high-low)*(c['screenBottomDepth']-c['screenTopDepth'])/c['screenRise']
    center=dx*v[0]+dy*v[1]
    return center+width/2>c['depth'] and center-width/2<rear


def add_roof_crown(mesh, c, z, C):
    a,u,v = c['corner'],c['u'],c['v']
    def at(s,t,h):
        return (a[0]+u[0]*s+v[0]*t, a[1]+u[1]*s+v[1]*t, z+h)
    def prism(profile, start, end, material):
        # Profile uses (depth, height), CCW seen along +u; orient with the local basis.
        front=[at(start,t,h) for t,h in profile];back=[at(end,t,h) for t,h in profile]
        if u[0]*v[1]-u[1]*v[0] < 0:
            front.reverse();back.reverse()
        mesh.face(front[::-1],material);mesh.face(back,material)
        for i in range(len(front)):
            j=(i+1)%len(front)
            mesh.face([front[i],front[j],back[j],back[i]],material)
    base=c['baseHeight'];top=base+c['rise']
    prism([(0,base),(c['depth'],base),(c['depth'],top),(0,top)],0,c['width'],C['stone'])
    sw=c.get('sideWall',{})
    screen_base=sw.get('baseHeight',base);screen_depth=sw.get('bottomDepth',c['screenBottomDepth'])
    projection=sw.get('projection',0)
    prism([(c['depth'],screen_base),(screen_depth,screen_base),
           (c['screenTopDepth'],base+c['screenRise']),(c['depth'],base+c['screenRise'])],
          -projection,c['screenThickness']-projection,C['white'])
    for direction,normal,length,end,columns in [
            (u,[-v[0],-v[1]],c['width'],c['frontEnd'],c['columns']),
            (v,[-u[0],-u[1]],c['depth'],c['sideEnd'],c['sideColumns'])]:
        facade=dict(start=a,end=[a[k]+direction[k]*length for k in (0,1)],normal=normal,
            rule=dict(panels=[dict(type='glazing', **{'from':.1/length,'to':end/length},
                bottom=c['glassBottom'],top=c['glassTop'],columns=columns,rows=c['rows'],frameWidth=.07,depth=.1)]))
        add_panels(mesh,facade,z,C)
