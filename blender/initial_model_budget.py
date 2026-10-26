"""Shared decimal-byte budget for base.glb + trees.glb, including textures."""
import json
from pathlib import Path


def check_initial_model_budget(total):
    budget = json.loads((Path(__file__).resolve().parents[1] /
                        'data/initial-model-budget.json').read_text())
    target, limit = budget['targetBytes'], budget['hardLimitBytes']
    if total > limit:
        raise RuntimeError(f'Initial model budget exceeded: {total:,} bytes > {limit:,}')
    status = 'WARNING: above target' if total > target else 'OK'
    print(f'Initial model budget [{status}]: {total:,} bytes; '
          f'target {target:,}, hard limit {limit:,}', flush=True)
    return dict(initialModelBytes=total, initialTargetBytes=target,
                initialBudgetBytes=limit, initialTargetExceeded=total > target)
