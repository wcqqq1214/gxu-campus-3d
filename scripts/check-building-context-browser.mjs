/* Comparable ordinary-building views using current or archived public assets.
 * Historical assets are fulfilled from a saved local root; frontend is unchanged.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root=fileURLToPath(new URL('../',import.meta.url));
const phase=process.argv[2];
if (!phase || !/^[a-z0-9-]+$/.test(phase)) throw new Error('A recording phase is required');
const cameraFile=process.env.REFINEMENT_CAMERAS;
const beforeRoot=process.env.BEFORE_ASSETS_ROOT;
const mobileOnly=process.argv.includes('--mobile-only');
if (!cameraFile || !beforeRoot) throw new Error('Provide cameras and archived public asset root');
const cameras=JSON.parse(await fs.readFile(path.resolve(root,cameraFile),'utf8'));
// Match share.ts preconditions so a rejected pose cannot silently capture the overview.
for(const camera of cameras)for(const pose of [camera,...(camera.mobile?[{...camera,...camera.mobile}]:[])]){
  const p=pose.position,t=pose.target;
  if(!Array.isArray(p)||!Array.isArray(t)||p.length!==3||t.length!==3||
     ![...p,...t,pose.span].every(Number.isFinite)||p.some(v=>Math.abs(v)>=25000)||
     t.some(v=>Math.abs(v)>=6000)||p[1]<=t[1]||
     Math.hypot(...p.map((v,i)=>v-t[i]))<18||pose.span<1||pose.span>10000)
    throw new Error(`Invalid shared camera pose: ${camera.id}`);
}
const target=path.join(root,'docs/model-checks/refinement',`${phase}-context-browser.json`);
try { await fs.access(target); throw new Error('Recording already exists'); } catch(e) { if(e.code!=='ENOENT') throw e; }
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});
const report={capturedAt:new Date().toISOString(),method:'UI layer controls; same frontend; before public assets served by local Playwright route fulfillment. Tree-hidden images inspect building geometry only.',states:[],errors:[],completed:false};
const base=process.env.REFINEMENT_URL || 'http://127.0.0.1:4300/gxu-campus-3d/';
try {
  for (const variant of mobileOnly?['after']:['before','after']) {
    const assets=path.resolve(root,variant==='before'?beforeRoot:'public');
    const manifestBytes=await fs.readFile(path.join(assets,'data/models.json'));
    const manifest=JSON.parse(manifestBytes);
    const context=await browser.newContext({viewport:{width:1280,height:720},deviceScaleFactor:1});
    if(variant==='before') await context.route(/\/(data|models)\//,async route=>{
      const pathname=new URL(route.request().url()).pathname.replace(/^\/gxu-campus-3d\//,'');
      const file=path.resolve(assets,pathname);
      if(!file.startsWith(assets+path.sep)) throw new Error('Asset escaped saved root');
      await route.fulfill({body:await fs.readFile(file),contentType:pathname.endsWith('.json')||pathname.endsWith('.geojson')?'application/json':'application/octet-stream'});
    });
    const page=await context.newPage();
    page.on('pageerror',e=>report.errors.push(String(e)));
    page.on('console',m=>{if(m.type()==='error')report.errors.push(m.text());});
    page.on('response',r=>{if(r.status()>=400)report.errors.push(`${r.status()} ${r.url()}`);});
    async function settle() {
      await page.waitForFunction(()=>{const t=document.querySelector('.debug-metrics')?.textContent;if(!t)return false;const m=JSON.parse(t);return m.readyMs>0&&m.queuedDetails===0;},undefined,{timeout:90000});
      await page.waitForTimeout(1800);
    }
    async function capture(camera,trees,light='day',mobile=false) {
      // Use an explicitly reviewed portrait angle where foreground buildings
      // would hide the entrance from the wider desktop camera direction.
      if(mobile&&camera.mobile)camera={...camera,...camera.mobile};
      await page.setViewportSize(mobile?{width:390,height:844}:{width:1280,height:720});
      const hash=new URLSearchParams({camera:[...camera.position,...camera.target].join(','),span:camera.span,light});
      const name=`${camera.id}-${trees?'trees-on':'trees-off'}-${light}${mobile?'-mobile':''}`;
      await page.goto(`${base}?debug&building-check=${variant}-${name}#${hash}`);await settle();
      await page.getByRole('tab',{name:'图层',exact:true}).click();
      for(const [name,enabled] of [['林木植被',trees],['地点名称',false]]){
        const control=page.getByRole('switch',{name:new RegExp(`^${name}`)});
        if((await control.getAttribute('aria-checked'))!==String(enabled))await control.click();
      }
      await page.getByRole('tab',{name:'探索',exact:true}).click();await settle();
      const metrics=JSON.parse(await page.locator('.debug-metrics').textContent());
      const b=JSON.parse(await fs.readFile(path.join(assets,'data/buildings.json'),'utf8')).find(b=>b.id===camera.buildingId);
      // Compact viewports may legitimately keep an ordinary building in base
      // representation under the existing detail budget.
      const representation=metrics.loadedDetails.includes(b.chunk)?'near':'base';
      if(!mobile&&representation!=='near')throw new Error(`Ordinary near chunk absent: ${b.chunk}`);
      const folder=path.join(root,'docs/screenshots/refinement',phase,variant);await fs.mkdir(folder,{recursive:true});
      await page.screenshot({path:path.join(folder,`${name}.png`),style:'.debug-metrics{visibility:hidden!important}'});
      report.states.push({variant,file:path.relative(root,path.join(folder,`${name}.png`)),camera,trees,light,mobile,representation,viewport:page.viewportSize(),metrics,manifestSha256:createHash('sha256').update(manifestBytes).digest('hex'),baseModelSha256:manifest.base.sha256});
      await fs.writeFile(target,JSON.stringify(report,null,2)+'\n');console.log(`Captured ${variant}/${name}`);
    }
    if(!mobileOnly)for(const camera of cameras)await capture(camera,false);
    if(variant==='after'){
      if(!mobileOnly){
        await capture(cameras[1],true);
        await capture(cameras[0],false,'night');
      }
      await capture(cameras[0],false,'day',true);
    }
    await context.close();
  }
  if(report.errors.length)throw new Error(JSON.stringify(report.errors));
  report.completed=true;
} catch(error){report.failure=String(error);throw error;}
finally{await fs.writeFile(target,JSON.stringify(report,null,2)+'\n');await browser.close();}
