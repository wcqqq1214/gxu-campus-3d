# 土木学院附楼东侧退台与高低屋面

2026-09-21，接续侧门厅，处理西南附楼面向前庭的上层退进。原模型为三层通高直墙和统一10.8米屋面；本批将东前沿划为7.2米露台，后部保留10.8米上层主体，补入退台后露出的三组窗。尺寸为照片约束估算，不是测绘；局部三角形高墙及后方屋面仍未完成。

## 依据与形体

[学院英文官网宽幅](https://tmjz-en.gxu.edu.cn/images/banner_six.jpg)与[完整正面图](https://tmjz.gxu.edu.cn/__local/A/7E/69/4A06C7C98FB4DD485911A8F3606_2806A0A4_AFCA6.jpg)可辨附楼上层墙面退在下部房间之后，前方留有露台。沿既定台阶所对应的原外环第4边向内退3.2米，两端与原相邻外边相交；新增露台占地约53.434平方米，剩余附楼主体约680.827平方米，两者完整覆盖原附楼。

| 部位 | 本批参数 | 依据口径 |
| --- | --- | --- |
| 东侧露台 | 屋面7.2米，上层退进3.2米，沿墙约16.70米 | 露台关系有照片支持；尺寸采用既有估算层高和轮廓约束 |
| 后部上层 | 屋面10.8米 | 保留原三段竖向空间估算，未确认地上/半地下层划分 |
| 女儿墙 | 高0.8米、厚0.25米 | 沿用共享平屋面构件的简化尺寸 |
| 退台后窗组 | 三组，底8.15米、顶10.35米，各三列两行 | 开口存在有照片支持；数量、尺寸和分格简化估算 |

照片中的三角形高墙及小拱窗不能单独证明后方整片屋顶为双坡。本批只落实已定位的东前沿退台，不将未核对的南、西、后部退进范围或屋面坡向视为已知。[证据记录](model-checks/refinement/s2-civil-annex-terrace-evidence.json)保留原图哈希、观察与估算；参考原图只保存在本机。

## 实现与边界

复用已有`parts`和`exposedFacadeRules`，没有增加新的生成接口。`southwest-annex`保留高部，新增`southwest-terrace`低部；基础与近景共同生成高差、露台、女儿墙及窗组。地面C形轮廓、内院、主楼、塔冠、白墙和东南门厅保持。

原两段台阶参数与位置保持，支撑体块身份随拆分改为`southwest-terrace`。台阶与屋顶露台是两个不同标高的空间，不据此生成新增门洞或认定内部通行连接已完成。场地到校道的铺装连接继续待办。

## 验证记录

独立固定坐标射线检查7.2米露台、10.8米上屋面、两级女儿墙、原前沿上层墙体移除、3.2米后退墙面及窗组。首次探针误把窗框深度作为玻璃外偏，预期后退3.10米；实际共享玻璃面距后墙0.04米，正确预期为3.16米。模型无须改变，修正了探针；[首次失败记录](model-checks/refinement/s2-civil-annex-terrace-initial-probe-geometry.json)保留，不作为模型失败或验收通过依据。

旧附楼屋面检查中，原x=-516米的三个探针如今靠近新高部边缘女儿墙，移动到x=-518米检查保留屋面；新高部边缘及露台由本批专项独立检查。其余既有专项继续执行。

[正式模型专项](model-checks/refinement/s2-civil-annex-terrace-geometry.json)在源文件、基础GLB、近景GLB各检查59处；[旧模型反例](model-checks/refinement/s2-civil-annex-terrace-negative-geometry.json)在7.2米露台处按预期失败。200项Python测试、56项Node测试、类型检查、lint及Pages构建通过，台阶、侧门厅、塔冠、白墙、主楼立面及其他既有专项回归通过。

[数据检查](model-checks/refinement/s2-civil-annex-terrace-data.json)确认三部分互不重叠并完整覆盖原轮廓，覆盖解析可重复执行，其他447栋和地面数据保持。[源对象比对](model-checks/refinement/s2-civil-annex-terrace-source-preservation.json)仅土木学院变化，其他530个非树对象及3063株树保持。通用建筑、树木净空与道路碰撞回归通过。

[资产检查](model-checks/refinement/s2-civil-annex-terrace-assets.json)确认仅基础GLB及本栋近景块变化，其他67个GLB和90个基础节点保持，69个模型与Pages产物一致。首屏5,178,172字节，比上批增加1,436字节；最大普通近景1,684,868字节。

## 固定视角

| 画面 | 对照 |
| --- | --- |
| 附楼退台 | [改前](screenshots/refinement/s2-civil-annex-terrace-visible/before/civil-annex-terrace-trees-off-day.png) / [改后](screenshots/refinement/s2-civil-annex-terrace-visible/after/civil-annex-terrace-trees-off-day.png) |
| 南侧全貌 | [改前](screenshots/refinement/s2-civil-annex-terrace-visible/before/civil-south-overview-trees-off-day.png) / [改后](screenshots/refinement/s2-civil-annex-terrace-visible/after/civil-south-overview-trees-off-day.png) |
| 环境 | [植被开启](screenshots/refinement/s2-civil-annex-terrace-visible/after/civil-south-overview-trees-on-day.png) / [夜景](screenshots/refinement/s2-civil-annex-terrace-visible/after/civil-annex-terrace-trees-off-night.png) |
| 手机尺寸 | [竖屏模拟](screenshots/refinement/s2-civil-annex-terrace-visible/after/civil-annex-terrace-trees-off-day-mobile.png)，非实体设备测试 |

七张画面均已直接核看，露台与后退窗墙可辨认，未见旧前沿上层墙残留或明显屋面裂缝。前方资环材楼遮挡附楼西侧部分，但东侧退台及台阶可见；手机尺寸中主体更小，仍能辨认本次高低变化。此结论不覆盖尚未实现的三角形高墙、后部屋面或完整场地连接。

## 性能与阶段状态

[联合验收](model-checks/refinement/s2-civil-annex-terrace-summary.json)通过。三次LOD往返及两档各三次30秒采样完成，精细档60/60/60 FPS、流畅档30/30/30 FPS。相对原同系统S0，两档中位帧率保持，三角形增加3.83%/8.07%，绘制调用增加2.38%/7.22%，均符合原预算。

24次CPU快照未在计时窗口捕获超过2%阈值的Python或Blender计算；10秒采样间隔不能证明完全没有后台活动。图书馆入口竖屏回归亦已直接核看，见[最终画面验收](model-checks/refinement/s2-civil-annex-terrace-visual-review.json)。

本批完成附楼东侧退台这一部分，累计仍为21条部分对象记录、0栋新增整栋验收。下一步继续前场连接及剩余屋面、立面，学院建筑完成后依次开展实验大厅、新结构大楼。
