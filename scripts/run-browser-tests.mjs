import { spawn } from 'node:child_process';
import { openSync, closeSync } from 'node:fs';
import { mkdir, mkdtemp, readFile } from 'node:fs/promises';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';

const root = fileURLToPath(new URL('../', import.meta.url));
process.chdir(root);
const args = process.argv.slice(2);
if (args.some((arg) => arg !== '--skip-build'))
  throw new Error('仅支持 --skip-build（使用刚生成的 out/）');
const basePath = process.env.PAGES_BASE_PATH ?? '/gxu-campus-3d';
if (!['', '/gxu-campus-3d'].includes(basePath))
  throw new Error('浏览器检查的静态预览支持根路径或 /gxu-campus-3d');
const port = (name, fallback) => {
  const value = Number(process.env[name] ?? fallback);
  if (!Number.isInteger(value) || value < 1 || value > 65535)
    throw new Error(`无效端口：${name}`);
  return value;
};
const devPort = port('BROWSER_DEV_PORT', 4317);
const previewPort = port('BROWSER_PREVIEW_PORT', 4318);
if (devPort === previewPort) throw new Error('开发与预览端口不能相同');
await mkdir('work/browser-checks', { recursive: true });
const output = await mkdtemp(path.join(root, 'work/browser-checks/run-'));
console.log(`浏览器检查产物：${output}`);
const processes = [];
let interrupted = false;
let interruptTimer;

function signal(child, name) {
  if (!child.pid) return;
  try {
    process.kill(-child.pid, name);
  } catch (error) {
    if (error.code !== 'ESRCH') throw error;
  }
}
function start(name, commandArgs, env = {}) {
  if (interrupted) throw new Error('浏览器检查已中断');
  const logfile = path.join(output, `${name}.log`);
  const fd = openSync(logfile, 'wx');
  let child;
  try {
    child = spawn(process.execPath, commandArgs, {
      cwd: root,
      env: { ...process.env, ...env },
      detached: true,
      stdio: ['ignore', fd, fd],
    });
  } finally {
    closeSync(fd);
  }
  const task = { child, finished: false };
  task.done = new Promise((resolve, reject) => {
    child.once('error', (error) => {
      task.finished = true;
      reject(error);
    });
    child.once('exit', (code, exitSignal) => {
      task.finished = true;
      if (code === 0) resolve();
      else
        reject(
          new Error(`${name} 失败 (${code ?? exitSignal})；日志：${logfile}`),
        );
    });
  });
  task.done.catch(() => {}); // A server may exit while a check is still running.
  processes.push(task);
  return task;
}
async function stop(task) {
  if (task.stopped) return;
  task.stopped = true;
  signal(task.child, 'SIGTERM');
  const timer = setTimeout(() => signal(task.child, 'SIGKILL'), 5000);
  try {
    await task.done.catch(() => {});
  } finally {
    clearTimeout(timer);
    // Also reap any browser or server descendants whose parent already exited.
    signal(task.child, 'SIGKILL');
  }
}
function interrupt() {
  if (interrupted) return;
  interrupted = true;
  for (const task of processes)
    if (!task.stopped) signal(task.child, 'SIGTERM');
  interruptTimer = setTimeout(() => {
    for (const task of processes)
      if (!task.stopped) signal(task.child, 'SIGKILL');
  }, 5000);
}
process.on('SIGINT', interrupt);
process.on('SIGTERM', interrupt);
async function requireFreePort(value) {
  const server = net.createServer();
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(value, '127.0.0.1', resolve);
  });
  await new Promise((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  );
}
async function ready(task, url) {
  const deadline = Date.now() + 120000;
  while (Date.now() < deadline) {
    if (interrupted) throw new Error('浏览器检查已中断');
    if (task.finished) {
      await task.done;
      throw new Error(`服务提前退出：${url}`);
    }
    try {
      const response = await fetch(url, {
        signal: AbortSignal.timeout(
          Math.max(1, Math.min(30000, deadline - Date.now())),
        ),
      });
      await response.arrayBuffer();
      if (response.ok && !task.finished) return;
    } catch {
      /* The server is still starting. */
    }
    await delay(250);
  }
  throw new Error(`服务启动超时：${url}`);
}
async function check(name, script, env, server) {
  console.log(`浏览器回归：${name}`);
  const task = start(name, [script], {
    ...env,
    BROWSER_REPORT_DIR: path.join(output, name),
  });
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(
      () => reject(new Error(`${name} 检查超过 10 分钟`)),
      600000,
    );
  });
  try {
    await Promise.race([
      task.done,
      timeout,
      server.done.then(() => {
        throw new Error(`${name} 检查期间服务退出`);
      }),
    ]);
    console.log(`通过：${name}`);
  } finally {
    clearTimeout(timer);
    await stop(task);
  }
}
try {
  await requireFreePort(devPort);
  await requireFreePort(previewPort);
  if (!args.includes('--skip-build'))
    await start('build', ['scripts/build-pages.mjs'], {
      PAGES_BASE_PATH: basePath,
    }).done;
  const html = await readFile('out/index.html', 'utf8');
  if (!html.includes(`"${basePath}/_next/static/`))
    throw new Error('out/ 的资源前缀与 PAGES_BASE_PATH 不匹配，请重新构建');
  const dev = start(
    'dev-server',
    [
      'node_modules/vite/bin/vite.js',
      '--host',
      '127.0.0.1',
      '--port',
      String(devPort),
      '--strictPort',
    ],
    {
      NEXT_PUBLIC_BASE_PATH: '',
      NEXT_PUBLIC_DATA_VERSION: '',
      NODE_ENV: 'development',
    },
  );
  const devUrl = `http://127.0.0.1:${devPort}/`;
  await ready(dev, `${devUrl}@vite/client`);
  await check(
    'menu',
    'scripts/check-menu-interactions-browser.mjs',
    { MENU_TEST_URL: devUrl },
    dev,
  );
  await check(
    'camera',
    'scripts/check-panel-camera-browser.mjs',
    { PANEL_TEST_URL: devUrl },
    dev,
  );
  await stop(dev);
  const preview = start('preview-server', ['scripts/preview.mjs'], {
    PORT: String(previewPort),
  });
  const previewUrl = `http://127.0.0.1:${previewPort}${basePath}/`;
  await ready(preview, previewUrl);
  await check(
    'i18n',
    'scripts/check-i18n-browser.mjs',
    { I18N_URL: previewUrl },
    preview,
  );
  console.log(`三项浏览器回归通过；产物：${output}`);
} finally {
  await Promise.all(processes.map(stop));
  clearTimeout(interruptTimer);
  process.off('SIGINT', interrupt);
  process.off('SIGTERM', interrupt);
}
