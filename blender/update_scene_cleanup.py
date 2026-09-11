"""Synchronize the selected ground cleanup to the web model and editable source."""
import hashlib,json,sys
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from geometry import MATERIALS
from huicui import compact_source
from preserve_glb_geometry import preserve_geometry,unpack

path=ROOT/'public/models/base.glb'
previous=path.read_bytes()
before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in path.parent.glob('*.glb')}
script=ROOT/'blender/build_campus.py'
ns={'__file__':str(script),'__name__':'__main__'}
sys.argv.append('--base-only')
try:exec(compile(script.read_text(),str(script),'exec'),ns)
except SystemExit as result:
    if result.code not in (None,0):raise

# All unrelated compressed geometry is preserved byte for byte.
changed={'terrain','roads','water','green','sports','infra-road-00'}
old,_=unpack(previous)
current,_=unpack(path.read_bytes())
current_names={n.get('name') for n in current['nodes']}
removed=[n['name'] for n in old['nodes'] if 'mesh' in n and n['name'] not in current_names]
assert all(n in {'basketball-bank-1379222486','basketball-bank-1379222488'} for n in removed),removed
retained=[n['name'] for n in old['nodes'] if 'mesh' in n and n['name'] not in changed and n['name'] in current_names]
preserve_geometry(previous,path,retained)
chunk=next(c for c in ns['infrastructure']['chunks'] if c['id']=='infra-road-00')
near=ns['road_chunk'](chunk,ns['C'],True)
ns['export']('infra-road-00.glb',{'infra-road-00':near})
blob=path.read_bytes()
manifest_path=ROOT/'public/data/models.json'
manifest=json.loads(manifest_path.read_text())
manifest['base'].update(bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest())
entry=next(e for e in manifest['infrastructure'] if e['id']=='infra-road-00')
raw=(ROOT/'public/models/infra-road-00.glb').read_bytes()
entry.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),bounds=chunk['bounds'])
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2))

names=[m.name for m in MATERIALS]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
MATERIALS[:]=[bpy.data.materials[name] for name in names]
for key in sorted(changed):
    if key=='infra-road-00':
        old=next(o for o in bpy.data.objects if o.get('infrastructureId')==key)
        name=old.name
    else:
        name='其他运动场地' if key=='sports' else key
        old=bpy.data.objects[name]
    collection=old.users_collection[0];props=dict(old.items());mesh=old.data
    bpy.data.objects.remove(old,do_unlink=True)
    if mesh.users==0:bpy.data.meshes.remove(mesh)
    compact_source((near if key=='infra-road-00' else ns['base'][key]).object(name,collection,props))
court_ids={c['id'] for c in ns['basketball']['courts']}
bank_ids={b['id'] for b in ns['basketball']['banks']}
for obj in list(bpy.data.objects):
    if ((obj.get('basketballCourt') and obj['basketballCourt'] not in court_ids)
            or (obj.get('basketballBank') and obj['basketballBank'] not in bank_ids)):
        mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'),compress=True)
assert all(hashlib.sha256((path.parent/n).read_bytes()).hexdigest()==h for n,h in before.items() if n not in {'base.glb','infra-road-00.glb'})
report={'updatedGroundNodes':sorted(changed),'removedBasketballBanks':removed,'basketballCourts':len(court_ids),'retainedBaseNodes':len(retained),
        'retainedNearAndTreeGlbs':len(before)-2,'baseBytes':len(blob),
        'blendBytes':(ROOT/'blender/gxu-campus.blend').stat().st_size}
assert report['blendBytes']<100*1024*1024,report
(ROOT/'docs/model-checks/scene-cleanup-models.json').write_text(json.dumps(report,indent=2)+'\n')
print(report,flush=True)
