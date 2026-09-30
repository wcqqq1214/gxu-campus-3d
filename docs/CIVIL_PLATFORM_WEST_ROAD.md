# 结构平台西侧服务路贴地修补

本批处理既有结构试验平台西侧的映射服务路 `way/759096572`，继续用户指定的实验大厅及“新结构大楼”优先队列。它是模型接地修复，不增加建筑整栋完成计数；九层结构平台与新建综合实验中心仍分别识别。

## 问题与范围

在上一批楼体地形侵入修复后，整条西侧服务路仍有旧的悬空和埋地问题。[修复前实际资产采样](model-checks/refinement/s2-platform-west-road-repro-before.json)覆盖源模型和基础GLB各6,515点：源模型有802点埋入地面超过3厘米，路地高差约为−0.764至1.506米；基础GLB有808处相同类型的埋地点。这是路面与实际地形三角面不一致，不能靠调整观看角度解决。

沿用原映射路面和上一批建筑避让裁剪；有效面积约1,684.88平方米。其中约18.61平方米的邻路重叠保留，修补约1,666.26平方米。三处接缝分别连接东侧平台服务路、南侧服务路和南端校园道路。原始DEM、建筑标高、楼体形状和道路平面数据保持。

## 实现

- 非路口区域跟随实际地形三角面，数值偏移为8厘米；自由路边封口下探地形6厘米。
- 接缝从保留路面的内侧采样，并外推其平面，避免边界射线误取埋在下面的旧路面。名义3米的方角过渡带用于接续，拐角范围并非严格的3米圆形缓冲。
- 路面依据地形折线裁分，路口过渡采用1.5米辅助网格；保留边界站点，合并近共面的碎三角形。源文件中的浮点坐标误差按0.1毫米焊接容差处理，并用保留路面的实际高度复查约束。
- 网页导出复用既有局部服务路节点；普通道路仍保留17位位置精度，局部道路使用15位位置精度。普通道路路面采用10位纹理坐标，局部道路保留11位，标线和其他材质不使用该纹理设置。
- 基础GLB加载后，从静态地形和道路索引中剔除9,650个严格零面积面。有效三角形顺序及全部顶点属性逐字节保持；没有使用“小面积”阈值，也不简化真实地形折线。七组校园渲染像素一致，UI图标的单像素差异另行记录。

8厘米偏移、6厘米封口、过渡宽度及纵坡均是模型修补参数，不是现场测量或道路设计值。路口仍沿用模型原有高程；保留地形中的陡坡不能据此解释成真实道路坡度。

## 验证

最终结果以本批机器报告为准：

- [路面、封口、三处接缝及保留区](model-checks/refinement/s2-platform-west-road-geometry.json)
- [与原6,515点复现对应的复测](model-checks/refinement/s2-platform-west-road-repro-after.json)
- [楼体内部侵入复验](model-checks/refinement/s2-platform-west-road-foundation.json)
- [D区人员入口接路复验](model-checks/refinement/s2-platform-west-road-connection-geometry.json)
- [源对象保持性](model-checks/refinement/s2-platform-west-road-source-preservation.json)、[网页资产保持性](model-checks/refinement/s2-platform-west-road-assets.json)
- [实际解码网格等价检查](model-checks/refinement/s2-platform-west-road-degenerate-triangles.json)、[画面像素对比](model-checks/refinement/s2-platform-west-road-pixel-preservation.json)
- [最终视图和性能汇总](model-checks/refinement/s2-platform-west-road-summary.json)

初次性能测量虽为60/30 FPS，但流畅档三角形增幅15.23%，超过原15%门槛，保留[未通过记录](model-checks/refinement/s2-platform-west-road-pre-prune-summary.json)。在剔除零面积面后重新测量，不将初次结果改写为通过。

大厅运输口的外墙配准、北楼南/西立面、西门厅屋面及旧大厅独立身份仍需继续核对。外围高地保持不变，低位镜头可能仍受前景遮挡；本批不作为平台整栋或现场场地完整验收。
