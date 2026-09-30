"""Shared foundation freshness check, usable in Blender without GIS libraries."""
import hashlib
import json

INPUTS = ('buildings', 'terrain', 'surfaces', 'infrastructure', 'surroundings',
          'campus-roads', 'sites', 'pavings', 'shores')


def foundation_context(root):
    context = {name:json.loads((root/'public/data'/f'{name}.json').read_text()) for name in INPUTS}
    context['buildings'] = [{k:v for k,v in b.items() if k not in ('elevation','zone','chunk')} for b in context['buildings']]
    context['config'] = json.loads((root/'data/foundation-overrides.json').read_text())
    return context


def revision(context):
    return hashlib.sha256(json.dumps(context,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def load_foundations(root):
    data = json.loads((root/'public/data/foundations.json').read_text())
    if data['contextRevision'] != revision(foundation_context(root)):
        raise ValueError('Foundation context is stale; run data preparation')
    return data
