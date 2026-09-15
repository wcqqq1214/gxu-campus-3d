# 资环材学院入口：空间约束核查与方案撤回

> 2026-09-16，`dev`。本批查明入口方案与道路、地形的冲突，增加构建前预检；没有交付新的入口模型。当前模型保持 `61d15e9` 的[东端透空框架](MATERIALS_BUILDING_FRAME.md)。

## 本轮结论

照片支持东侧有低雨棚、圆柱和前后上升的台阶，但不能直接确定这些构件在当前地图中的边界与标高。将照片比例直接外推到既有东外墙的试制方案出现两项问题：

| 核查项 | 实际证据 | 处理 |
| --- | --- | --- |
| 外台阶与道路 | 候选入口占地与 `way/842784663` 的 `highway=service` 三角网平面重叠 **60.0002 m²** | 不以抬高、缩短、挪路或假设隧道消除冲突；撤回候选入口 |
| 台阶落地 | 候选最低踏面为楼栋基准以上 0.26 m；其一侧实际地面为基准以上约 1.919 m，踏面被埋约 **1.659 m** | 保存失败结果，后续先核对局部场地基准 |
| 现有道路验证范围 | `validate_road_buildings.py` 检查专用 infrastructure 道路与桥梁，未覆盖全部 `surfaces.json` 中的道路 | 增加显式入口占地与机动车道路的二维预检 |

候选方案中的外20级、内22级、平台3.3/6.6米和13.2米低雨棚等数字已撤回，不是当前模型的校准值。源文件、派生建筑数据、全部 GLB 和本地预览资源均恢复到本轮开始版本；原地图道路、地形、树木及三个内院保持。

原始候选参数、40个地面采样、失败信息与输入指纹见[约束证据](model-checks/refinement/s2-materials-entry-constraints.json)。地面采样来自模型，不是现场测量。失败候选只在本机工作目录留档，未作为公开模型发布。

## 新增预检及范围

`scripts/audit_entry_road_context.py` 检查已解析的 `attachedPortico`、`stairFlight` 及候选 `recessedStairEntry` 占地，对比原始地表机动车道路三角网。它保留隧道、桥梁和层级标签供复核；存在平面重叠时退出码为1，不自动假定上下层已经避让。

当前快照中共有4个适用的显式入口占地，均无机动车道路面积重叠，见[当前预检](model-checks/refinement/current-entry-road-preflight.json)。这不包括所有示意门口，也不代表地形、步行道、树冠或完整入口已通过验收。

```sh
# 在完整建模前执行：当前已有显式入口
work/refinement-venv/bin/python scripts/audit_entry_road_context.py \
  --report docs/model-checks/refinement/current-entry-road-preflight.json

# 复现本轮失败候选：预期退出码为1，并报告约60平方米重叠
work/refinement-venv/bin/python scripts/audit_entry_road_context.py \
  --proposal docs/model-checks/refinement/s2-materials-entry-constraints.json \
  --report docs/model-checks/refinement/s2-materials-entry-road-preflight.json
```

5项新增测试覆盖实质面积重叠、仅边界接触、步行道范围、上下层标签和无效占地。最终159项Python测试通过。当前资产恢复核查见[恢复报告](model-checks/refinement/s2-materials-entry-restoration.json)。本批没有变更运行模型，因此未以候选构建的通过项或性能结果宣称入口完成。

## 下一步资料与实施条件

[校方2023年改造公告](https://www.gxu.edu.cn/info/1364/32571.htm)提及原建筑图及楼梯改造；本轮检查到的公开页面未提供可读取的原建筑图下载链接。公告中的拟改造内容仍不视为竣工状态。[学校规划图页面](https://www.gxu.edu.cn/ggfw/xxght.htm)提供文件名为2019ght的[规划图](https://www.gxu.edu.cn/images/18/2019ght.jpg)，可辅助整体位置核对，但未提供本入口的可测量台阶标高，不能替代现状测绘。

继续核对入口首级、两处平台、门区与道路的平面对应，优先寻找总平面、可辨识的俯视资料或建筑图。确认服务道路究竟位于台阶外、位置有误或存在上下层关系之后，再确定局部平台及道路处理。入口未确认期间，S2其他楼栋与S3邻楼工作继续按原计划推进；对象数仍为19条部分记录，整栋验收数不增加。
