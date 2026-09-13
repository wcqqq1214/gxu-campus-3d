import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import os from 'node:os';
import { createRequire } from 'node:module';
assert(process.argv[2], 'Usage: node scripts/check-export-attributes.mjs BEFORE_ROOT [REPORT_PATH]');
const beforeRoot=path.resolve(process.argv[2]);
const reportPath=process.argv[3]??'docs/model-checks/export-attributes.json';
const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'gxu-draco-'));
let draco;
try {
 const wrapper=path.join(temporary,'decoder.cjs');
 fs.copyFileSync('public/draco/draco_wasm_wrapper.js',wrapper);
 const factory=createRequire(import.meta.url)(wrapper);
 draco=await factory({wasmBinary:fs.readFileSync('public/draco/draco_decoder.wasm')});
} finally { fs.rmSync(temporary,{recursive:true,force:true}); }
function unpack(file){const raw=fs.readFileSync(file), n=raw.readUInt32LE(12);return {doc:JSON.parse(raw.subarray(20,20+n)),bin:raw.subarray(28+n),raw};}
const old=unpack(path.join(beforeRoot,'public/models/base.glb'));
const now=unpack('public/models/base.glb');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const lex=(a,b)=>a<b?-1:a>b?1:0;
const nodes=d=>Object.fromEntries(d.nodes.filter(n=>n.mesh!==undefined).map(n=>[n.name.replace(/\.\d{3,}$/,''),n]));
const oldNodes=nodes(old.doc),newNodes=nodes(now.doc);
assert.deepEqual(Object.keys(oldNodes).sort(),Object.keys(newNodes).sort());
assert.deepEqual(old.doc.materials,now.doc.materials);
assert.deepEqual(old.doc.textures,now.doc.textures);
assert.deepEqual(old.doc.samplers,now.doc.samplers);
assert.deepEqual(old.doc.scenes,now.doc.scenes);
assert.equal(old.doc.scene,now.doc.scene);
assert.equal(old.doc.nodes.length,now.doc.nodes.length);
function payload(asset,index){const v=asset.doc.bufferViews[index];return asset.bin.subarray(v.byteOffset??0,(v.byteOffset??0)+v.byteLength);}
assert.equal(old.doc.images.length,now.doc.images.length);
for(let i=0;i<old.doc.images.length;i++){
  const {bufferView:a,...x}=old.doc.images[i],{bufferView:b,...y}=now.doc.images[i];
  assert.deepEqual(x,y);assert.deepEqual(payload(old,a),payload(now,b));
}
function decodedTriangles(asset,p,attributes){
 const ext=p.extensions.KHR_draco_mesh_compression, raw=payload(asset,ext.bufferView);
 const decoder=new draco.Decoder(),buffer=new draco.DecoderBuffer(),mesh=new draco.Mesh();
 buffer.Init(new Int8Array(raw),raw.length);
 const status=decoder.DecodeBufferToMesh(buffer,mesh);assert(status.ok(),status.error_msg());
 const arrays=attributes.map(name=>{
  const attribute=decoder.GetAttributeByUniqueId(mesh,ext.attributes[name]);assert(attribute?.ptr);
  const count=attribute.num_components(), values=new draco.DracoFloat32Array();
  assert(decoder.GetAttributeFloatForAllPoints(mesh,attribute,values));
  const data=new Float32Array(mesh.num_points()*count);
  for(let j=0;j<data.length;j++)data[j]=values.GetValue(j);
  draco.destroy(values);return {data,count};
 });
 const width=arrays.reduce((n,a)=>n+a.count*4,0),corners=[];
 for(let i=0;i<mesh.num_points();i++){
  const value=Buffer.alloc(width);let offset=0;
  for(const a of arrays)for(let j=0;j<a.count;j++){const f=a.data[i*a.count+j];value.writeFloatLE(f===0?0:f,offset);offset+=4;}
  corners.push(value.toString('hex'));
 }
 const face=new draco.DracoInt32Array(),triangles=[];
 for(let i=0;i<mesh.num_faces();i++){
  assert(decoder.GetFaceFromMesh(mesh,i,face));
  const a=corners[face.GetValue(0)],b=corners[face.GetValue(1)],c=corners[face.GetValue(2)];
  triangles.push([a+b+c,b+c+a,c+a+b].sort(lex)[0]);
 }
 const counts={points:mesh.num_points(),triangles:mesh.num_faces()};
 for(const name of attributes)assert.equal(asset.doc.accessors[p.attributes[name]].count,counts.points);
 assert.equal(asset.doc.accessors[p.indices].count,counts.triangles*3);
 draco.destroy(face);draco.destroy(mesh);draco.destroy(buffer);draco.destroy(decoder);
 triangles.sort(lex);return {...counts,hash:sha(triangles.join('\n'))};
}
const report={nodes:[],changedPrimitives:0,preservedPrimitivePayloads:0,removedUVVertices:0,passed:false};
for(const [name,node] of Object.entries(oldNodes)){
 const other=newNodes[name];
 const {mesh:a,...oldProps}=node,{mesh:b,...newProps}=other;
 assert.deepEqual(newProps,oldProps,name+' node');
 const before=old.doc.meshes[a].primitives,after=now.doc.meshes[b].primitives;
 assert.equal(before.length,after.length,name);
 let changed=0;
 for(let i=0;i<before.length;i++){
  const p=before[i],q=after[i];assert.equal(p.material,q.material,name);
  const oldKeys=Object.keys(p.attributes).sort(),newKeys=Object.keys(q.attributes).sort();
  const removed=oldKeys.filter(k=>!newKeys.includes(k));
  assert(newKeys.every(k=>oldKeys.includes(k)));assert(removed.every(k=>k.startsWith('TEXCOORD_')));
  const pb=payload(old,p.extensions.KHR_draco_mesh_compression.bufferView),qb=payload(now,q.extensions.KHR_draco_mesh_compression.bufferView);
  assert.equal(p.mode,q.mode);assert.deepEqual(p.targets,q.targets);assert.deepEqual(p.extras,q.extras);
  if(pb.equals(qb)){
   assert.deepEqual(newKeys,oldKeys);
   for(const name of oldKeys)assert.deepEqual(old.doc.accessors[p.attributes[name]],now.doc.accessors[q.attributes[name]]);
   assert.deepEqual(old.doc.accessors[p.indices],now.doc.accessors[q.indices]);
   report.preservedPrimitivePayloads++;continue;
  }
  assert(removed.length>0,name+' changed a primitive without omitting UVs');
  const material=now.doc.materials[q.material];
  assert(!JSON.stringify(material).includes('Texture'),name+' textured material');
  assert(!material.extensions || !Object.keys(material.extensions).length,name+' material extension');
  const x=decodedTriangles(old,p,newKeys),y=decodedTriangles(now,q,newKeys);
  assert.equal(y.triangles,x.triangles,name+' triangle count');
  assert.equal(y.hash,x.hash,name+' exact oriented triangle corners ('+newKeys.join(',')+')');
  report.removedUVVertices+=old.doc.accessors[p.attributes[removed[0]]].count;
  report.changedPrimitives++;changed++;
 }
 report.nodes.push({name,changedPrimitives:changed,primitives:before.length});
}
report.passed=true;report.scope='Exact decoded oriented triangle multiset for every changed primitive, including positions and normals; unchanged primitive payloads, images/materials/node transforms are byte/metadata preserved. Only unused UV streams omitted.';
report.previousBaseSha256=sha(old.raw);report.currentBaseSha256=sha(now.raw);
report.savedBytes=old.raw.length-now.raw.length;
fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({...report,nodes:report.nodes.length},null,2));
