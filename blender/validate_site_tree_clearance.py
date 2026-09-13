"""Check saved and shipped roads/water/sports geometry against actual trees.

Read-only: imports into a disposable Blender process; never saves source/models.
Includes all infrastructure and landmark GLBs, not just the ordinary chunks.
"""
import bpy,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'blender'))
from tree_mesh_audit import snapshot,check_meshes
LAYERS={'roads','water','sports'}
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
prefix=next((a.split('=',1)[1] for a in args if a.startswith('--report-prefix=')),'s4-site-trees')
if not prefix or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in prefix):
    raise ValueError('Invalid report prefix')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=json.loads((ROOT/'public/data/vegetation.json').read_text())
manifest=json.loads((ROOT/'public/data/models.json').read_text())
fingerprints={'source':sha(ROOT/'blender/gxu-campus.blend'),
              'trees':sha(ROOT/'public/data/vegetation.json'),
              'manifest':sha(ROOT/'public/data/models.json')}


def collect(asset):
    meshes=[];inventory=[]
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or obj.get('layer') not in LAYERS or not obj.data.polygons:continue
        key=asset+'/'+obj.name
        meshes.append((key,snapshot(obj)))
        inventory.append({'key':key,'layer':obj.get('layer'),
                          'vertices':len(obj.data.vertices),'polygons':len(obj.data.polygons)})
    return meshes,inventory


def label(report):
    # The legacy building validator retains its historical field names;
    # this caller reports generic site meshes without calling them buildings.
    report['siteMeshes']=report.pop('buildingMeshes')
    report['testedClosedSiteComponents']=report.pop('testedClosedBuildingComponents')
    report['testedOpenSiteComponents']=report.pop('testedOpenBuildingComponents')
    for hit in report['collisions']:
        hit['siteMesh']=hit.pop('buildingMesh')
        hit['collisionKind']=hit['collisionKind'].replace('building','site')
    return report


bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
source_meshes,source_inventory=collect('source')
source_templates={o['template']:snapshot(o) for o in bpy.context.scene.objects
                  if o.type=='MESH' and o.get('template') is not None}
assert set(source_templates)=={0,1,2}
print('Source inventory',len(source_meshes),flush=True)
source=label(check_meshes(rows,source_meshes,{'near':source_templates}))
print('Source result',len(source['collisions']),'collisions;',source['testedPairs'],'pairs',flush=True)
del source_meshes
bpy.ops.wm.read_factory_settings(use_empty=True)
templates={};asset_hashes={}
for key,lod in [('trees','base'),('treesNear','near')]:
    asset_hashes[manifest[key]['url']]=sha(ROOT/'public'/manifest[key]['url'])
    assert asset_hashes[manifest[key]['url']]==manifest[key]['sha256']
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'public'/manifest[key]['url']))
    templates[lod]={o['template']:snapshot(o) for o in bpy.context.scene.objects
                    if o.type=='MESH' and o.get('template') is not None}
    assert set(templates[lod])=={0,1,2}
    bpy.ops.wm.read_factory_settings(use_empty=True)
meshes=[];inventory=[]
assets=[manifest['base']]+manifest['zones']+manifest['landmarks']+manifest['infrastructure']
for asset in assets:
    path=ROOT/'public'/asset['url']
    asset_hashes[asset['url']]=sha(path)
    assert asset_hashes[asset['url']]==asset['sha256']
    bpy.ops.import_scene.gltf(filepath=str(path))
    loaded,records=collect(asset['url']);meshes.extend(loaded);inventory.extend(records)
    bpy.ops.wm.read_factory_settings(use_empty=True)
print('Shipping inventory',len(meshes),flush=True)
shipping=label(check_meshes(rows,meshes,templates))
print('Shipping result',len(shipping['collisions']),'collisions;',shipping['testedPairs'],'pairs',flush=True)
assert fingerprints=={'source':sha(ROOT/'blender/gxu-campus.blend'),'trees':sha(ROOT/'public/data/vegetation.json'),
                      'manifest':sha(ROOT/'public/data/models.json')}
assert all(sha(ROOT/'public'/name)==digest for name,digest in asset_hashes.items())
report={'layers':sorted(LAYERS),'fingerprints':fingerprints,'assetsSha256':asset_hashes,
        'source':source,'shipping':shipping,'sourceInventory':source_inventory,'shippingInventory':inventory,
        'passed':source['passed'] and shipping['passed'],
        'scope':'Actual saved and decoded roads, water, sports, site surfaces and all infrastructure/bridge assets; surface intersections and detected closed-component containment, both shipping tree LODs.',
        'limitations':['Open surfaces are not capped; this does not prove an arbitrary solid volume below a road or above a sport court.',
                       'No regulatory headroom/setback or unsurveyed canopy envelope is imposed. Intended clearance and sourced planting layouts remain separate.',
                       'Shares the mesh audit and shell primitive with the existing building audit; asset collection and labels are specific to this scope.'],
        'implementationSha256':{p:sha(ROOT/'blender'/p) for p in ['tree_mesh_audit.py','mesh_volumes.py','validate_site_tree_clearance.py']}}
target=ROOT/'docs/model-checks/refinement'/f'{prefix}-geometry.json'
target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert report['passed'],f"Site/tree crossings: source {len(source['collisions'])}, shipping {len(shipping['collisions'])}"
