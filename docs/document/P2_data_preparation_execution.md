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

P2 当前已闭合：数据统计、DataLoader、PASDF 16384 点固定采样目录、GT 格式转换、真实样本 GT/法向 smoke 可视化均已完成。可进入 P3 官方 PASDF 权重评估。

### 0.1 P2 DoD 状态

按 `SOP_engineering_workflow.md` 的 P2 DoD 拆分，当前状态如下：

| 项目 | 状态 | 证据/说明 |
|---|---|---|
| 数据集解压与目录确认 | 已完成 | `data/Anomaly-ShapeNet-v2/` 为有效目录；`7z` 失败残留已隔离为忽略目录 |
| `experiments/data_stats.md` 产出 | 已完成 | `make data` 可重新生成；主协议统计为 40 类、1472 样本、train 160、test 1312 |
| 点数口径结论 | 已完成 | `pcd` 点数为 17,422-157,824，均值 56,861.24，确认是高密度课程版 |
| 官方 40 类主协议固化 | 已完成 | `configs/data/anomaly_shapenet.yaml` 使用 `collections: [pcd]` 和 `target_num_points: 16384` |
| DataLoader 与单测 | 已完成 | `AnomalyShapeNetDataset` 返回 `(points, normals, labels, meta)`；`make test` 通过 |
| 随机抽 1 类可视化点云 + GT + 法向 | 已完成 | `experiments/p2_smoke/anomaly_shapenet_ashtray0_gt_normals.svg`，样本为 `ashtray0_bulge0` |
| 标准化/16384 点采样产物 | 已完成 | `data/Anomaly-ShapeNet-v2/dataset/16384/`，40 类、1472 个 PCD、每个 16,384 点 |
| 法向估计 | P2 smoke 完成，训练缓存延期 | smoke 图用 Open3D KNN 法向；Dataset 仍返回零法向占位，真实法向缓存留到几何模块 |

因此，P2 的 SOP DoD 已闭合。后续 P3 可以直接使用 `data/Anomaly-ShapeNet-v2/dataset/16384` 作为 PASDF ShapeNetAD 评估输入。

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
src/pcdad/data/preprocess.py
src/pcdad/viz/pointcloud.py
```

能力：

- 发现 `dataset/pcd` 与 `dataset/new_pcd` 下的 train/test PCD 样本。
- 解析异常类型，兼容 `crak -> crack` 以及 `desk0/desk_bulge0.pcd` 这类类名实例编号不一致的文件。
- 读取 PCD header，用于快速统计点数。
- 读取 ASCII / uncompressed binary PCD 的 XYZ 点坐标。
- 读取 GT txt 第 4 列点级标签。
- 提供 `AnomalyShapeNetDataset`，返回 `(points, normals, gt_point_labels, meta)`。
- 提供确定性采样、单位球标准化、PASDF 兼容 PCD/GT 写出与 manifest 记录。
- 提供轻量 SVG smoke 可视化，叠加点级 GT 和抽样法向线。

当前 PCD 只有 XYZ，没有原生 normals。Dataset 在未做预处理时返回零法向占位；P2 smoke 图用 Open3D 临时估计法向，仅用于人工检查。后续几何模块若需要法向，应显式执行并缓存，避免在 DataLoader 中反复对 15 万点样本做昂贵邻域搜索。

新增脚本：

```text
scripts/prepare_data.py --stat
scripts/prepare_data.py --prepare-pasdf
scripts/prepare_data.py --smoke-visualize
```

新增测试：

```text
tests/test_dataset.py
tests/test_prepare_data.py
tests/test_preprocess.py
tests/test_visualize.py
```

---

## 7. PASDF 16384 点目录

生成命令：

```bash
PYTHONPATH=src python scripts/prepare_data.py \
  --prepare-pasdf \
  --output-root data/Anomaly-ShapeNet-v2/dataset/16384 \
  --target-num-points 16384 \
  --normalize none \
  --seed 42
```

输出目录：

```text
data/Anomaly-ShapeNet-v2/dataset/16384/
```

产物审计：

```text
classes: 40
pcd files: 1472
train pcd: 160
test pcd: 1312
GT txt: 712
point counts: all 16384
manifest: data/Anomaly-ShapeNet-v2/dataset/16384/preprocess_manifest.json
data size: about 1.2G
```

采样策略：

- 默认 `normalize=none`，保留课程数据原始坐标尺度。PASDF 官方 `test_ShapeNetAD.yaml` 也设置 `normalize: False`，这样避免重复归一化。
- 采样为确定性 sample-key 随机采样。随机种子为 `42`，sample key 为 `collection/class/split/sample_id`。
- 每个样本在 manifest 中记录原始点数、输出点数、采样索引 SHA256、唯一采样索引数、normalization 参数。
- 若原始点数小于目标点数，采样会使用 replacement；当前主协议所有 PCD 点数均大于 16,384，因此全量产物无 replacement。

GT 转换策略：

- 源 GT 为逗号分隔 `x,y,z,label`，PASDF `ShapeNetAD.py` 使用空格分隔读取，所以 16384 目录中的 GT 改写为空格分隔。
- 源 PCD 点顺序与 GT 行顺序不保证一致；`helmet1` 中 5 个 GT 文件还比对应 PCD 多 1 行。
- 预处理时按 GT 坐标到 PCD 点坐标做最近邻匹配，先把标签重排到 PCD 点顺序，再使用同一采样索引同步采样 points 和 labels。

PASDF loader smoke：

```text
ashtray0_bulge0: points (16384, 3), mask (16384,), mask sum 1095, label 1
helmet1_bulge0: points (16384, 3), mask (16384,), mask sum 539, label 1
vase0_bulge0: points (16384, 3), mask (16384,), mask sum 805, label 1
```

---

## 8. 可视化 smoke

生成命令：

```bash
PYTHONPATH=src python scripts/prepare_data.py \
  --smoke-visualize \
  --classes ashtray0 \
  --output experiments/p2_smoke/anomaly_shapenet_ashtray0_gt_normals.svg \
  --max-points 4096 \
  --seed 42
```

输出：

```text
experiments/p2_smoke/anomaly_shapenet_ashtray0_gt_normals.svg
```

内容：

```text
sample: ashtray0_bulge0
original points: 44388
original anomaly labels: 3057
rendered points: 4096
rendered anomaly labels: 275
normal lines: Open3D KNN normal smoke sample
```

---

## 9. 后续进入 P3 前的注意事项

1. PASDF 默认 `target_num_points=16384`。P2 已生成固定采样目录，P3 应优先使用 `data/Anomaly-ShapeNet-v2/dataset/16384`，不要在 PASDF loader 内再次随机下采样。
2. 默认主协议为 `configs/data/anomaly_shapenet.yaml` 中的 `collections: [pcd]`，对应 40 类、train 160、test 1312。
3. `new_pcd` 当前是 12 个类目录，应作为扩展口径单独报告，不要混入 PASDF 40 类主结果。
4. 该 RAR 包以后用 `unar` 解压；`7z` 在当前容器会生成 0 字节残留。
5. `data/Anomaly-ShapeNet-v2/dataset/16384`、`experiments/data_stats.md`、`experiments/p2_smoke/` 都是本地运行产物，不提交；提交本文档中的关键结论、命令和代码即可复现口径。
