"""Read optional bounded high-precision terrain export regions."""
import json
import math
from pathlib import Path


def load_precision_regions(root):
    path=Path(root)/'data/terrain-export-regions.json'
    if not path.exists():return []
    data=json.loads(path.read_text())
    if not isinstance(data,dict) or set(data)!={'schemaVersion','regions'} or data['schemaVersion']!=1 or not isinstance(data['regions'],list):
        raise ValueError('Invalid terrain export region schema')
    ids=set();regions=[]
    for item in data['regions']:
        if not isinstance(item,dict) or set(item)!={'id','bounds'}:
            raise ValueError('Invalid terrain export region')
        ident=item['id'];bounds=item['bounds']
        if not isinstance(ident,str) or not ident.strip() or ident in ids:
            raise ValueError('Invalid or duplicate terrain export region ID')
        if (not isinstance(bounds,list) or len(bounds)!=4
                or any(type(v) not in (int,float) or not math.isfinite(v) for v in bounds)
                or bounds[0]>=bounds[2] or bounds[1]>=bounds[3]):
            raise ValueError('Invalid terrain export region bounds')
        ids.add(ident);regions.append(bounds)
    return regions
