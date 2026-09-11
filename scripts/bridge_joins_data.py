"""Local transition aprons at six existing underpass mouths; dimensions are estimates."""
import math
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union,linemerge,substring
from surroundings_data import surface_shape,tiled_triangles
TRIM=8

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

def prepare_joins(infra,surfaces,roads):
    vehicle=[];paths=[]
    for s in surfaces:
        t=s['tags']
        if s['kind']!='roads' or s.get('suppressed') or s['id'] in infra['replaceSurfaceIds'] or t.get('bridge') or t.get('tunnel') or str(t.get('layer','0'))!='0':continue
        (paths if t.get('highway') in ('footway','path','steps','pedestrian') else vehicle).append(surface_shape(s))
    vehicle=unary_union(vehicle);paths=unary_union(paths);result=[];masks=[]
    axes={ident:line for ident,line,kind in roads}
    for b in infra['bridges']:
        line=linemerge([axes[i] for i in b['lowerRoadIds']])
        for end in [0,1]:
            original=b['underpass'];idx=TRIM if end==0 else len(original)-TRIM-1
            seq=original[idx::-1] if end==0 else original[idx:]
            walk=b['pedestrian']['path'][idx]
            a=original[idx-1];c=original[idx+1];norm=math.hypot(c[0]-a[0],c[1]-a[1]);ux=(c[0]-a[0])/norm;uy=(c[1]-a[1])/norm
            if end==0:ux=-ux;uy=-uy
            start=seq[0];tip=seq[-1];axis=LineString([p[:2] for p in seq]);distance=axis.length
            tip_d=line.project(Point(tip[:2]));start_d=line.project(Point(start[:2]));direction=1 if tip_d>start_d else -1
            available=line.length-tip_d if direction>0 else tip_d
            extension=min(20,available);junction=extension<3
            if extension>0:
                tail=substring(line,tip_d,tip_d+direction*extension)
                coords=list(axis.coords)+list(tail.coords)[1:];axis=LineString(coords)
            # Influence includes cross streets, but begins exactly at the old ribbon edge.
            nx,ny=-uy,ux
            span=distance+extension+16
            mask=Polygon([(start[0]+nx*s+ux*t,start[1]+ny*s+uy*t) for s,t in [(-25,0),(-25,span),(25,span),(25,0)]])
            masks.append(mask)
            sections=[]
            for i in range(math.ceil(axis.length)+1):
                d=min(axis.length,i);p=axis.interpolate(d);left=axis.interpolate(max(0,d-.2));right=axis.interpolate(min(axis.length,d+.2))
                dx=right.x-left.x;dy=right.y-left.y;size=math.hypot(dx,dy);u,v=(ux,uy) if d==0 else (dx/size,dy/size)
                q=smooth(d/axis.length)
                target=5 if junction else 3.72
                car=5*(1-q)+target*q
                width=8.65 if junction else 8.65*(1-q)+4*q
                inner=6.3*(1-q)+(target+.28)*q;outer=8.5*(1-q)+(target+.28)*q
                sections.append((p.x,p.y,u,v,car,inner,outer,width))
            def ribbon(lo,hi):
                polys=[]
                for a,c in zip(sections,sections[1:]):
                    pts=[]
                    for p,k in [(a,lo),(c,lo),(c,hi),(a,hi)]:
                        offset=k(p);pts.append((p[0]-p[3]*offset,p[1]+p[2]*offset))
                    poly=Polygon(pts)
                    if poly.area>1e-9:polys.append(poly.buffer(0))
                return unary_union(polys).buffer(0)
            full=ribbon(lambda p:-p[7],lambda p:p[7])
            car=ribbon(lambda p:-p[4],lambda p:p[4]).union(vehicle.buffer(-.28).intersection(mask)).intersection(mask)
            # Remove kerbs and raised walks wherever a mapped side road joins.
            walkshape=unary_union([ribbon(lambda p:side*p[5],lambda p:side*p[6]) for side in [-1,1]]).difference(car.buffer(.28))
            foot=paths.intersection(mask).difference(car.buffer(.28));walkshape=walkshape.union(foot)
            paving=full.union(vehicle.intersection(mask)).union(foot).intersection(mask)
            curb=paving.difference(car).difference(walkshape)
            patch={'id':b['id']+'-'+str(end),'bridgeId':b['id'],'end':end,'trim':TRIM,'axis':list(axis.coords),'start':start,'direction':[ux,uy],'walkStart':walk[2],'rampLength':distance,'extension':extension,'junction':junction,'ramp':seq,'mask':list(mask.exterior.coords),'layers':[]}
            for name,mat,g in [('沥青','asphalt',car),('步道缓接','path',walkshape),('渐变路缘','curb',curb)]:
                patch['layers'].append(dict(id=patch['id']+'-'+name,material=mat,**tiled_triangles(g,step=2)))
            # Recessed backing closes sub-centimetre cracks from independent Draco quantization.
            backing=car.buffer(.16,join_style=2).difference(car.buffer(-.2,join_style=2))
            patch['layers'].append(dict(id=patch['id']+'-接缝下承层',material='asphalt',zOffset=-.12,**tiled_triangles(backing,step=2)))
            # The old excavation is wider than the tapered apron: close it with ground.
            cut=LineString([p[:2] for p in seq]).buffer(8.65,cap_style=2,join_style=2).intersection(mask)
            ground=cut.difference(paving)
            patch['layers'].append(dict(id=patch['id']+'-地面回填',material='grass',**tiled_triangles(ground,step=2)))
            result.append(patch)
    return result,unary_union(masks)
