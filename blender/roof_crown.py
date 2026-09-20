"""Raised curtain mass and tapered white roof screen, identical in both LODs."""
from facade_panels import add_panels


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
    prism([(c['depth'],base),(c['screenBottomDepth'],base),
           (c['screenTopDepth'],base+c['screenRise']),(c['depth'],base+c['screenRise'])],
          0,c['screenThickness'],C['white'])
    for direction,normal,length,end,columns in [
            (u,[-v[0],-v[1]],c['width'],c['frontEnd'],c['columns']),
            (v,[-u[0],-u[1]],c['depth'],c['sideEnd'],c['sideColumns'])]:
        facade=dict(start=a,end=[a[k]+direction[k]*length for k in (0,1)],normal=normal,
            rule=dict(panels=[dict(type='glazing', **{'from':.1/length,'to':end/length},
                bottom=c['glassBottom'],top=c['glassTop'],columns=columns,rows=c['rows'],frameWidth=.07,depth=.1)]))
        add_panels(mesh,facade,z,C)
