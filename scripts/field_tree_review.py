"""Apply image-reviewed exclusions only to the matching background candidates."""

import json


def reviewed_field_positions(root):
    review = json.loads((root / 'data/east-north-field-vegetation.json').read_text())
    groups = {'exclude': set(), 'retain': set()}
    for row in review['trees']:
        decision = row['decision']
        position = tuple(row['xy'])
        if decision not in groups:
            raise ValueError(f'Unknown field tree decision at {position}: {decision!r}')
        if position in groups['exclude'] or position in groups['retain']:
            raise ValueError(f'Duplicate field tree position: {position}')
        groups[decision].add(position)
    return groups['exclude'], groups['retain']
