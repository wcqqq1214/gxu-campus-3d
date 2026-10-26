"""Finalize existing prepared data offline, without rebuilding geometry or models."""
import argparse
import json
from pathlib import Path

from foundation_contract import foundation_context, revision
from low_planting_contract import CONTEXT_FILES, context_value, context_revision, digest
from mapped_canopy_data import context_revision as canopy_revision, part_revision
from public_data_fields import without_documentation

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ('buildings.json', 'geography.geojson', 'sites.json', 'foundations.json')


def export_public_data(root=ROOT):
    out = root / 'public/data'
    read = lambda name: json.loads((out / name).read_text())
    values = {name:read(name) for name in (*EXPORTS, 'low-planting.json', 'pavings.json', 'shores.json')}
    foundation = foundation_context(root)
    planting_config = json.loads((root / 'data/low-planting.json').read_text())
    planting_data = {name:read(name + '.json') for name in CONTEXT_FILES}
    planting = context_value(root, planting_config, planting_data)
    # Accept the old fingerprint only when it still matches the complete input.
    # Never bless a geometry/config change by merely replacing its fingerprint.
    if values['foundations.json']['contextRevision'] not in (digest(foundation), revision(foundation)):
        raise ValueError('Foundation context is stale; run data preparation before export')
    low = values['low-planting.json']
    if (low['contextRevision'] not in (digest(planting), context_revision(planting))
            or low['configRevision'] != digest(planting_config) or not low['placementPassed']):
        raise ValueError('Low-planting context is stale; run vegetation preparation before export')
    ground = {name:read(name+'.json') for name in
              ('surfaces','infrastructure','surroundings','campus-roads')}
    def ground_contexts(sites):
        paving = [ground[name] for name in ('surfaces','infrastructure','surroundings','campus-roads')] + [sites]
        shore = {'surfaces':ground['surfaces'],'roads':ground['campus-roads'],
                 'surroundings':ground['surroundings'],'infrastructure':ground['infrastructure'],
                 'sites':sites,'buildings':[[b['id'],b['polygons']] for b in values['buildings.json']]}
        return {'pavings.json':paving,'shores.json':shore}
    raw_contexts = ground_contexts(values['sites.json'])
    exported_contexts = ground_contexts(without_documentation(values['sites.json']))
    # Removing site evidence changes the serialized context. Validate the
    # prepared input first; only then migrate its hash to the exported input.
    for name, context in raw_contexts.items():
        if values[name]['contextRevision'] not in (digest(context),digest(exported_contexts[name])):
            raise ValueError(f'{name} context is stale; run data preparation before export')
        values[name]['contextRevision'] = digest(exported_contexts[name])
    buildings = values['buildings.json']
    by_id = {building['id']:building for building in buildings}
    for building in buildings:
        for entry in building.get('form', {}).get('entrances', []):
            if 'mappedCanopy' not in entry:
                continue
            config = entry['mappedCanopy']
            roof = by_id[config['buildingId']]
            part = next(p for p in roof['form']['parts'] if p['id'] == config['partId'])
            shelter = entry['shelter']
            payload = [{k:v for k,v in entry.items() if k != 'shelter'}, roof['center'], roof['polygons'], part]
            if (shelter['contextRevision'] not in (digest(payload), canopy_revision(entry, roof, part))
                    or shelter['partRevision'] not in (digest(part), part_revision(part))):
                raise ValueError('Mapped canopy context is stale; prepare the data before export')
            shelter['contextRevision'] = canopy_revision(entry, roof, part)
            shelter['partRevision'] = part_revision(part)
    for name in EXPORTS:
        values[name] = without_documentation(values[name])
    # Canopy fingerprints are part of the building input to the foundation guard.
    foundation['buildings'] = [{k:v for k,v in b.items() if k not in ('elevation', 'zone', 'chunk')}
                               for b in values['buildings.json']]
    for name in ('sites','pavings','shores'):
        foundation[name] = values[name+'.json']
        planting[name] = values[name+'.json']
    values['foundations.json']['contextRevision'] = revision(foundation)
    low['contextRevision'] = context_revision(planting)
    sizes = {}
    # All validation and serialization finish before any public file is replaced.
    encoded = {}
    for name, value in values.items():
        before = (out / name).read_bytes()
        after = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
        if before.endswith(b'\n'):
            after += b'\n'
        encoded[name] = after
        sizes[name] = {'before':len(before), 'after':len(after), 'saved':len(before)-len(after)}
    for name, payload in encoded.items():
        (out / name).write_bytes(payload)
    return sizes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(export_public_data(args.root.resolve()), ensure_ascii=False, indent=2))
