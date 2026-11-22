"""Replay the production V4–V6 entry points on the retained native campus input."""
import bpy,hashlib,json,pickle,sys
from pathlib import Path
from types import SimpleNamespace
p = Path(__file__).resolve().parent
stage = p.parent / 'roadside-terrain-v6/stage'
out = p / 'applied'
out.mkdir(exist_ok=True)
sys.path[:0]=[str(stage/'blender'),str(stage/'scripts')]
src=stage/'blender/build_campus.py'
whole=src.read_text()
begin=whole.index('from tree_terrain_changes import')
code=whole[begin:whole.index('\nfor k, m in base.items():',begin)]
base,C=pickle.loads((p.parent/'roads-terrain-v4/baseline-mesh.pkl').read_bytes())
trees=json.loads((p.parent/'roads-terrain-v3/stage/public/data/vegetation.json').read_text())
orig=[r[4] for r in trees]
objects={f'树木示意-{i:04}':SimpleNamespace(location=SimpleNamespace(z=r[4])) for i,r in enumerate(trees)}
import tree_terrain_changes as tc
measure=tc.tree_surface_heights;calls=[]
def counted(rows,terrain):
 calls.append(len(rows));return measure(rows,terrain)
tc.tree_surface_heights=counted
env=dict(base=base,C=C,trees=trees,DATA=out,BASE_ONLY=False,bpy=SimpleNamespace(data=SimpleNamespace(objects=objects)),json=json)
exec(compile(code,str(src),'exec'),env)
def sha(b):return hashlib.sha256(b).hexdigest()
digest=sha(pickle.dumps(base['terrain'],protocol=5))
assert all(o.location.z==r[4] for o,r in zip(objects.values(),trees))
record=dict(terrain=digest,vegetation=sha((out/'vegetation.json').read_bytes()),treeCount=len(trees),changedTrees=sum(r[4]!=v for r,v in zip(trees,orig)),heightPasses=len(calls),rays=sum(calls),faces=len(base['terrain'].f),verts=len(base['terrain'].v))
(out/'replay.json').write_text(json.dumps(record,indent=2));print(record,flush=True)
