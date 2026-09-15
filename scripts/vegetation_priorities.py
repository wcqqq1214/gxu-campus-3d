"""Keep surviving sourced planting groups ahead of schematic background rows."""
import json
from pathlib import Path


def priority_positions(layout, trees):
    present = {tuple(t[:2]) for t in trees}
    positions = {tuple(t[:2]) for kind in ('avenues', 'courtyards')
                 for group in layout.get(kind, []) for t in group['retainedCandidates']}
    return [list(p) for p in sorted(positions & present)]


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    data = root/'public/data'
    read = lambda name: json.loads((data/name).read_text())
    manifest = read('models.json')
    manifest['treePriorityPositions'] = priority_positions(read('vegetation-zones.json'), read('vegetation.json'))
    (data/'models.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print('Priority tree positions:', len(manifest['treePriorityPositions']))
