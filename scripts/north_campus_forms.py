"""Photo-constrained envelopes, with explicit estimated dimensions.

All cuts are made in the traced footprint; no generated solid seals a passage.
Blender consumes the packed geometry without requiring Shapely at runtime.
"""
import math
from shapely.geometry import Polygon, box
from shapely.ops import transform
from shapely.geometry.polygon import orient
from building_overrides import pack_geometry


def prepare_form(record, parameters):
    polygon=Polygon(record['polygons'][0][0],record['polygons'][0][1:])
    ring=list(polygon.exterior.coords)
    direction=parameters.get('front','south')
    edges=[(a,b) for a,b in zip(ring,ring[1:]) if math.dist(a,b)>10]
    def score(edge):
        a,b=edge;dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        normal=(dy/length,-dx/length)
        axis={'south':(0,-1),'west':(-1,0),'east':(1,0)}[direction]
        return normal[0]*axis[0]+normal[1]*axis[1]
    a,b=max(edges,key=score);length=math.dist(a,b)
    ux,uy=(b[0]-a[0])/length,(b[1]-a[1])/length
    cx,cy=polygon.centroid.coords[0]
    def local(x,y,z=None):return (x-cx)*ux+(y-cy)*uy,-(x-cx)*uy+(y-cy)*ux
    def world(u,v,z=None):return cx+u*ux-v*uy,cy+u*uy+v*ux
    local_polygon=transform(local,polygon)
    u0,v0,u1,v1=local_polygon.bounds
    w,d=u1-u0,v1-v0
    form={**parameters,'frame':{'center':[cx,cy],'u':[ux,uy],'bounds':[u0,v0,u1,v1]},'solids':[]}
    def part(name,area,lo,hi):
        if area.is_empty:return
        polygons=[area] if area.geom_type=='Polygon' else list(area.geoms)
        polygons=[orient(p,1) for p in polygons if p.area>.001]
        rings,triangles=pack_geometry(polygons)
        form['solids'].append({'name':name,'polygons':rings,'triangles':triangles,'bottom':lo,'top':hi})
    def cut_rect(x0,y0,x1,y1):return transform(world,box(x0,y0,x1,y1))
    kind=parameters['kind'];h=parameters['bodyHeight']
    if kind=='library':
        recess=cut_rect(-w*.27,v0-.1,w*.27,v0+5)
        part('入口两侧与下部主体',polygon.difference(recess),0,10.2)
        part('门厅上方阅览体量',polygon,10.2,h)
        for side in (-1,1):
            x0,x1=(u0,u0+w*.23) if side<0 else (u1-w*.23,u1)
            part('端部高起体量',polygon.intersection(cut_rect(x0,v0,x1,v1)),h,record['height']-.5)
        form['entry']={'width':w*.54,'depth':12,'rise':4.0,'recessDepth':5}
        entry=transform(world,Polygon([(-w*.46,v0-12),(w*.46,v0-12),(w*.29,v0),(-w*.29,v0)]))
        form['entryFootprint']=list(entry.exterior.coords)
    elif kind=='gallery':
        # An open connector; slabs/columns are assembled in Blender.
        pass
    elif kind=='gym':
        part('体育馆围护主体',polygon,0,h)
    else:
        portal_width=parameters.get('portalWidth',0)
        portal=cut_rect(-portal_width/2,v0-1,portal_width/2,v1+1) if portal_width else Polygon()
        stair=Polygon()
        if parameters.get('openStair'):
            x=parameters['openStair']['centerFraction']*w
            sw=parameters['openStair']['width']
            stair=cut_rect(x-sw/2,v0-.1,x+sw/2,v0+3.7)
        shape=polygon.difference(stair)
        part('底层门洞两侧主体',shape.difference(portal),0,3.8)
        part('门洞上方主体',shape,3.8,h)
        form['portalCeiling']=list(polygon.intersection(portal).exterior.coords) if portal_width else []
        for i,interval in enumerate(parameters.get('roofPavilions',[])):
            x0,x1=[u0+w*v for v in interval]
            area=polygon.intersection(cut_rect(x0,v0,x1,v1))
            part(f'屋面高起分段{i+1}',area,h,record['height']-.45)
    return form
