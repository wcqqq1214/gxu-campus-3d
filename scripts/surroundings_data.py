"""Unify mapped perimeter road surfaces and expose the approximate campus outline.

Original OSM axes stay intact. Road widths / edge treatment are display estimates;
grade-separated ways and the detailed Nongyuan corridor retain their existing models.
"""
import json,math
from pathlib import Path
import numpy as np
import mapbox_earcut as earcut
from shapely.geometry import Polygon,LineString,shape,Point,box
from shapely.ops import transform,unary_union
from shapely import make_valid
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/data'
def polys(g):return [g] if g.geom_type=='Polygon' else [p for p in getattr(g,'geoms',[]) if p.geom_type=='Polygon']
def triangulate(g):
    vertices=[];triangles=[]
    for p in polys(g):
        rings=[list(p.exterior.coords)[:-1]]+[list(r.coords)[:-1] for r in p.interiors];v=[list(a) for ring in rings for a in ring]
        if not v:continue
        tri=earcut.triangulate_float64(np.asarray(v,dtype=np.float64),np.cumsum([len(r) for r in rings],dtype=np.uint32))
        triangles.extend(int(i)+len(vertices) for i in tri);vertices.extend(v)
    return {'vertices':vertices,'triangles':triangles}
def tiled_triangles(g,step=12):
    # Tile before triangulation: long thin curb polygons must not generate
    # exponential subdivisions across their entire length in the mesh builder.
    vertices=[];triangles=[]
    if g.is_empty:return {'vertices':vertices,'triangles':triangles}
    x0,y0,x1,y1=g.bounds
    for x in range(math.floor(x0/step)*step,math.ceil(x1/step)*step,step):
        for y in range(math.floor(y0/step)*step,math.ceil(y1/step)*step,step):
            cell=box(x,y,x+step,y+step)
            if not g.intersects(cell):continue
            part=triangulate(g.intersection(cell))
            triangles.extend(i+len(vertices) for i in part['triangles']);vertices.extend(part['vertices'])
    return {'vertices':vertices,'triangles':triangles}
def surface_shape(s):
    vs=s['vertices'];ts=s['triangles']
    return unary_union([Polygon([vs[i] for i in ts[k:k+3]]) for k in range(0,len(ts),3)])
def prepare_surroundings():
    from prepare_geodata import project
    geo=json.loads((OUT/'geography.geojson').read_text());infra=json.loads((OUT/'infrastructure.json').read_text());ss=json.loads((OUT/'surfaces.json').read_text());bs=json.loads((OUT/'buildings.json').read_text());terrain=json.loads((OUT/'terrain.json').read_text())
    campus=transform(project,shape(next(f for f in geo['features'] if f['id']=='campus')['geometry']));clip=campus.buffer(300)
    display=transform(project,shape(next(f for f in geo['features'] if f['id']=='campus-display-area')['geometry']))
    obstacles=unary_union([Polygon(p[0],p[1:]) for b in bs for p in b['polygons']]).buffer(2.2)
    features={f['id']:f for f in geo['features']};overrides={};groups={'carriageway':[],'walkway':[]};records=[];original=[];skipped=[]
    widths={'trunk':11,'trunk_link':6,'primary':18,'primary_link':6,'secondary':14,'secondary_link':6,'tertiary':12,'residential':8,'unclassified':7,'service':5,'living_street':5,'footway':2.2,'path':2,'steps':2,'pedestrian':5}
    for i,s in enumerate(ss):
        if s['kind']!='roads' or s['id'] in infra['replaceSurfaceIds']:continue
        f=features.get(s['id'])
        if not f:continue
        tags=s['tags'];axis=transform(project,shape(f['geometry']))
        if campus.covers(axis):continue
        # Keep distinct-level crossings out of the at-grade union.
        if tags.get('bridge') or tags.get('tunnel') or str(tags.get('layer','0'))!='0':skipped.append(s['id']);continue
        old=surface_shape({**s,**infra['surfaceOverrides'].get(str(i),{})})
        overrides[str(i)]=triangulate(old.intersection(campus));original.append(old.difference(campus))
        kind='walkway' if tags.get('highway') in ('footway','path','steps','pedestrian') else 'carriageway'
        width=widths.get(tags.get('highway'),5)
        try:
            if tags.get('width'):width=max(1,min(30,float(tags['width'].split()[0])))
        except (ValueError,TypeError):pass
        # Closed road ways are centerline loops unless OSM explicitly says area.
        if axis.geom_type in ('Polygon','MultiPolygon') and tags.get('area')!='yes':axis=axis.boundary
        paved=axis if axis.geom_type in ('Polygon','MultiPolygon') else axis.buffer(width/2,cap_style=1,join_style=1,quad_segs=4)
        paved=make_valid(paved.intersection(clip).difference(campus).difference(obstacles))
        groups[kind].append(paved)
        records.append({'id':s['id'],'name':tags.get('name',''),'highway':tags.get('highway'),'width':width,'widthBasis':'OSM width' if tags.get('width') else '按道路等级估算','osmVersion':f['properties'].get('osmVersion'),'osmEditedAt':f['properties'].get('osmEditedAt'),'sourceUrl':f['properties'].get('sourceUrl')})
    raw={k:unary_union(v) for k,v in groups.items()}
    road=raw['carriageway'].simplify(.12,preserve_topology=True).difference(obstacles).difference(campus)
    walk=raw['walkway'].simplify(.10,preserve_topology=True).difference(road).difference(obstacles).difference(campus)
    # A thin, disjoint curb ring clarifies the edge without double drawing asphalt.
    curb=road.buffer(.45,join_style=1,quad_segs=3).difference(road).difference(walk).difference(campus).difference(obstacles).intersection(clip)
    layers=[dict(id='surrounding-'+k,material=mat,**tiled_triangles(g)) for k,mat,g in [('road','asphalt',road),('walk','path',walk),('curb','white',curb)]]
    cols,rows=terrain['cols'],terrain['rows'];x0,y0,x1,y1=terrain['bounds'];hh=terrain['heights']
    def elevation(x,y):
        u=max(0,min(cols-1.001,(x-x0)/(x1-x0)*(cols-1)));v=max(0,min(rows-1.001,(y-y0)/(y1-y0)*(rows-1)));i,j=int(u),int(v);a,t=u-i,v-j
        return (hh[j*cols+i]*(1-a)+hh[j*cols+i+1]*a)*(1-t)+(hh[(j+1)*cols+i]*(1-a)+hh[(j+1)*cols+i+1]*a)*t
    rings=[]
    for p in polys(display.simplify(.35,preserve_topology=True)):
        for ring in [p.exterior,*p.interiors]:
            points=[]
            for a,b in zip(ring.coords,list(ring.coords)[1:]):
                count=max(1,math.ceil(math.dist(a,b)/10))
                for t in np.linspace(0,1,count,endpoint=False):
                    x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t
                    points.append([round(x,3),round(y,3),round(elevation(x,y)+2,3)])
            points.append(points[0])
            points[-1]=points[0];rings.append(points)
    boundary={'version':1,'name':'校园大致边界','sourceUrl':'https://www.openstreetmap.org/way/398115378','snapshotAt':geo['metadata']['snapshotAt'],'note':'按 OSM 校园轮廓与农院路估算路幅绘制，仅供辨认校园大致范围，不表示精确围墙或权属界线。','rings':rings}
    raw_area=sum(g.area for g in original);union_area=unary_union(original).area
    report={'roadFeatures':len(records),'preservedGradeSeparatedIds':skipped,'beforeOverlappingArea':round(raw_area-union_area,3),'afterRoadWalkOverlap':round(road.intersection(walk).area,6),'roadCurbOverlap':round(road.intersection(curb).area,6),'buildingOverlap':round(unary_union([road,walk,curb]).intersection(obstacles).area,6),'insideCampusOverlap':round(unary_union([road,walk,curb]).intersection(campus).area,6),'roadArea':round(road.area,2),'boundaryRings':len(rings),'boundaryArea':round(display.area,2)}
    data={'version':1,'basis':'2026 OSM 快照；保留道路轴线，路幅与浅色路缘估算；仅规整校外同层地面道路。','surfaceOverrides':overrides,'layers':layers,'sources':records,'checks':report}
    for name,value in [('surroundings.json',data),('campus-boundary.json',boundary)]:
        (OUT/name).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')))
    (ROOT/'docs/model-checks/surroundings-data.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report)
if __name__=='__main__':prepare_surroundings()
