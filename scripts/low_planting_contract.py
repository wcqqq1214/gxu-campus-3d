"""Standard-library fingerprints used by data preparation and Blender."""
import hashlib
import json

CONTEXT_FILES = ('surfaces', 'infrastructure', 'surroundings', 'campus-roads',
                 'sites', 'pavings', 'shores', 'sports', 'buildings', 'landmarks', 'basketball')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def context_value(root, config, data):
    value = {k:data[k] for k in CONTEXT_FILES if k not in ('buildings', 'landmarks')}
    value['buildings'] = [{k:b.get(k) for k in ('id', 'polygons', 'architecture', 'center', 'landmark')}
                          for b in data['buildings']]
    value['attachedPorticos'] = [{'buildingId':b['id'], 'entranceId':e['id'],
                                  'footprint':e['attachedPortico']['footprint']}
                                 for b in data['buildings']
                                 for e in b.get('form', {}).get('entrances', [])
                                 if 'attachedPortico' in e]
    value['landmarks'] = [{k:l.get(k) for k in ('id', 'placeKind', 'bounds', 'center', 'radius')}
                          for l in data['landmarks']]
    flights=[{'buildingId':b['id'],'entranceId':e['id'],'footprint':e['stairFlight']['footprint']}
             for b in data['buildings'] for e in b.get('form',{}).get('entrances',[]) if 'stairFlight' in e]
    if flights:value['stairFlights']=flights
    value['config'] = config
    value['openZones'] = json.loads((root / 'data/vegetation-zones.json').read_text())
    value['campus'] = next(f['geometry'] for f in json.loads((root / 'public/data/geography.geojson').read_text())['features'] if f['id'] == 'campus')
    return value


def load_prepared(root):
    config = json.loads((root / 'data/low-planting.json').read_text())
    prepared = json.loads((root / 'public/data/low-planting.json').read_text())
    data = {name:json.loads((root / 'public/data' / (name + '.json')).read_text()) for name in CONTEXT_FILES}
    if prepared['configRevision'] != digest(config) or prepared['contextRevision'] != digest(context_value(root, config, data)):
        raise ValueError('Low-planting context is stale; run vegetation preparation')
    if not prepared['placementPassed']:
        raise ValueError('Low-planting placement was not validated')
    return prepared['plantings']
