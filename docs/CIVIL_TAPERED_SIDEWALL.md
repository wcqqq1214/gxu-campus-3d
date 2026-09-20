# 土木学院东南塔部连续白色斜墙

2026-09-21，接续[玻璃塔头与屋顶墙片](CIVIL_ROOF_CROWN.md)，将东侧白墙向下延续到建筑模型底座。此前白墙只出现在屋顶上，下面仍是通用窗墙；本批形成由近地面到塔冠的连续白色轮廓，并去掉与它相交的通用窗。主入口、玻璃转角、塔头高度、主楼和附楼分段及原占地保持。

## 依据与估算

[学院英文官网宽幅](https://tmjz-en.gxu.edu.cn/images/banner_six.jpg)可见玻璃转角后方的大面积白墙向下接近地面，[完整正面图](https://tmjz.gxu.edu.cn/__local/A/7E/69/4A06C7C98FB4DD485911A8F3606_2806A0A4_AFCA6.jpg)提供墙片高于玻璃塔头的上部关系。[入口近照](https://tmjz-en.gxu.edu.cn/info/1050/1096.htm)中的侧门厅玻璃与局部低层开口继续单独校准，本批没有把这些细节替换成已确认的门洞。图片拍摄日期未知，只作本地参考。

沿用原东南转角与屋顶段：前缘深3.8米，主屋面26.4米处后缘深8米，顶部34.8米处后缘深6.2米。将这条估算斜率连续下延至模型基准以下0.5米，得到底部后缘约13.76米；白墙厚0.35米，表面向原东墙外偏0.08米，以免与已有墙面重合闪烁。底部与现有主体基座口径一致，不代表地下结构或现场测量。

全部高度、厚度、进深、斜率和外偏均为照片约束下的简化估算。证据和参数见[本批记录](model-checks/refinement/s2-civil-sidewall-evidence.json)。这次完成的是连续白墙体量，侧门厅玻璃、局部小开口与细部并未因此算作完成。

## 实现与验证边界

在 `roofCrown` 中增加可选 `sideWall`，复用同一转角、墙厚和上部斜率；未配置时保留原屋顶段生成。下延范围必须沿同一完整实体外墙，其背衬不得越过轮廓、体块边界或内院。外偏与底部标高有明确范围校验。

白墙整体在基础和近景中共用。默认窗采用墙面法向、所在平面和斜墙范围的相交检查，只有确实相交的窗整组退出，避免半窗及框线穿出；其他墙面、白墙后方和原玻璃转角保持。该逻辑不自动切割门洞，也不将同栋其他立面变成白墙。

数据测试覆盖下延斜率、非法标高/外偏和过短支撑边界。两级实际生成小样检查白墙材质、原窗位置及墙外窗列保留。专项检查核对正式源文件和GLB的连续白墙、斜后缘、原窗中心及斜边外保留墙面；上一批仅有屋顶墙片的版本作为反例。

原幕墙回归中的东墙4.2米、8米两处原石色检查已由新白墙专项替代；其他幕墙检查保持。塔头回归只将白墙表面预期外偏改为0.08米，原塔头高度、玻璃、斜率及屋顶检查保持。没有将预期变更说成原面片完全未变。

## 模型与画面

197项Python测试、56项Node测试、类型检查、lint与Pages构建通过。[侧墙专项](model-checks/refinement/s2-civil-sidewall-geometry.json)在源文件、基础及近景GLB各检查54处，[仅有屋顶墙片的反例](model-checks/refinement/s2-civil-sidewall-negative-geometry.json)按预期失败。塔头每级92处、幕墙每级218处、附楼台阶每级101处及其余既有专项通过；普通建筑、树木及道路碰撞回归通过。

[源对象比对](model-checks/refinement/s2-civil-sidewall-source-preservation.json)确认仅土木学院变化，其他530个非树对象和3063个树实例保持。[资产检查](model-checks/refinement/s2-civil-sidewall-assets.json)确认69个GLB与Pages产物一致，仅基础模型与本栋近景块改变。首屏5,175,920字节，较上一批减少56字节；最大普通近景仍1,684,868字节。

| 画面 | 对照 |
| --- | --- |
| 东南斜侧墙 | [改前](screenshots/refinement/s2-civil-sidewall-visible/before/civil-sidewall-trees-off-day.png) / [改后](screenshots/refinement/s2-civil-sidewall-visible/after/civil-sidewall-trees-off-day.png) |
| 南侧全貌 | [改前](screenshots/refinement/s2-civil-sidewall-visible/before/civil-south-overview-trees-off-day.png) / [改后](screenshots/refinement/s2-civil-sidewall-visible/after/civil-south-overview-trees-off-day.png) |
| 树木与夜景 | [树木开启](screenshots/refinement/s2-civil-sidewall-visible/after/civil-south-overview-trees-on-day.png) / [夜景](screenshots/refinement/s2-civil-sidewall-visible/after/civil-sidewall-trees-off-night.png) |
| 手机尺寸 | [桌面竖屏模拟](screenshots/refinement/s2-civil-sidewall-visible/after/civil-sidewall-trees-off-day-mobile.png)，非实体手机测试 |

七张最终建筑画面已直接核看。白墙上下连续，未见相交窗框穿出；原主门厅、上部玻璃和附楼台阶保留。侧门厅仍有待替换的通用窗，不能把本批白墙验收等同完整入口或整栋完成。道路连接和附楼细分屋顶继续按原计划推进。

## 性能与本批结论

[联合验收](model-checks/refinement/s2-civil-sidewall-summary.json)通过。三次LOD往返及两档各三次30秒采样完成，精细档60/60/60 FPS，流畅档29/29/29 FPS。对照原同系统S0，帧率变化0%/−3.33%，三角形增加3.82%/8.44%，绘制调用增加2.38%/11.03%，均符合原预算。

24次CPU快照未在计时窗口捕获超过2%阈值的Python或Blender进程；该10秒间隔采样不证明完全没有后台活动。图书馆入口竖屏回归画面已核看，记录见[最终画面验收](model-checks/refinement/s2-civil-sidewall-visual-review.json)。本批连续白墙局部通过，累计21条部分对象记录、0栋新增整栋验收；继续收尾当前学院建筑，然后依次开展实验大厅、新结构大楼。

2026-09-21接续：[侧门厅玻璃与转角顶板](CIVIL_PORTAL_RETURN.md)已补入，替换本页截图中的两排侧面通用窗；白墙几何保持。局部小开口仍未据此认定完成。
