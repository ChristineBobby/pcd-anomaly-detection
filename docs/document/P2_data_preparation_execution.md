# P2 数据准备执行记录

撰写日期：2026-06-07
适用阶段：P2 数据准备
执行地点：Linux GPU 服务器 + Docker 容器 `upbeat_jemison`

---

## 0. 当前结论

课程数据集已放置在：

```text
data/Anomaly-ShapeNet-v2.rar
```

有效解压目录为：

```text
data/Anomaly-ShapeNet-v2/
```

主实验应继续使用官方 40 类协议目录：

```text
data/Anomaly-ShapeNet-v2/dataset/pcd/
```

实测点数范围为 **17,422-157,824**，均值 **56,861.24**，与课程任务书的高密度口径一致，明显高于公开低密度 `8K-30K` 版本。PASDF 后续评估必须按 `target_num_points=16384` 做下采样/采样策略控制，不能假设输入天然是公开低密度版本。

### 0.1 P2 DoD 状态

按 `SOP_engineering_workflow.md` 的 P2 DoD 拆分，当前状态如下：

| 项目 | 状态 | 证据/说明 |
|---|---|---|
| 数据集解压与目录确认 | 已完成 | `data/Anomaly-ShapeNet-v2/` 为有效目录；`7z` 失败残留已隔离为忽略目录 |
| `experiments/data_stats.md` 产出 | 已完成 | `make data` 可重新生成；主协议统计为 40 类、1472 样本、train 160、test 1312 |
| 点数口径结论 | 已完成 | `pcd` 点数为 17,422-157,824，均值 56,861.24，确认是高密度课程版 |
| 官方 40 类主协议固化 | 已完成 | `configs/data/anomaly_shapenet.yaml` 使用 `collections: [pcd]` 和 `target_num_points: 16384` |
| DataLoader 与单测 | 已完成 | `AnomalyShapeNetDataset` 返回 `(points, normals, labels, meta)`；`make test` 通过 |
| 随机抽 1 类可视化点云 + GT | 未完成 | 尚未实现 P2 可视化 smoke artifact；进入 P3 前应补一张本地图或交互检查记录 |
| 标准化/16384 点采样产物 | 部分完成 | 配置已固化目标点数，但尚未生成标准化缓存；P3 PASDF wrapper 必须实现确定性采样并记录策略 |
| 法向估计 | 未完成且有意延期 | 源 PCD 只有 XYZ；当前 Dataset 返回零法向占位。真实法向估计放到后续 `preprocess.py` 或几何模块，不在 DataLoader 热路径中做 |

因此，P2 的“数据审计 + 协议口径 + DataLoader”已经完成；严格按 SOP，P2 还剩可视化 smoke 和标准化/采样落地两项未完成。它们不影响开始 P3 的官方 PASDF 权重评估，但必须在 P3 wrapper 或 P4 几何模块中补齐并记录。

---

## 1. 解压排查与处理

### 1.1 归档信息

RAR 文件：

```text
data/Anomaly-ShapeNet-v2.rar
```

实测大小约 `3.6G`，RAR v4 archive。归档内容统计：

```text
path_count: 5070
.pcd: 1931
.obj: 1930
.txt: 943
directory entries: 266
```

### 1.2 7z 失败根因

容器内安装 `7zip` 后使用：

```bash
7z x -y -odata data/Anomaly-ShapeNet-v2.rar
```

该命令报大量：

```text
ERROR: Unsupported Method
Sub items Errors: 4804
```

并生成了 4804 个占位文件，但所有 `.pcd/.obj/.txt` 均为 0 字节。结论：这是当前 `7z` 对该 RAR 压缩方法不兼容，不是可用解压结果。

### 1.3 正确解压方式

容器内安装并使用 `unar`：

```bash
unar -f -o /tmp/anomaly_shapenet_unar_probe data/Anomaly-ShapeNet-v2.rar
```

`unar` 全量解压成功，所有文件均为非零大小。随后将有效目录移动到：

```text
data/Anomaly-ShapeNet-v2/
```

最终有效解压目录统计：

```text
file_count: 4804
.pcd: 1931
.obj: 1930
.txt: 943
zero_files: 0
data size: about 12G
```

注意：以后处理此 RAR 包优先使用 `unar`，不要使用当前容器中的 `7z` 作为最终解压工具。

---

## 2. 数据目录结构

有效数据目录：

```text
Anomaly-ShapeNet-v2/
└── dataset/
    ├── pcd/       # 官方主协议目录，40 个类目录
    ├── new_pcd/   # 扩展目录，当前包内为 12 个类目录
    ├── obj/
    └── new_obj/
```

`pcd` 和 `new_pcd` 下每个类目录均包含：

```text
GT/
test/
train/
```

PCD 文件为 binary PCD，字段为 `x y z`。GT `.txt` 为逗号分隔，前 3 列为点坐标，第 4 列为点级异常标签。

---

## 3. 统计命令

默认主协议统计：

```bash
PYTHONPATH=src python scripts/prepare_data.py --stat
```

输出：

```text
experiments/data_stats.md
```

扩展全包统计：

```bash
PYTHONPATH=src python scripts/prepare_data.py --stat --all-collections \
  --output experiments/data_stats_all_collections.md
```

两个输出均在 `experiments/` 下，默认不提交入库；关键结论在本文档中保留。

---

## 4. 主协议统计结果

命令：

```bash
PYTHONPATH=src python scripts/prepare_data.py --stat
```

结果摘要：

```text
collections: pcd
classes: 40
samples: 1472
train: 160
test: 1312
GT files: 712
point count min: 17422
point count mean: 56861.24
point count max: 157824
labeled points: 41726112
anomaly points: 999969
aggregate anomaly ratio: 2.3965%
```

样本类型计数：

```text
bending: 8
broken: 36
bulge: 280
concavity: 280
crack: 25
hole: 38
positive: 600
scratch: 45
template: 160
```

这说明当前课程数据包不是公开低密度 PCD 版本，而是高密度重采样版本。主实验继续按 `pcd` 的 40 类协议执行。

---

## 5. 扩展目录统计结果

命令：

```bash
PYTHONPATH=src python scripts/prepare_data.py --stat --all-collections \
  --output experiments/data_stats_all_collections.md
```

结果摘要：

```text
collections: pcd, new_pcd
classes: 52
samples: 1931
train: 208
test: 1723
GT files: 943
point count min: 17422
point count mean: 57074.01
point count max: 157824
labeled points: 55481600
anomaly points: 1145704
aggregate anomaly ratio: 2.0650%
```

当前 RAR 包中的 `new_pcd` 目录包含 12 个类目录：

```text
cabinet0 cap1 cap2 chair0 cup2 desk0 knife0 knife1 microphone1 screen0 vase10 vase6
```

因此全包目录级统计为 52 类，而不是文档调研时预期的 50 类。P3 主线暂不使用 `new_pcd`，只在后续扩展实验中单独说明口径。

---

## 6. 已实现代码

新增数据模块：

```text
src/pcdad/data/dataset.py
```

能力：

- 发现 `dataset/pcd` 与 `dataset/new_pcd` 下的 train/test PCD 样本。
- 解析异常类型，兼容 `crak -> crack` 以及 `desk0/desk_bulge0.pcd` 这类类名实例编号不一致的文件。
- 读取 PCD header，用于快速统计点数。
- 读取 ASCII / uncompressed binary PCD 的 XYZ 点坐标。
- 读取 GT txt 第 4 列点级标签。
- 提供 `AnomalyShapeNetDataset`，返回 `(points, normals, gt_point_labels, meta)`。

当前 PCD 只有 XYZ，没有原生 normals。Dataset 在未做预处理时返回零法向占位；法向估计应在后续 `src/pcdad/data/preprocess.py` 或几何模块中显式执行并缓存，避免在 DataLoader 中反复对 15 万点样本做昂贵邻域搜索。

新增脚本：

```text
scripts/prepare_data.py --stat
```

新增测试：

```text
tests/test_dataset.py
tests/test_prepare_data.py
```

---

## 7. 后续进入 P3 前的注意事项

1. PASDF 默认 `target_num_points=16384`。当前高密度数据最大 157,824 点，必须在评估入口中固定随机种子并记录采样索引或采样策略。
2. 默认主协议为 `configs/data/anomaly_shapenet.yaml` 中的 `collections: [pcd]`，对应 40 类、train 160、test 1312。
3. `new_pcd` 当前是 12 个类目录，应作为扩展口径单独报告，不要混入 PASDF 40 类主结果。
4. 该 RAR 包以后用 `unar` 解压；`7z` 在当前容器会生成 0 字节残留。
5. `experiments/data_stats.md` 是本地运行产物，不提交；提交本文档中的关键结论即可复现口径。
