# 地形导出：完整顶点属性去重

> 后续：该去重已随[三教正式修补](TEACHING_THREE_FOUNDATION.md)进入地形与道路导出；道路共享18位位置量化。下文保存本工具首次实现时的独立候选证明与状态。

2026-09-30。本批实现导出阶段的精确顶点去重，支持继续修复第三教学楼接地和道路冲突。**正式源模型、公开数据和69份GLB尚未替换；下列体积是独立候选的测量，不是已发布成果。**

## 实现与边界

Blender导出器将源顶点编号纳入顶点去重判断，因此独立编号可能使属性完全相同的顶点重复存储。新增 `blender/vertex_dedup.py`，在 glTF mesh hook、Draco压缩之前，将一个 primitive 内全部顶点属性的原始字节组成键，只合并键完全相同的记录，并重映射原索引。位置相同而UV、法线或其他属性不同的顶点保持分离；压缩前的三角面顺序、重复面和各个角的属性保持。Draco仍可重排面，最终验证比较有向面的多重集合，不主张编码后的索引顺序不变。

不使用距离、角度、精度舍入或面积阈值。没有移动顶点、降低Draco位数或重新生成UV。新建accessor与BinaryData，避免修改导出器共享缓存；非三角面、非索引几何及带形变目标的primitive不处理。

`omit_unused_uvs(deduplicate_vertices=True)`按上下文启用，正常退出、嵌套调用及异常时恢复原设置。`replace_precise_terrain`当前仅对地形精确导出启用；普通道路仍沿用既有生产规则。道路材料更高精度版本仅是本地试验，尚未接入正式构建。

## 实际解码证明

[地形对照](model-checks/refinement/s2-teaching3-terrain-dedup-equivalence.json)使用三教候选的相同源几何和18位位置/UV、6位法线设置：

- 单节点文件1,312,488 → 1,002,976字节，减少309,512字节。
- 解码顶点313,852 → 246,135。
- 三角面均为117,906个，包括7,547个严格零面积面；有效面110,359个。
- 全部有向三角面的材质名和所有Float32顶点属性组成的多重集合完全一致，包含零面积面，不只是有效面一致。

同一方法对[19位道路试验](model-checks/refinement/s2-teaching3-road-dedup-equivalence.json)的89,811个三角面也证明完全一致。该试验的整体预算及漏点另行判定；属性等价不等于道路候选通过。

可重复检查命令：

```sh
node scripts/check-glb-node-equivalence.mjs \
  --before work/refinement-s2-teaching3-review/terrain-18.glb \
  --after work/refinement-s2-teaching3-review/terrain-attribute-dedup.glb \
  --report work/terrain-equivalence.json
```

可用 `--node roads` 检查道路节点。检查器解码实际Draco数据，保留有向面、重复次数和全部属性，仅规范化正负零；材质参数与图像载荷不在该检查范围内。这里的前后单节点文件均来自同一源文件，组合候选继续沿用正式基础模型的材质与图像。

## 已排除的路径

直接重建Blender网格并合并重合顶点的试验虽然更小，但[实际解码对照](model-checks/refinement/s2-teaching3-terrain-weld-rejected.json)少了102个有效面，且不只涉及重复面；不能采用。源网格法线检查通过并不足以证明最终三角面保持。正式实现因此在导出属性与索引数组中去重，不重建Blender拓扑。

## 检查与接续

7项去重回归覆盖完整面角保持、UV/法线差异、不同索引类型、共享缓存、自定义属性、非法索引、跳过范围和嵌套异常清理。既有混合材质实际Draco导出、带后缀地形/道路精确导出夹具通过；299项Python检查通过，新解码脚本lint通过。本批未新增网页、Pages构建或性能测量。

三教的源修补候选与周边检查已有进展，但跨材质路面边界仍未联合通过，见[接地专项](TEACHING_THREE_FOUNDATION.md)及[本批汇总](model-checks/refinement/s2-teaching3-export-investigation.json)。下一步解决共享边界，再集成正式模型并做道路回归、网页和性能验证。完整S0–S5目标及当前22/2/20计数保持。
