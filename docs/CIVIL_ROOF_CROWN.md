# 土木学院东南玻璃塔头与白色屋顶墙片

2026-09-20，接续附楼台阶，将 `relation/12875606` 东南玻璃体量从原统一屋面中抬出，并补入其东侧后方更高的白色屋顶墙片。原主楼屋面26.4米、低附楼10.8米及主体层数保持；塔头按屋顶构件表达，不据此增加楼层。本批仍为局部校准，不计整栋完成。

## 照片依据与取舍

[学院域名完整正面图](https://tmjz.gxu.edu.cn/__local/A/7E/69/4A06C7C98FB4DD485911A8F3606_2806A0A4_AFCA6.jpg)能直接辨认玻璃塔头高于主楼檐口，以及玻璃后方更高的白色墙片。[英文官网宽幅](https://tmjz-en.gxu.edu.cn/images/banner_six.jpg)裁掉塔顶，只用于核对既定玻璃转角和学院楼身份，不用于单独确定塔高。两张照片拍摄日期均未知，原图仅保存在本机作为参考。

沿用已定位的东南转角（原外环顶点17），两边分别跟随南立面和东立面方向。塔头宽度和进深由现有玻璃边界及原实体屋面约束；白墙采用后缘上收的简化轮廓。照片支持相对高低关系，不能提供精确尺寸、内部空间或楼层数。附楼的三角形墙面也不足以证明完整双坡屋顶，本批不据此设置坡屋面。

| 构件 | 本批参数 | 依据口径 |
| --- | --- | --- |
| 塔头实体 | 宽15.35米、进深3.8米；屋面32.4米 | 较原主楼屋面高6米，照片约束估算 |
| 延伸玻璃 | 26.0–32.2米；正面六列、东侧两列，四行 | 延续原幕墙边界，分格简化估算 |
| 东侧白色墙片 | 顶34.8米、厚0.35米 | 较主屋面高8.4米，非实测 |
| 墙片后缘 | 屋面处深8米，上缘深6.2米 | 上收斜率与厚度均为展示估算 |

本批只还原屋面以上的白墙。屋面以下贯穿塔身的完整斜侧墙、侧门厅、附楼分级屋顶及其他立面继续核对；不把当前屋顶墙片描述为完整斜墙已经完成。详细参数、参考文件哈希和未知项见[证据记录](model-checks/refinement/s2-civil-crown-evidence.json)。

## 数据与生成

新增 `roofCrown` 显式覆盖，要求锚定近似直角的原轮廓凸角、依附单个实体平屋面，完整构件占地必须在该体块内。拒绝越界、侵入内院、错误高度、过密玻璃分格和与其他屋顶专项叠加。原占地、内院和主体分段保持。

基础与近景共用塔头实体、玻璃和墙片几何。仅裁去被新构件覆盖的原屋顶女儿墙，保留其他屋缘；避免旧女儿墙横穿新玻璃。旋转测试曾暴露接触多边形并集因浮点误差分裂的问题，改为直接构造闭合边界后通过，不使用扩大实体或放宽院落约束来绕过。

## 验收范围

专项验证直接检查源文件和实际导出模型的玻璃、框线、接缝、塔头屋面、白墙高度、斜后缘和范围外留空。原无塔头版本作为反例，须在新增玻璃位置失败。既有幕墙回归保留26米以下的检查；原26.2米实体屋缘两处探针改由本批玻璃接缝验证覆盖，未将预期变更误称为原几何保持。

通用建筑验证同时检查支撑屋面、塔头屋面和白墙上缘。原主门厅、附楼台阶、凹窗、南立面窗带、主楼/附楼及其他建筑与树木继续按原范围回归。性能仍对照同系统原S0预算，不修改门槛。

196项Python测试、56项Node测试、类型检查、lint和Pages构建通过。[塔头专项](model-checks/refinement/s2-civil-crown-geometry.json)在源文件、基础GLB和近景GLB各核对92处，[旧模型反例](model-checks/refinement/s2-civil-crown-negative-geometry.json)如预期失败。原幕墙下段每级220处、外台阶每级101处及其余既有专项回归通过；430栋普通建筑、3063棵树和道路碰撞检查通过。

[源文件比对](model-checks/refinement/s2-civil-crown-source-preservation.json)确认只有土木学院对象变化，其他530个非树对象及树实例保持。[资产检查](model-checks/refinement/s2-civil-crown-assets.json)确认69个GLB与Pages产物一致，仅基础模型与所在近景块改变；首屏5,175,976字节，较本批前增加1,112字节，最大普通近景块1,684,868字节。

| 画面 | 对照 |
| --- | --- |
| 玻璃塔头与主楼 | [改前](screenshots/refinement/s2-civil-crown-visible/before/civil-crown-trees-off-day.png) / [改后](screenshots/refinement/s2-civil-crown-visible/after/civil-crown-trees-off-day.png) |
| 南侧全貌 | [改前](screenshots/refinement/s2-civil-crown-visible/before/civil-south-overview-trees-off-day.png) / [改后](screenshots/refinement/s2-civil-crown-visible/after/civil-south-overview-trees-off-day.png) |
| 树木与夜景 | [树木开启](screenshots/refinement/s2-civil-crown-visible/after/civil-south-overview-trees-on-day.png) / [夜景](screenshots/refinement/s2-civil-crown-visible/after/civil-crown-trees-off-night.png) |
| 手机尺寸 | [桌面竖屏模拟](screenshots/refinement/s2-civil-crown-visible/after/civil-crown-trees-off-day-mobile.png)，非实体设备测试 |

七张最终建筑画面已逐张检查。抬高玻璃塔头及更高白墙在前后对照中可见，原玻璃接缝未被旧女儿墙穿出，门厅、窗带和附楼台阶保留。该视角不能证明未实现的完整斜侧墙或附楼屋顶已还原，待办范围保持。

## 性能与本批结论

2026-09-21完成[联合验收](model-checks/refinement/s2-civil-crown-summary.json)。三次LOD往返、精细与流畅两档各三次30秒采样完成，浏览器无错误；精细档60/60/60 FPS，流畅档29/29/29 FPS。相对原同系统S0，帧率变化为0%/−3.33%，三角形增加3.65%/8.44%，绘制调用增加2.38%/11.03%，均符合原预算。

24次CPU快照未在计时窗口捕获超过2%阈值的Python或Blender进程；这是10秒间隔采样的有限结论。图书馆入口竖屏回归画面已核看，见[画面记录](model-checks/refinement/s2-civil-crown-visual-review.json)。本批屋顶塔头局部通过，累计仍为21条部分对象记录、0栋新增整栋验收。继续完成学院建筑的已知缺项，再按用户顺序开展实验大厅与新结构大楼。
