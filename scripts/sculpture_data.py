"""Curated sculpture POIs; keep the mapped source name separate from display name."""
import gzip,json,math
from prepare_geodata import ROOT,OUT,CACHE,project

def prepare_sculptures():
    catalogue=json.loads((ROOT/'data/sculptures.json').read_text())
    raw=CACHE/'osm.json'
    snapshot=json.loads(raw.read_text()) if raw.exists() else json.loads(gzip.decompress((ROOT/'data/snapshots/osm-2026-09-09.json.gz').read_bytes()))
    elements={f"{e['type']}/{e['id']}":e for e in snapshot['elements']}
    ids={s['id'] for s in catalogue}
    landmarks=[l for l in json.loads((OUT/'landmarks.json').read_text()) if l['id'] not in ids]
    geo=json.loads((OUT/'geography.geojson').read_text())
    geo['features']=[f for f in geo['features'] if f['id'] not in {s['osmId'] for s in catalogue}]
    terrain=json.loads((OUT/'terrain.json').read_text());x0,y0,x1,y1=terrain['bounds'];cols=terrain['cols'];rows=terrain['rows'];hh=terrain['heights']
    def height(x,y):
        u=max(0,min(cols-1.001,(x-x0)/(x1-x0)*(cols-1)));v=max(0,min(rows-1.001,(y-y0)/(y1-y0)*(rows-1)))
        i=int(u);j=int(v);a=u-i;b=v-j
        return (hh[j*cols+i]*(1-a)+hh[j*cols+i+1]*a)*(1-b)+(hh[(j+1)*cols+i]*(1-a)+hh[(j+1)*cols+i+1]*a)*b
    for l in catalogue:
        e=elements[l['osmId']];x,y=project(e['lon'],e['lat']);r=l['radius']
        l.update(center=[x,y],lonLat=[e['lon'],e['lat']],bounds=[x-r,y-r,x+r,y+r],
                 osmSourceName=e['tags'].get('name'),osmVersion=e['version'],osmEditedAt=e['timestamp'],
                 sourceRefs=['osm',l['reference']]+l['additionalReferences'])
        # The tiny estimated sculpture island sits above coarse ground / paving;
        # its outside edge returns to the sampled terrain rather than floating.
        l['islandElevation']=round(max(height(x+r*math.cos(i*math.tau/64),y+r*math.sin(i*math.tau/64)) for i in range(64))+.45,3)
        l['groundRing']=[[x+(r+1)*math.cos(i*math.tau/64),y+(r+1)*math.sin(i*math.tau/64),height(x+(r+1)*math.cos(i*math.tau/64),y+(r+1)*math.sin(i*math.tau/64))+.42] for i in range(64)]
        l['elevation']=round(height(x,y),2);l['zone']='east';landmarks.append(l)
        geo['features'].append({'type':'Feature','id':l['osmId'],'geometry':{'type':'Point','coordinates':l['lonLat']},
          'properties':{'kind':'artwork','name':l['name'],'osmSourceName':l['osmSourceName'],'tags':e['tags'],
            'landmark':l['id'],'insideCampus':True,'sourceUrl':l['sourceUrl'],'osmVersion':e['version'],
            'osmEditedAt':e['timestamp'],'positionBasis':l['positionBasis']}})
    # Explicit order for newly curated buildings keeps existing index numbers stable.
    landmarks.sort(key=lambda l:l.get('navigationOrder',0))
    trees=json.loads((OUT/'vegetation.json').read_text())
    trees=[t for t in trees if all(math.dist(t[:2],l['center'])>l['radius']+1+4*t[2]/9 for l in catalogue)]
    overview=json.loads((OUT/'overview.json').read_text());overview.update(landmarks=len(landmarks),trees=len(trees))
    for name,d in [('landmarks.json',landmarks),('geography.geojson',geo),('vegetation.json',trees),('overview.json',overview)]:
        (OUT/name).write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')))
    print('时光之门已绑定 OSM 节点；精选地标',len(landmarks),'示意树',len(trees),flush=True)

if __name__=='__main__':prepare_sculptures()
