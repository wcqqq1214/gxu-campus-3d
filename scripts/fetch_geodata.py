#!/usr/bin/env python3
"""Download a complete, versioned OSM snapshot and public elevation tiles."""
import argparse, concurrent.futures, datetime, json, math, urllib.parse, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'work/geodata'
REGION=json.loads((ROOT/'data/region.json').read_text())
def request(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'GxuCampus3D/1.0 (open-source geographic visualization)'}),timeout=120) as r:return r.read()
def fetch_osm(refresh=False):
    path=CACHE/'osm.json'
    if path.exists() and not refresh:return
    w,s,e,n=REGION['bbox']; b=f'({s},{w},{n},{e})'
    query=f'''[out:json][timeout:100];(
      nwr["building"]{b}; way["building:part"]{b};
      nwr["highway"]{b}; nwr["waterway"]{b};
      nwr["natural"]{b}; nwr["landuse"]{b};
      nwr["leisure"]{b}; nwr["amenity"]{b};
      nwr["barrier"]{b}; nwr["entrance"]{b};
      nwr["tourism"]{b};
    );out meta geom;'''
    (CACHE/'query.overpassql').write_text(query)
    for base in ['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']:
        try:
            raw=request(base+'?'+urllib.parse.urlencode({'data':query})); payload=json.loads(raw)
            if payload.get('remark') or not payload.get('elements'):raise RuntimeError(payload.get('remark','empty snapshot'))
            for element in payload['elements']:
                for key in ('user','uid','changeset'):element.pop(key,None)
            payload['retrievedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
            path.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')))
            print('OSM',len(payload['elements']),payload['osm3s']['timestamp_osm_base'],flush=True);return
        except Exception as exc:print(type(exc).__name__,str(exc),flush=True)
    raise RuntimeError('No complete OSM response; refusing partial data.')
def tile(lon,lat,z):return ((lon+180)/360*2**z,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*2**z)
def fetch_terrain():
    z=REGION['terrainZoom'];w,s,e,n=REGION['bbox'];x0,y0=tile(w,n,z);x1,y1=tile(e,s,z)
    def fetch(key):
        x,y=key;p=CACHE/f'terrain-{z}-{x}-{y}.png'
        if not p.exists():p.write_bytes(request(f'https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png'))
    keys=[(x,y) for x in range(int(x0),int(x1)+1) for y in range(int(y0),int(y1)+1)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(fetch,keys))
    if (CACHE/'terrain-source.json').exists():return
    (CACHE/'terrain-source.json').write_text(json.dumps({'source':'Mapzen Terrain Tiles / SRTM','url':'https://registry.opendata.aws/terrain-tiles/','retrievedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'capturePeriod':'SRTM: 2000-02; individual tile source dates not published','tileZoom':z,'tiles':keys}))
    print('Terrain tiles',len(keys),flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--refresh',action='store_true');args=parser.parse_args()
    CACHE.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(fetch_osm,args.refresh),pool.submit(fetch_terrain)]
        for j in jobs:j.result()
