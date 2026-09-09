"""Restore the published, attributed snapshot without changing its source dates."""
import gzip,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1];source=root/'data/snapshots';out=root/'work/geodata';out.mkdir(parents=True,exist_ok=True)
(out/'osm.json').write_bytes(gzip.decompress((source/'osm-2026-09-09.json.gz').read_bytes()))
for f in source.glob('terrain-*'):shutil.copy(f,out/f.name)
shutil.copy(source/'query.overpassql',out/'query.overpassql')
print('已恢复 2026-09-09 OSM 快照与历史 DEM 缓存。')
