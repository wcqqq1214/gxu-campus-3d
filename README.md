<div align="center">

# 西大 · 云游校园

**在浏览器里，走近广西大学。**

基于公开地理数据与 Blender 建模的三维校园，支持地标探索、自动巡游与昼夜切换。

[在线游览](https://wcqqq1214.github.io/gxu-campus-3d/) · [数据依据](docs/DATA.md) · [建模说明](docs/MODELING.md) · [体验优化](docs/OPTIMIZATION.md) · [验收记录](docs/VALIDATION.md)

![Three.js](https://img.shields.io/badge/Three.js-000000?style=for-the-badge&logo=threedotjs&logoColor=white)
![Blender](https://img.shields.io/badge/Blender-E87D0D?style=for-the-badge&logo=blender&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![OpenStreetMap](https://img.shields.io/badge/OpenStreetMap-387C44?style=for-the-badge&logo=openstreetmap&logoColor=white)

</div>

![广西大学三维校园全景，实际网页截图](docs/screenshots/overview.png)

## 一座可以探索的三维校园

项目复现广西大学大学东路主校区，覆盖东、西、北校园及周边道路环境；校外建筑仅保留距校界约 20 米以内的紧邻部分。以自然建筑配色、浓绿乔木与棕榈，呈现校园中的楼宇、湖塘、道路和运动场。打开网页即可游览，无需账号、地图密钥或后端服务。

| 校内建筑 | 周边建筑 | 精选地标 | 示意树木 |
| :---: | :---: | :---: | :---: |
| **435 栋** | **13 栋** | **20 处** | **3,034 株** |

> 基于 2026-09-09 07:57:13 UTC 的 OpenStreetMap 快照。建筑外观参考资料跨越不同年份；道路与桥梁采用 2026-09-11 获取的补充快照。快照日期不代表所有模型均反映该日实景。项目为独立开源作品，未经过校园实地测绘。

## 游览体验

| 功能 | 可以做什么 |
| --- | --- |
| **地标探索** | 按分类与“六教”“新东园门”等别名搜索，定位 20 处精选地标。 |
| **自动巡游** | 按地标顺序游览，支持暂停、继续和前后跳站；手动操作会暂停巡游。 |
| **自由视角** | 旋转、平移、缩放；地标可切换全貌、正背面、俯视、入口近景与环绕观察。 |
| **位置与分享** | 小图显示地标及镜头方向；分享链接还原镜头和光照，并适配不同屏幕。 |
| **光照与画质** | 选择晨光、日间、黄昏或夜景，搭配自动、精细、流畅画质。 |
| **图层控制** | 分别开关建筑、植被、道路与桥梁、水体、运动场、紧邻校界建筑、校园大致边界和名称标注。 |
| **截图与移动端** | 导出带 OSM 署名的 PNG；手机统一底部面板，桌面菜单可收起，镜头按可用画面自动构图。 |

精选地标涵盖南大门、图书馆、汇学堂、大礼堂、综合体育馆、大学生活动中心、第六教学楼、第二教学楼、综合实验大楼、计算机与电子信息学院、留学生公寓、新东门、东门、西门，以及崇左桥、博萃桥、荟贤桥、图书馆北侧的时光之门、第十教学楼及荟萃楼。普通建筑与七座无可靠名称资料的湖上桥梁参与场景展示，不进入搜索与巡游名单。

农院路按约 **2.17 千米公共道路**单独建模，保留与两侧校园的隔离关系；崇左桥、博萃桥、荟贤桥呈现农院路上跨、校道下穿的结构，桥上沥青与引道连续衔接，临街狭窄处按建筑轮廓渐变收窄估算路幅，并提供桥下近景。校内车道两侧建有独立抬高步道，步道与护栏连续穿过桥洞。近景包含围栏、路缘、盲道、路灯、坡道、挡墙、桥梁护栏和排水盖板。详细依据和照片覆盖范围见[农院路与桥梁研究及建模记录](docs/INFRASTRUCTURE.md)。

[查看荟萃楼精建](https://wcqqq1214.github.io/gxu-campus-3d/#place=huicui)：重建北侧通高柱廊、分层窗格、金属雨棚、字牌与门厅踏步，保留原有内院，加入第 20 处精选目录。[资料年代与建模说明](docs/HUICUI.md)。

![荟萃楼北立面，实际网页截图](docs/screenshots/huicui-north.png)

[查看西校园篮球场](https://wcqqq1214.github.io/gxu-campus-3d/#light=day&camera=-392,55,490,-420,3,375&span=46)：保留 19 片已有地图定位的独立球场，其中西校园集中区 16 片；另补东田径场西侧 15 片资料约束的估算球场；补齐禁区、三分线、中圈、篮板、篮圈及镂空篮网。

[查看东田径场旁篮球场](https://wcqqq1214.github.io/gxu-campus-3d/#light=day&camera=655,240,155,620,3,-120&span=108) · [位置与精度说明](docs/EAST_BASKETBALL.md)

![西校园篮球场，实际网页截图](docs/screenshots/basketball-west.png)

[查看六教北门](https://wcqqq1214.github.io/gxu-campus-3d/#place=teaching-six&view=rear-entrance&light=day)：补齐南北门厅、东西侧门及首层通道，保留三个内院。[入口核对记录](docs/MODELING.md#第六教学楼四向入口核对2026-09-11) · [网页效果](docs/screenshots/teaching-six-north.png)。

[直接游览第十教学楼](https://wcqqq1214.github.io/gxu-campus-3d/#place=teaching-ten)：第 19 处精选地标，支持“十教”“10教”搜索；按实际轮廓复原南侧弧形低楼、北侧八层教学翼及入口细节。照片日期与估算范围见[建模说明](docs/MODELING.md#第十教学楼2026-09-11)。

![第十教学楼，实际网页导出](docs/screenshots/teaching-ten.png)

[直接游览时光之门](https://wcqqq1214.github.io/gxu-campus-3d/#place=time-gate)：银色三足雕塑、褶皱金属与铭牌，支持雕塑近景；[参考依据与估算范围](docs/MODELING.md#时光之门2026-09-11)。

![时光之门，实际网页导出](docs/screenshots/time-gate.png)

![崇左桥桥下近景，实际网页导出](docs/screenshots/chongzuo-bridge.png)

<details>
<summary>查看更多场景预览</summary>

| 南大门 | 汇学堂 |
| --- | --- |
| ![南大门近景](docs/screenshots/south-gate-current.png) | ![汇学堂朝东入口](docs/screenshots/huixue-east.png) |

| 东田径场 | 西田径场 |
| --- | --- |
| ![东田径场](docs/screenshots/east-track.png) | ![西田径场](docs/screenshots/west-track.png) |

[查看移动端截图](docs/screenshots/mobile-optimized.png)

</details>

汇学堂正东侧保留无树草地；校内主路沿用桥下道路的沥青、浅色路缘与中心虚线，保持原路幅，小路与支路暂保留原样。崇左桥、博萃桥、荟贤桥下六处接口采用渐变路幅与步道收口，路口留出连续通道。范围与估算说明见[校内主路与草地](docs/CAMPUS_ROADS.md)。

校园外围地面道路采用连续路面、圆角交叉口和浅色路缘；灰绿色细线显示校园大致边界，在农院路两侧区分校园范围，可通过图层开关控制。

![校园大致边界，实际网页截图](docs/screenshots/campus-boundary.png)

## 技术与资源

| 技术 | 用途 |
| --- | --- |
| **Three.js** | 浏览器三维场景、相机交互和模型展示。 |
| **Blender** | 校园与地标建模，保留可编辑源文件。 |
| **React + TypeScript** | 游览菜单、搜索与交互状态。 |
| **vinext + Vite** | 本地开发与静态构建。 |
| **OpenStreetMap + DEM** | 建筑轮廓、道路、水体和地形的数据基础。 |
| **GLB + Draco** | 压缩模型资源，优先加载当前地标与附近区块。 |

- [Blender 源文件](blender/gxu-campus.blend)：米制尺寸、具名建筑、材质与集合，纹理已打包。
- [模型资源](public/models/)：校园基础模型、30 个普通建筑区块、16 个道路与跨水桥近景区块、20 处独立地标和树木模板。
- [场景数据](public/data/)：GeoJSON、建筑与地标目录、模型清单、来源记录和高程数据。
- [原始快照](data/snapshots/)：保留版本与编辑时间的 OSM 数据、DEM 瓦片及查询，支持离线恢复与重建。

## 本地运行

建议使用 **Node.js 24**，与仓库 CI 保持一致。

```sh
git clone https://github.com/wcqqq1214/gxu-campus-3d.git
cd gxu-campus-3d
npm ci
npm run dev
```

打开终端输出的 Local 地址。

### 检查与构建

```sh
npm run typecheck
npm run lint
npm test
npm run build:pages
npm run preview
```

构建产物生成于 `out/`，默认预览地址为 `http://127.0.0.1:4300/gxu-campus-3d/`。请通过 HTTP 服务访问，不要直接用 `file://` 打开文件。

数据准备与模型重建流程见 [建模说明](docs/MODELING.md)，来源与快照说明见 [数据依据](docs/DATA.md)。

## 数据来源与精度

模型以公开地理数据为基础，结合校方照片、视频及资料重建部分地标。近期核对采用 2024—2026 年校方资料；缺少近期外观时也引用更早的官方记录，资料获取时间不等于拍摄时间。

- **建筑高度**：370 栋按类型估算，部分地标参考照片估高；第二教学楼立面主要按类型推定。
- **外观细节**：照片未覆盖的立面、植物种类与树位包含推定。新东门外观暂为推定，东门参考含 2018 年实拍，西门参考照片拍摄日期未知。
- **覆盖范围**：北校园及周边以现有 OSM 数据为准，未绘制的位置没有虚构补建。
- **地形高程**：历史 DEM 经过湖岸与基底局部平整，不能作为工程高程依据。

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [数据依据](docs/DATA.md) | 地理数据、资料年份、来源与精度边界。 |
| [农院路与桥梁](docs/INFRASTRUCTURE.md) | 公共道路分隔、立交关系、近期资料与估算范围。 |
| [建模说明](docs/MODELING.md) | Blender 重建流程与地标建模依据。 |
| [界面说明](docs/DESIGN.md) | 菜单、交互与视觉设计。 |
| [验收记录](docs/VALIDATION.md) | 功能检查与验证结果。 |

## 许可与署名

| 内容 | 许可／署名 |
| --- | --- |
| 代码 | [MIT](LICENSE) |
| 自制模型与材质 | [CC BY 4.0](licenses/MODELS.md)，作者 `wcqqq1214` |
| 地理数据库及衍生数据库 | ODbL 1.0，**© OpenStreetMap contributors** |
| SRTM / Mapzen 等数据 | 见 [第三方说明](licenses/THIRD_PARTY.md) |

模型作为地理数据的可视化作品保留 OSM 署名，并提供对应数据库。官方照片与视频仅用于造型参考，未作为网页贴图或仓库图片再分发。
