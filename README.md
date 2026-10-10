<h1 align="center">广西大学 校园地图</h1>

<p align="center">
  <strong>简体中文</strong> · <a href="README.en.md">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Three.js-000000?style=flat&amp;logo=threedotjs&amp;logoColor=white" alt="Three.js">
  <img src="https://img.shields.io/badge/Blender-E87D0D?style=flat&amp;logo=blender&amp;logoColor=white" alt="Blender">
  <img src="https://img.shields.io/badge/React-20232A?style=flat&amp;logo=react&amp;logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat&amp;logo=typescript&amp;logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/OpenStreetMap-387C44?style=flat&amp;logo=openstreetmap&amp;logoColor=white" alt="OpenStreetMap">
</p>

<p align="center">
  广西大学大学东路主校区的三维校园地图。使用 Three.js 和 Blender 制作，基于 OpenStreetMap 与公开资料建模，可在浏览器中查找地点、查看建筑、游览校园和切换昼夜。
</p>

<p align="center">
  <a href="https://wcqqq1214.github.io/gxu-campus-3d/">在线游览</a>
</p>

![校园全景与按类别分组的地点列表](docs/screenshots/readme/overview.jpg)

## 功能

- 浏览 20 处精选地点，按教学、文体、校门、路桥和生活分组；搜索支持“六教”“新东园门”等别名，结果平铺显示。
- 列表与地图标注双向高亮，编号对应游览站号，便于在目录与场景之间定位。
- 地点详情展示简介、观察视角和分享入口；视角栏可横向滚动，提供全貌、俯视、环绕、正背面及近景，也可自由旋转、平移和缩放。
- 游览入口常驻面板底部，支持暂停、继续和跳站，并显示每站 8.5 秒的进度；收起面板后仍可暂停和继续。
- 选择晨光、日间、黄昏或夜景；自动画质会根据运行表现调整阴影、树木和近景细节。
- 独立开关校园建筑、树木、道路与桥梁、水体、运动场地、周边建筑、校园边界和地点名称。
- 通过“分享”菜单复制当前视角链接，或导出带 OpenStreetMap 署名的 PNG。
- 手机使用底部面板，支持简要、详情和收起；“更多工具”集中提供视角、分享和操作说明。支持键盘操作及系统“减少动态效果”偏好。

| 手机地点详情 | 手机工具菜单 |
| --- | --- |
| ![手机上的六教简要详情](docs/screenshots/readme/mobile-detail.jpg) | ![手机上的更多工具菜单](docs/screenshots/readme/mobile-tools.jpg) |

## 模型范围

| 校内建筑 | 周边建筑 | 精选地标 | 示意树木 |
| :---: | :---: | :---: | :---: |
| 446 栋／体块 | 13 栋 | 20 处 | 2,936 株 |

模型覆盖东、西、北校园，包含两处田径场、31 片室外篮球场，以及农院路和三座主要下穿桥梁。白线标示校园大致范围，农院路按公共道路表示。校外建筑仅保留距校界约 20 米以内的紧邻部分。

| 图书馆北侧 | 崇左桥下穿道路 |
| --- | --- |
| ![图书馆北侧与入口](docs/screenshots/readme/library-north.jpg) | ![崇左桥桥下道路与两侧步道](docs/screenshots/readme/chongzuo-bridge.jpg) |

![东田径场西侧的篮球场模型](docs/screenshots/readme/basketball-east.jpg)

截图更新于 2026-10-07，采自当前 `dev` 分支的本地开发版本（含最新详情页调整），可能领先于在线站点；手机图使用桌面浏览器的 390 × 844 视口采集。截图日期、版本与视角（本地开发记录）。

建筑轮廓主要来自 **2026-09-09 的 OpenStreetMap 快照**，道路与桥梁使用 2026-09-11 获取的补充数据。建筑外观参考不同年份的公开照片和资料，资料日期不等于当前实景。这是独立开源项目，未经过校园实地测绘。

334 条建筑记录仍沿用类型默认高度；另有楼栋按资料层数乘估算层高计算，不能视为实测。校内数量包括北校园新增的 11 个建筑与连廊体块，不能全部按独立楼栋理解。照片没有覆盖的立面、树位及部分设施布局也包含推定。篮球场中 16 片沿用地图定位，东区另有 15 片依据资料估算布置。具体依据与局限见 [数据说明](docs/DATA.md) 和 [逐项来源](public/data/sources.json)。

## 本地运行

使用 Node.js 24，与 CI 保持一致。

```sh
git clone https://github.com/wcqqq1214/gxu-campus-3d.git
cd gxu-campus-3d
npm ci
npm run dev
```

打开终端输出的 Local 地址。项目使用 React、TypeScript、vinext 和 Vite，网页运行不需要地图密钥或后端服务。

### 检查与静态构建

```sh
npm run typecheck
npm run lint
npm test
npm run build:pages
npm run preview
```

静态文件生成于 `out/`，默认预览地址为 `http://127.0.0.1:4300/gxu-campus-3d/`。请通过 HTTP 服务访问，不要直接打开 HTML 文件。

提交到 `main` 和面向 `main` 的 Pull Request 均执行检查与构建；只有主分支推送和手动运行会发布 Pages。

### 数据测试与模型重建

数据测试使用 Python 3.12：

```sh
python3.12 -m venv work/data-venv
source work/data-venv/bin/activate
python -m pip install -r scripts/requirements.txt -c scripts/constraints-geodata.txt
npm run test:data
```

Blender 可编辑源文件在本地保存为 `blender/gxu-campus.blend`，内含具名对象、材质和打包纹理，不再纳入 Git，目前尚未提供 Release 下载。运行网页与普通测试无需该文件；增量修改和源模型检查需要本地源文件及 Blender，步骤见 [建模说明](docs/MODELING.md)。[原始数据快照](data/snapshots/) 用于离线恢复，[网页模型](public/models/) 使用 Draco 压缩并按需加载。初始模型大小由资源清单和测试约束在 6 MB（十进制）以内，脚本、JSON 和解码器另计。

## 项目文档

- [数据来源与精度](docs/DATA.md)
- [模型结构与重建](docs/MODELING.md)
- [界面与交互](docs/DESIGN.md)

开发过程文档、验收报告和截图仅在本地保存，不随仓库分发；测试与校验依赖的基准数据及 README 展示图除外。

## 许可

代码采用 [MIT](LICENSE)，自制模型和材质采用 [CC BY 4.0](licenses/MODELS.md)。地理数据库及其衍生数据采用 ODbL，署名 **© OpenStreetMap contributors**。其他数据与字体的许可见 [第三方说明](licenses/THIRD_PARTY.md)。

官方照片和视频只用于造型参考，未作为网页贴图或仓库图片分发。
