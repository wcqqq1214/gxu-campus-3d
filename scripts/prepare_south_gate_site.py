"""Prepare bounded surface meshes and convex clipping masks from the dated trace.

Run with work/venv/bin/python. Imagery stays local; only traced vectors are shipped.
"""
import json, math
from pathlib import Path
from shapely.geometry import Polygon, box
from shapely.ops import triangulate, unary_union
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'data/south-gate-site.json';d=json.loads(p.read_text())
features=d['features']
# Recompute local ground coordinates from the retained pixel trace.
for f in features.values():
 f['localMeters']=[]
 for px,py in f['pixels']:
  n=2**d['zoom']*256;lon=(d['tileOrigin'][0]*256+px)/n*360-180
  lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*(d['tileOrigin'][1]*256+py)/n))))
  f['localMeters'].append([round((lon-108.2882)*111320*math.cos(math.radians(22.84715))-d['localOrigin'][0],3),round((lat-22.84715)*111320-d['localOrigin'][1],3)])
polys={k:Polygon(v['localMeters']) for k,v in features.items()}
assert all(p.is_valid for p in polys.values())
def triangles(poly):
 if poly.is_empty:return []
 if poly.geom_type!='Polygon':return [t for p in poly.geoms if p.geom_type in ('Polygon','MultiPolygon') for t in triangles(p)]
 return [list(t.exterior.coords)[:3] for t in triangulate(poly) if poly.covers(t.representative_point())]
def grid(poly,step):
 x0,y0,x1,y1=poly.bounds;result=[]
 for i in range(math.floor(x0/step),math.ceil(x1/step)):
  for j in range(math.floor(y0/step),math.ceil(y1/step)):
   result+=triangles(poly.intersection(box(i*step,j*step,(i+1)*step,(j+1)*step)))
 return result
# Include the superseded symmetric asphalt patch so old paint is removed.
mask=unary_union([polys['road'],polys['westApron'],polys['eastApron'],box(-14,-36,14,3)])
parts=[Polygon(t) for t in triangles(mask)]
changed=True
while changed:
 changed=False
 for i,a in enumerate(parts):
  for j in range(i+1,len(parts)):
   u=a.union(parts[j])
   if u.geom_type=='Polygon' and not u.interiors and u.convex_hull.area-u.area<1e-7:
    parts[i]=u;parts.pop(j);changed=True;break
  if changed:break
# Cover the former too-wide road shoulder with the correct paving, not a grass slit.
road=polys['road']
d['roadTriangles']=grid(road,2.5)
d['pavingTriangles']={k:grid(polys[k],.6 if k=='island' else 1.2) for k in ['island','westApron','eastApron']}
d['maskConvexPolygons']=[list(p.exterior.coords)[:-1] for p in parts]
d['repairBounds']=list(mask.bounds)
# North-south paint strips clipped by the oblique crossing envelope.
stripe_polys=[]
for i in range(math.floor(polys['crossing'].bounds[0]),math.ceil(polys['crossing'].bounds[2])):
 s=polys['crossing'].intersection(box(i,-100,i+.5,10))
 if s.area>2.5 and s.bounds[2]-s.bounds[0]>.49:stripe_polys.append(s)
d['crossingStripeTriangles']=[grid(s,.65) for s in stripe_polys]
d['crossingStripeCenters']=[list(s.representative_point().coords)[0] for s in stripe_polys]
d['crossingGapCenters']=[list(polys['crossing'].intersection(box(i+.5,-100,i+1,10)).representative_point().coords)[0] for i in range(-15,10)]
p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')
print('Road triangles',len(d['roadTriangles']),'convex masks',len(parts),'stripes',len(stripe_polys),'bounds',d['repairBounds'])
