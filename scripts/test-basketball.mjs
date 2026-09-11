import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const read=(n)=>JSON.parse(fs.readFileSync(new URL('../public/data/'+n,import.meta.url)));
const data=read('basketball.json');
test('篮球场使用独立运动场节点，保持精选目录稳定且来源可查询',()=>{
  const bytes=fs.readFileSync(new URL('../public/models/base.glb',import.meta.url));
  const size=bytes.readUInt32LE(12);const gltf=JSON.parse(bytes.subarray(20,20+size).toString());
  for(const bank of data.banks){
    const roots=gltf.nodes.filter(n=>n.name===bank.id);
    assert.equal(roots.length,1);assert.equal(roots[0].extras.layer,'sports');
  }
  assert.ok(!read('landmarks.json').some(l=>l.id.startsWith('basketball-')));
  assert.equal(new Set(data.courts.filter(c=>c.osmId).map(c=>c.osmId)).size,19);
  const sources=new Set(read('sources.json').sources.map(s=>s.id));
  for(const id of data.sourceRefs)assert.ok(sources.has(id),id);
  assert.equal(read('overview.json').trees,read('vegetation.json').length);
});
