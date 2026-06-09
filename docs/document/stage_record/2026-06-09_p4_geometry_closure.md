# P4 几何增强 Smoke 收口记录

记录日期：2026-06-09

## 1. 当前检查范围

本次收口对照 SOP 的 P4 DoD，重点检查三件事：

- A2/A3/A4 配置是否存在并可驱动 smoke。
- 几何增强是否在代表类别上产生足够稳定的正信号。
- 当前实现是否适合直接扩到 P5 的 40 类消融。

已执行配置：

| 实验 | 配置 | 组件 | 代表类别 | 每类样本 |
|---|---|---|---|---:|
| A2 | `configs/experiment/A2_pasdf_normal.yaml` | distance + normal | `cap3/tap1/helmet1/ashtray0` | 2 |
| A3 | `configs/experiment/A3_pasdf_curvature.yaml` | distance + normal + curvature | `cap3/tap1/helmet1/ashtray0` | 2 |
| A4 | `configs/experiment/A4_pasdf_geom_full.yaml` | distance + normal + curvature，加大 normal/curvature 权重 | `cap3/tap1/helmet1/ashtray0` | 2 |

对应产物：

```text
docs/document/stage_record/2026-06-09_a2_pasdf_normal_geometry_smoke_summary.md
docs/document/stage_record/2026-06-09_a3_pasdf_curvature_geometry_smoke_summary.md
docs/document/stage_record/2026-06-09_a4_pasdf_geom_full_geometry_smoke_summary.md
experiments/P4_geometry_smoke/config_svgs/
```

## 2. 关键结果

### 2.1 A2：distance + normal

| 类别 | 异常 Object Score | Positive Object Score | 结论 |
|---|---:|---:|---|
| cap3 | 1.308899 | 1.327130 | positive 更高 |
| tap1 | 1.264911 | 1.261057 | 几乎持平 |
| helmet1 | 1.046785 | 1.032571 | 异常略高 |
| ashtray0 | 1.142623 | 1.136399 | 异常略高 |

局部 GT 信号：`tap1_broken2` 的 GT point score mean 为 `1.150848`，高于背景 `0.727031`；但 `helmet1_bulge0` 和 `ashtray0_bulge0` 的 GT 均值低于背景。

### 2.2 A3：distance + normal + curvature

| 类别 | 异常 Object Score | Positive Object Score | 结论 |
|---|---:|---:|---|
| cap3 | 1.574997 | 1.600806 | positive 更高 |
| tap1 | 1.394393 | 1.414237 | positive 更高 |
| helmet1 | 1.182358 | 1.173565 | 异常略高 |
| ashtray0 | 1.373567 | 1.365287 | 异常略高 |

加入曲率后 object score 整体变大，但没有稳定拉开异常和 positive control。

### 2.3 A4：full geometry 权重

| 类别 | 异常 Object Score | Positive Object Score | 结论 |
|---|---:|---:|---|
| cap3 | 1.951258 | 1.978263 | positive 更高 |
| tap1 | 1.706668 | 1.715392 | positive 更高 |
| helmet1 | 1.427666 | 1.410428 | 异常略高 |
| ashtray0 | 1.688806 | 1.680003 | 异常略高 |

A4 只是放大了分数尺度，没有解决异常/正常对照不可分的问题。

## 3. 收口判断

P4 几何增强基础设施已经完成：

- `configs/experiment/A2/A3/A4` 已存在。
- `scripts/run_geometry_smoke.py --config ...` 已可从 YAML 读取类别、k 值、top-k 比例、组件开关和权重。
- 代表类别 smoke 已生成轻量 CSV/Markdown/SVG。
- 几何算子和 scoring 模块已有单测。

但当前结果不支持直接进入 P5 的 A2/A3/A4 40 类全量消融：

- object score 没有稳定区分异常样本和 positive control。
- normal/curvature 加权后主要放大分数尺度，没有稳定改善排序。
- 曲率实现是 CPU PCA，多尺度 16k 点 smoke 已明显耗时，不适合未经优化直接扩到 40 类。
- 单 template residual 对整体形变、template 差异和采样分布敏感，尤其 `bending/bulge` 类型不稳定。

## 4. 下一步建议

不建议下一步直接跑 40 类 A2/A3/A4。更合理的下一步是做 P4.5 小修正：

1. 从 PASDF 官方流程中导出 per-sample/per-point score，先确认 baseline 的点级分数在哪里失败。
2. 几何 residual 改为多 template 或 registration 后 residual，而不是固定 `template0`。
3. 曲率计算加缓存或下采样策略，避免每次对 16k 点重复多尺度 PCA。
4. 只在 `tap1_broken2`、`cap3_broken2` 这类局部距离 residual 有正信号的样本上做 targeted 可视化，不扩大到全量。

若时间优先级要求进入 P5，则应把 A2/A3/A4 标记为“弱几何 smoke，不进入主表”，P5 主线改为：

- PASDF baseline 结果表和失败分析。
- registration/voxel sweep 作为主要消融证据。
- Real3D-AD 或 PO3AD 作为扩展对照，而不是把当前 geometry score 当作已验证增强。
