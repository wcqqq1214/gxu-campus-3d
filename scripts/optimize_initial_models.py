"""Losslessly repack existing initial GLBs and refresh their manifest hashes.

Run after model export, without opening or regenerating the Blender scene.
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from preserve_glb_geometry import compact_buffer_views


def main():
    manifest_path = ROOT / 'public/data/models.json'
    manifest = json.loads(manifest_path.read_text())
    # Prepare both outputs before publishing, so encoder failures leave all
    # production assets and their manifest untouched.
    with tempfile.TemporaryDirectory() as temporary:
        prepared = []
        for key in ('base', 'trees'):
            target = ROOT / 'public' / manifest[key]['url']
            source = target.read_bytes()
            candidate = Path(temporary) / target.name
            candidate.write_bytes(source)
            compact_buffer_views(candidate, optimize_jpegs=key == 'base')
            result = candidate.read_bytes()
            if len(result) > len(source):
                raise ValueError(f'Packing enlarged {target.name}; original assets retained')
            manifest[key]['bytes'] = len(result)
            manifest[key]['sha256'] = hashlib.sha256(result).hexdigest()
            prepared.append((target, result))
            print(f'{target.name}: {len(source)} -> {len(result)} bytes')
        for target, result in prepared:
            target.write_bytes(result)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
