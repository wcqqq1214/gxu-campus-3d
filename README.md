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
  广西大学大学东路主校区三维地图，使用 Three.js 和 Blender，基于 OpenStreetMap 与公开资料建模。
</p>

<p align="center">
  <a href="https://wcqqq1214.github.io/gxu-campus-3d/">在线游览</a>
</p>

![校园全景与按类别分组的地点列表](docs/screenshots/readme/overview.jpg)

## 功能

- 搜索 20 处精选地点及约 300 栋有名称的校内建筑，切换建筑观察视角，跟随校园游览路线。
- 晨光、日间、黄昏、夜景四种光影，支持图层开关与自动／手动画质。
- 分享当前视角链接，或导出带 OpenStreetMap 署名的 PNG。
- 适配手机，支持键盘操作及系统“减少动态效果”偏好。

<details>
<summary>更多截图：光影、近景与手机界面</summary>

| 晨光 | 日间 |
| --- | --- |
| ![晨光下的图书馆](docs/screenshots/readme/library-morning.jpg) | ![日间的图书馆](docs/screenshots/readme/library-day.jpg) |
| 黄昏 | 夜景 |
| ![黄昏下的图书馆](docs/screenshots/readme/library-evening.jpg) | ![夜景中的图书馆](docs/screenshots/readme/library-night.jpg) |
| 图书馆北侧 | 崇左桥下穿道路 |
| ![图书馆北侧与入口](docs/screenshots/readme/library-north.jpg) | ![崇左桥桥下道路](docs/screenshots/readme/chongzuo-bridge.jpg) |
| 手机地点详情 | 手机工具菜单 |
| ![手机上的六教详情](docs/screenshots/readme/mobile-detail.jpg) | ![手机上的工具菜单](docs/screenshots/readme/mobile-tools.jpg) |

![东田径场西侧篮球场](docs/screenshots/readme/basketball-east.jpg)

</details>

截图：2026-10-12，`dev` 本地静态构建、自动画质；手机为浏览器模拟，可能与在线站点不同。

## 模型范围

覆盖东、西、北校园，含校内 446 栋建筑／体块、周边 13 栋建筑及 2,936 株示意树木。未经实地测绘，部分高度、立面和设施布局为估算，详见 [数据说明](docs/DATA.md)。

## 本地运行

使用 Node.js 24，无需地图密钥或后端服务。

```sh
git clone --branch dev https://github.com/wcqqq1214/gxu-campus-3d.git
cd gxu-campus-3d
npm ci
npm run dev
```

打开终端输出的 Local 地址。检查与静态构建：

```sh
npm run typecheck
npm run lint
npm test
npm run build:pages
npm run preview
```

静态文件生成于 `out/`，预览地址为 `http://127.0.0.1:4300/gxu-campus-3d/`。开发提交推送至 `origin/dev`；更新 `main` 需明确授权。

## 文档与许可

- [数据来源与精度](docs/DATA.md)
- [模型结构、数据测试与重建](docs/MODELING.md)（Blender 源文件未分发，运行网页无需该文件）
- [界面与交互](docs/DESIGN.md)

原创代码、文档、模型、材质及渲染图采用 [MIT](LICENSE)；OpenStreetMap 地理数据库及衍生数据采用 ODbL，署名 **© OpenStreetMap contributors**。其他资源见 [第三方说明](licenses/THIRD_PARTY.md)。官方照片和视频仅供建模参考，不随仓库分发。
