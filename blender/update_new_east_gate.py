"""Build a bounded new-east-gate candidate; --publish installs it after validation."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from campus_gates import campus_gate
from export_attributes import omit_unused_uvs
from geometry import MATERIALS
from incremental_glb import splice_nodes, validate_retained
from incremental_update import copy_inputs, snapshot, publication_lock, publish, require_recovered, run_checked
from initial_model_budget import check_initial_model_budget
from preserve_glb_geometry import unpack, mesh_nodes_by_name


def export(obj, target):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    with omit_unused_uvs(deduplicate_vertices=True):
        bpy.ops.export_scene.gltf(
            filepath=str(target), export_format='GLB', use_selection=True,
            export_extras=True, export_cameras=False, export_lights=False,
            export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=7,
            export_draco_position_quantization=18,
            export_draco_normal_quantization=10,
            export_materials='EXPORT')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    target=args.output_root.resolve()
    with publication_lock(ROOT):
        require_recovered(ROOT)
        before=snapshot(ROOT)
        copy_inputs(ROOT,target)
        for folder in ['app','components']:
            shutil.copytree(ROOT/folder,target/folder)
        if snapshot(ROOT)!=before:raise RuntimeError('Inputs changed during candidate copy')
    (target/'work/baseline.json').write_text(json.dumps(before))
    catalog=json.loads((target/'public/data/landmarks.json').read_text())
    record=next(x for x in catalog if x['id']=='new-east-gate')
    source=next(x for x in json.loads((target/'data/landmarks.json').read_text()) if x['id']==record['id'])
    record.update(source)
    record['sourceRefs']=['osm',record['reference'],*record['additionalReferences']]
    (target/'public/data/landmarks.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
    references=json.loads((target/'public/data/sources.json').read_text())
    fresh={s['id']:s for s in json.loads((target/'data/sources.json').read_text()) if s['id'] in record['sourceRefs']}
    references['sources']=[fresh.pop(s['id'],s) for s in references['sources']]+list(fresh.values())
    (target/'public/data/sources.json').write_text(json.dumps(references,ensure_ascii=False,indent=2)+'\n')
    bpy.ops.wm.open_mainfile(filepath=str(target/'blender/gxu-campus.blend'))
    old,=[o for o in bpy.context.scene.objects if o.get('landmark')==record['id']]
    MATERIALS[:]=list(bpy.data.materials)
    C={m.name:i for i,m in enumerate(MATERIALS)}
    collection=old.users_collection[0];props=dict(old.items());name=old.name
    unchanged={o.name:(o.as_pointer(),o.data.as_pointer() if o.data else None)
               for o in bpy.context.scene.objects if o!=old}
    high=campus_gate(record,record['elevation'],C,True)
    low=campus_gate(record,record['elevation'],C,False)
    key='landmark-new-east-gate'
    original=(target/'public/models/base.glb').read_bytes()
    export_props=dict(mesh_nodes_by_name(unpack(original)[0])[key].get('extras',{}))
    for mesh,path in [(high,target/'public/models/new-east-gate.glb'),(low,target/'work/new-east-base.glb')]:
        obj=mesh.object(key,collection,export_props)
        export(obj,path)
        data=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(data)
    updated=splice_nodes(original,(target/'work/new-east-base.glb').read_bytes(),{key})
    validate_retained(original,updated,{key})
    (target/'public/models/base.glb').write_bytes(updated)
    old_mesh=old.data;bpy.data.objects.remove(old,do_unlink=True)
    if not old_mesh.users:bpy.data.meshes.remove(old_mesh)
    high.object(name,collection,{**props,'modelingBasis':'photo','reference':record['reference']})
    assert all((bpy.data.objects[k].as_pointer(),bpy.data.objects[k].data.as_pointer() if bpy.data.objects[k].data else None)==v for k,v in unchanged.items())
    bpy.ops.wm.save_as_mainfile(filepath=str(target/'blender/gxu-campus.blend'),compress=True)
    manifest=json.loads((target/'public/data/models.json').read_text())
    for asset in [manifest['base'],next(x for x in manifest['landmarks'] if x['id']==record['id'])]:
        raw=(target/'public'/asset['url']).read_bytes()
        asset.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    budget=check_initial_model_budget(manifest['base']['bytes']+manifest['trees']['bytes'])
    (target/'public/data/models.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    for label,script,extra in [
        ('source-retention','validate_incremental_source.py',[f'--baseline-root={ROOT}','--update-kind=new-east-gate']),
        ('new-east-geometry','validate_new_east_gate.py',[])]:
        run_checked([bpy.app.binary_path,'-b','--factory-startup','--disable-autoexec','--python-exit-code','1',
                     '--python',str(target/'blender'/script),'--',*extra],target,label)
    run_checked([os.environ.get('NODE_BIN','node'),'--experimental-strip-types','--test','scripts/test-campus.mjs','scripts/test-sources.mjs',
                 'scripts/test-i18n.mjs','scripts/test-camera.mjs'],target,'catalog-and-assets')
    changed=[p for p,h in snapshot(target).items() if before.get(p)!=h]
    allowed={'blender/gxu-campus.blend','public/models/base.glb','public/models/new-east-gate.glb',
             'public/data/models.json','public/data/landmarks.json','public/data/sources.json'}
    # Repeated builds or catalogue-only updates can retain identical GLBs.
    # The checks above validate their contents; only the write scope matters here.
    assert set(changed)<=allowed,changed
    report={'passed':True,'changedFiles':changed,'retainedSourceObjects':len(unchanged),**budget}
    (target/'work/new-east-update.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if args.publish:publish(ROOT,target,before)
    print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
