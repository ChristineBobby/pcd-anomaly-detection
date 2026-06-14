# P7 代码框架与依赖预研

撰写日期：2026-06-14

文档定位：本文件服务 P7-P11 创新阶段开发，重点回答“代码如何模块化、需要哪些 package、哪些依赖必须隔离、哪些 release/issue 风险会导致环境冲突”。本文件与 `SOP_P7_innovation_workflow.md` 配套使用。

<!-- TOC START -->
## 目录

- [1. 结论先行](#1-结论先行)
- [2. 当前 codebase 基础](#2-当前-codebase-基础)
- [3. P7 推荐代码框架](#3-p7-推荐代码框架)
  - [3.1 新增目录](#31-新增目录)
  - [3.2 模块职责](#32-模块职责)
  - [3.3 核心接口](#33-核心接口)
  - [3.4 CLI 设计](#34-cli-设计)
  - [3.5 实验产物结构](#35-实验产物结构)
- [4. 环境分层策略](#4-环境分层策略)
- [5. Package 预研与版本策略](#5-package-预研与版本策略)
  - [5.1 P7 主线环境：沿用 PASDF/PyTorch 1.11](#51-p7-主线环境沿用-pasdfpytorch-111)
  - [5.2 轻量新增依赖](#52-轻量新增依赖)
  - [5.3 高风险扩展依赖](#53-高风险扩展依赖)
  - [5.4 不建议混装的依赖](#54-不建议混装的依赖)
- [6. 官方 release/install/issue 风险摘要](#6-官方-releaseinstallissue-风险摘要)
- [7. 推荐环境矩阵](#7-推荐环境矩阵)
- [8. 安装与验证命令草案](#8-安装与验证命令草案)
- [9. 测试计划](#9-测试计划)
- [10. 风险清单与规避策略](#10-风险清单与规避策略)
- [11. 下一步开发顺序](#11-下一步开发顺序)
- [12. References](#12-references)
<!-- TOC END -->

## 1. 结论先行

P7 主线应尽量**不大改当前 PASDF 环境**。原因是 P3 baseline 已经在当前环境复现到 mean object AUROC=`0.900214149779`、mean pixel AUROC=`0.896009030694`，这套环境是当前最可靠资产。

推荐环境策略：

1. **主线环境 `pasdf` 保守扩展**：只增加纯 Python 或已有依赖能覆盖的模块，优先使用 `numpy/scipy/scikit-learn/open3d/trimesh/point-cloud-utils`。不要把 PO3AD、MinkowskiEngine、PTv3、Pointcept 直接装进 `pasdf`。
2. **PO3AD 单独环境 `po3ad`**：官方要求 Python 3.8、PyTorch 1.9.0、CUDA 11.1、MinkowskiEngine。该栈和 PASDF 的 Python 3.10、PyTorch 1.11、CUDA 11.3 不一致，必须隔离。
3. **PTv3/Pointcept 单独环境 `pointcept`**：官方推荐 PyTorch 2.1/2.5、CUDA 11.8/12.4、spconv/torch-geometric/FlashAttention。该栈和 PASDF/PO3AD 都不一致，只能做 P9 扩展。
4. **NumPy 暂时不升级到 2.x**：Open3D 官方文档明确提示 NumPy 2.0 与 Open3D 0.18 及以前存在兼容问题；NumPy 官方也明确 2.0 有二进制兼容破坏。P7 主线建议固定 `numpy<2`，除非单独新环境。
5. **P7-A/P7-B 不需要深度新依赖**：multi-template、registration confidence、positive-aware calibration 可以先用已有几何/分析模块和 scikit-learn 完成。这是最稳的第一步。

## 2. 当前 codebase 基础

当前仓库已有结构：

```text
src/pcdad/
  analysis/       # P4-P6 分析、calibration、failure mode、case study
  data/           # dataset/preprocess
  geometry/       # normals/curvature/neighbors/residuals
  metrics/        # 指标入口
  models/         # pasdf_adapter
  scoring/        # aggregate/geometric
  viz/            # pointcloud visualization

scripts/
  evaluate.py
  export_pasdf_scores.py
  run_geometry_smoke.py
  run_p6_*.py
  visualize_pasdf_scores.py
```

可复用资产：

- `src/pcdad/geometry/residuals.py`：可复用 nearest-neighbor residual。
- `src/pcdad/analysis/pasdf_registration.py`：可复用 cap3 registration diagnostics 思路。
- `src/pcdad/analysis/pasdf_calibration.py`：可复用 top-k/boundary 指标。
- `src/pcdad/analysis/failure_modes.py`：可复用 weak-localization 和 failure closure 口径。
- `scripts/run_p6_targeted_diagnostics.py`：可作为 P7-A targeted diagnostic CLI 的范式。

需要新增的核心能力：

- 多模板 prototype bank。
- registration confidence/uncertainty 的结构化输出。
- positive-aware calibration head。
- pseudo anomaly generation。
- discriminative SDF training utilities。

## 3. P7 推荐代码框架

### 3.1 新增目录

```text
src/pcdad/prototypes/
  __init__.py
  template_bank.py
  registration_confidence.py

src/pcdad/calibration/
  __init__.py
  positive_aware.py

src/pcdad/training/
  __init__.py
  pseudo_anomaly.py
  discriminative_sdf.py

scripts/
  build_template_bank.py
  run_p7_multitemplate.py
  train_p7_calibration.py
  train_p7_discriminative_sdf.py
  run_po3ad_smoke.py

configs/experiment/
  P7_A_multitemplate_cap3.yaml
  P7_A_multitemplate_four_class.yaml
  P7_B_calibration_four_class.yaml
  P7_C_dsdf_helmet1.yaml
  P8_ra_mt_dsdf_four_class.yaml
```

### 3.2 模块职责

| 模块 | 职责 | 依赖等级 |
|---|---|---|
| `template_bank.py` | 加载 normal templates、计算 template assignment、输出 top-k residual | 低 |
| `registration_confidence.py` | 根据 residual/overlap/entropy/bbox/pair ratio 计算 confidence | 低 |
| `positive_aware.py` | boundary margin、positive-aware calibration、score 对照 | 低 |
| `pseudo_anomaly.py` | 法向扰动、patch corruption、registration jitter | 中 |
| `discriminative_sdf.py` | margin loss、训练 step、checkpoint/metrics 管理 | 中高 |
| `run_p7_multitemplate.py` | P7-A CLI | 低 |
| `train_p7_calibration.py` | P7-B CLI | 低 |
| `train_p7_discriminative_sdf.py` | P7-C CLI | 中高 |
| `run_po3ad_smoke.py` | PO3AD 外部环境封装，不 import PO3AD | 高 |

原则：

- `scripts/` 不写核心逻辑。
- 不在 `src/pcdad/analysis/` 继续堆 P7 主逻辑，避免分析模块过载。
- P7-A/P7-B 先保持 CPU/轻 GPU 可跑，P7-C 才引入 torch training。
- 外部 repo 只通过命令行或 adapter 调用，不把第三方源码复制进主包。

### 3.3 核心接口

#### TemplateAssignment

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateAssignment:
    class_name: str
    sample_id: str
    template_id: str
    rank: int
    nn_mean: float
    nn_topk_mean: float
    residual_overlap: float
    bbox_ratio: float
    pair_ratio: float
    assignment_entropy: float
    registration_confidence: float
```

#### RegistrationConfidenceConfig

```python
@dataclass(frozen=True)
class RegistrationConfidenceConfig:
    topk_ratio: float = 0.01
    entropy_weight: float = 0.25
    overlap_weight: float = 0.25
    residual_weight: float = 0.35
    coverage_weight: float = 0.15
    eps: float = 1e-12
```

#### CalibrationRecord

```python
@dataclass(frozen=True)
class CalibrationRecord:
    class_name: str
    sample_id: str
    label: int
    pasdf_score: float
    template_score: float
    registration_confidence: float
    calibrated_score: float
    boundary_margin: float
    failure_reason: str
```

#### PseudoAnomalySpec

```python
@dataclass(frozen=True)
class PseudoAnomalySpec:
    mode: str
    normal_scale: float
    patch_radius: float
    curvature_weight: float
    jitter_scale: float
    seed: int
```

### 3.4 CLI 设计

P7-A：

```bash
PYTHONPATH=src python scripts/run_p7_multitemplate.py \
  --score-root experiments/P5_pasdf_scores/representative \
  --template-root third_party/PASDF/data/ShapeNetAD \
  --classes cap3 tap1 helmet1 ashtray0 \
  --output-dir experiments/P7_A_multitemplate/four_class
```

P7-B：

```bash
PYTHONPATH=src python scripts/train_p7_calibration.py \
  --input-csv experiments/P7_A_multitemplate/four_class/per_sample_scores.csv \
  --classes cap3 tap1 helmet1 ashtray0 \
  --method logistic \
  --output-dir experiments/P7_B_calibration/four_class
```

P7-C：

```bash
PYTHONPATH=src CUDA_VISIBLE_DEVICES=0 python scripts/train_p7_discriminative_sdf.py \
  --class-name helmet1 \
  --pseudo-mode normal_patch \
  --config configs/experiment/P7_C_dsdf_helmet1.yaml \
  --output-dir experiments/P7_C_dsdf/helmet1_smoke
```

### 3.5 实验产物结构

```text
experiments/P7_A_multitemplate/four_class/
  README.md
  config.yaml
  git_hash.txt
  per_sample_scores.csv
  template_assignments.csv
  failure_toplist.csv
  svg/

experiments/P7_B_calibration/four_class/
  README.md
  config.yaml
  git_hash.txt
  calibration_records.csv
  boundary_margin.csv
  metrics.csv

experiments/P7_C_dsdf/helmet1_smoke/
  README.md
  config.yaml
  git_hash.txt
  train.log
  metrics.csv
  checkpoints/
  svg/
```

## 4. 环境分层策略

| 环境 | 用途 | Python | PyTorch/CUDA | 是否改当前主环境 | 说明 |
|---|---|---:|---|---|---|
| `pasdf` | P7-A/P7-B/P7-C 主线 | 3.10 | torch 1.11 + CUDA 11.3 | 小心扩展 | 保留 P3 baseline 可复现性 |
| `po3ad` | PO3AD 官方 smoke | 3.8 | torch 1.9 + CUDA 11.1 | 否 | 必须独立 |
| `pointcept` | PTv3/Pointcept feasibility | 3.8 或 3.10 | torch 2.1/2.5 + CUDA 11.8/12.4 | 否 | P9 扩展 |
| `docs` 可选 | 只做文档/打包 | 系统 Python | 无 | 否 | 非必要 |

环境隔离原因：

- PASDF 当前依赖 PyTorch3D 与 torch 1.11/CUDA 11.3。
- PO3AD 官方 README 指定 Python 3.8、PyTorch 1.9.0、CUDA 11.1、MinkowskiEngine。
- PTv3 官方 README 推荐 CUDA 11.6+、PyTorch 1.12+，开发环境使用 CUDA 11.8/PyTorch 2.1.0；Pointcept 新版 README 示例已到 PyTorch 2.5/CUDA 12.4。
- 这些栈之间没有必要强行统一。

## 5. Package 预研与版本策略

### 5.1 P7 主线环境：沿用 PASDF/PyTorch 1.11

| Package | 当前/建议 | 用途 | 风险 |
|---|---|---|---|
| `python` | `3.10` | 当前 PASDF 环境 | 保持不动 |
| `torch` | `1.11.0` | PASDF、P7-C 训练 smoke | 不升级 |
| `torchvision` | `0.12.0` | torch 配套 | 不升级 |
| `pytorch3d` | `0.7.4` 或当前可用版本 | Chamfer/SDF/PASDF 兼容 | 与 torch/CUDA 强绑定 |
| `numpy` | 建议 `<2.0` | 几何数组、sklearn/scipy | 避免 NumPy 2 ABI 风险 |
| `scipy` | 保守使用当前版本 | KDTree/统计/插值 | 与 NumPy 版本联动 |
| `scikit-learn` | 当前可用即可，建议不要升到 1.7+ | calibration head | 新版要求 Python 3.10+，可兼容但不必升级 |
| `open3d` | 当前可 import 的版本 | PCD IO、可视化、配准 | 0.18 及以前与 NumPy 2 风险 |
| `trimesh` | 当前可用即可 | mesh/OBJ/SDF 辅助 | 基础安装只依赖 NumPy |
| `point-cloud-utils` | 当前可用即可 | mesh/point distance、采样 | 使用 wheel，避免源码编译 |

### 5.2 轻量新增依赖

P7-A/P7-B 原则上不新增重依赖。如果确实需要：

| Package | 建议 | 理由 |
|---|---|---|
| `pandas` | 可选 | 读写 CSV 更方便，但当前可用标准库 `csv` 替代 |
| `matplotlib` | 已有或可选 | SVG/plot 输出 |
| `joblib` | scikit-learn 间接依赖 | 保存 calibration head |

若为保持依赖最小，P7-A/P7-B 可全部用 `numpy + scipy + scikit-learn + csv` 完成。

### 5.3 高风险扩展依赖

| Package/Repo | 用途 | 风险 | 策略 |
|---|---|---|---|
| `MinkowskiEngine` | PO3AD sparse tensor | CUDA/GCC/PyTorch 版本强绑定，issue 多 | 只进 `po3ad` 环境 |
| `Pointcept` | PTv3/Pointcept backbone | PyTorch 2.x、spconv、torch-geometric、FlashAttention | 只进 `pointcept` 环境 |
| `spconv-cu*` | sparse conv | CUDA wheel 后缀必须匹配 | 跟随 Pointcept 官方环境 |
| `torch-scatter/cluster/sparse` | PyG 生态 | 与 torch/CUDA 版本强绑定 | 使用 PyG channel，不混主环境 |
| `flash-attn` | PTv3 加速 | CUDA/PyTorch/GCC 约束严格 | P9 才测试；可禁用 FlashAttention |
| `wandb` | 实验日志 | 网络与账号依赖 | 不作为必需依赖 |

### 5.4 不建议混装的依赖

不要在 `pasdf` 环境中安装：

- PO3AD 依赖的 `MinkowskiEngine`。
- Pointcept/PTv3 依赖的 `spconv-cu*`、PyG CUDA 扩展、FlashAttention。
- 会强制升级 torch/numpy/scipy 的包。
- 未固定版本的 `pip install -U` 大型包。

## 6. 官方 release/install/issue 风险摘要

| 依赖 | 官方资料结论 | 对本项目的影响 |
|---|---|---|
| PyTorch | 官方 previous versions 明确提供 torch 1.11.0 + CUDA 11.3 的 conda/pip 安装命令。 | 当前 PASDF 环境的 torch 栈是合理锚点，不要为 P7-A/P7-B 升级。 |
| PyTorch3D | 官方 INSTALL 说明 PyTorch3D wheel 与 Python/PyTorch/CUDA 组合绑定；PyTorch 重装后常需要重装或重编 PyTorch3D。 | 不动当前 PyTorch3D；如果 torch 变更，必须重建环境。 |
| NumPy 2.x | 官方 migration guide 明确 NumPy 2.0 有二进制兼容破坏。 | P7 主环境固定 `numpy<2` 更稳。 |
| SciPy | 官方 toolchain 说明 SciPy 与 Python/NumPy 版本有明确兼容矩阵。 | 不单独升级 SciPy，跟随当前 NumPy。 |
| Open3D | 0.19 文档支持 Python 3.8-3.12；同时提示 NumPy >=2 需要 Open3D >0.18。 | 若当前 Open3D <=0.18，不升级 NumPy 到 2。 |
| scikit-learn | 官方安装文档列出依赖最小版本；1.7 要求 Python 3.10+。 | P7 calibration 可用 scikit-learn，但不追最新版。 |
| trimesh | 官方说明基础安装只需要 NumPy，其他为 soft dependencies。 | 适合作为低风险几何辅助包。 |
| point-cloud-utils | PyPI 有 cp39/cp310/cp311/cp312 manylinux wheels。 | 使用 wheel 安装，不从源码编译。 |
| PO3AD | 官方 README 使用 Python 3.8、PyTorch 1.9.0、CUDA 11.1、MinkowskiEngine。 | 必须单独 conda env。 |
| MinkowskiEngine | 官方 README 要求 CUDA 版本和 PyTorch CUDA 匹配，并在 GitHub 上有大量安装相关 issue。 | 只作为 P9 强对照依赖，不进主线。 |
| PTv3 | 官方 README 推荐 CUDA 11.6+、PyTorch 1.12+；开发使用 CUDA 11.8/PyTorch 2.1.0，并说明低环境需关闭 FlashAttention。 | PTv3 与 PASDF 主环境不兼容，只做单独环境。 |
| Pointcept | 官方 README 示例使用 PyTorch 2.5/CUDA 12.4、PyG、spconv-cu124 等。 | 不进入 P7 主线，P9 独立 smoke。 |

## 7. 推荐环境矩阵

### 7.1 `pasdf` 主线环境

用途：P7-A/P7-B/P7-C 最小 smoke。

建议：

```text
python=3.10
torch==1.11.0
torchvision==0.12.0
cudatoolkit=11.3
pytorch3d==0.7.4
numpy<2
scipy
scikit-learn
open3d
trimesh
point-cloud-utils
```

原则：

- 不执行 `pip install -U torch numpy scipy open3d`。
- 如果需要新增轻依赖，先 `pip install --dry-run` 或新容器试装。
- 安装后立即 `pip check` 和 import smoke。

### 7.2 `po3ad` 对照环境

用途：P9 PO3AD official smoke。

官方建议：

```text
python=3.8
torch=1.9.0
cudatoolkit=11.1
torchvision
openblas-devel
MinkowskiEngine
```

策略：

- 单独 Docker/conda，不影响 `pasdf`。
- 半天跑不通就记录失败，不阻塞 RA-MT-DSDF。
- 优先使用官方 README 命令，不自行升级 torch。
- MinkowskiEngine 安装参数会随 pip/setuptools 变化；正式执行前必须核对当前官方 README 和本机 pip 版本。

### 7.3 `pointcept` 扩展环境

用途：P9/PTv3 feasibility，不作为 P7 必需。

两个可选栈：

```text
PTv3 repo: python=3.8, torch=2.1.0, CUDA 11.8
Pointcept newer docs: python=3.10, torch=2.5.0, CUDA 12.4
```

策略：

- 若只想拿 PTv3 model.py 做 feature smoke，优先尝试 PTv3 repo 的自包含路径。
- 若用 Pointcept 全框架，直接使用官方 Docker 或独立 env。
- FlashAttention 失败时先关闭，不让它阻塞主线。

## 8. 安装与验证命令草案

### 8.1 P7 主环境新增依赖 smoke

在容器内执行：

```bash
conda activate pasdf
python - <<'PY'
import numpy
import scipy
import sklearn
import open3d
import trimesh
print('numpy', numpy.__version__)
print('scipy', scipy.__version__)
print('sklearn', sklearn.__version__)
print('open3d', open3d.__version__)
print('trimesh', trimesh.__version__)
PY
pip check
```

### 8.2 P7-A 单测命令

```bash
PYTHONPATH=src pytest \
  tests/test_template_bank.py \
  tests/test_registration_confidence.py \
  -q
```

### 8.3 P7-B 单测命令

```bash
PYTHONPATH=src pytest \
  tests/test_positive_aware_calibration.py \
  -q
```

### 8.4 P7-C 单测命令

```bash
PYTHONPATH=src pytest \
  tests/test_pseudo_anomaly.py \
  tests/test_discriminative_sdf.py \
  -q
```

### 8.5 PO3AD 环境 smoke

```bash
conda create -n po3ad python=3.8 -y
conda activate po3ad
conda install -c pytorch -c nvidia -c conda-forge pytorch=1.9.0 cudatoolkit=11.1 torchvision -y
conda install openblas-devel -c anaconda -y
pip install -U git+https://github.com/NVIDIA/MinkowskiEngine -v --no-deps \
  --install-option="--blas_include_dirs=${CONDA_PREFIX}/include" \
  --install-option="--blas=openblas"
python - <<'PY'
import torch
import MinkowskiEngine as ME
print(torch.__version__, torch.version.cuda)
print(ME.__version__)
PY
```

说明：上面的 MinkowskiEngine 安装命令是按官方 README 思路整理的草案。若当前 pip 不再接受 `--install-option`，优先切换到官方最新命令或 `--config-settings`，不要在主 `pasdf` 环境中反复试错。

### 8.6 PTv3 环境 smoke

```bash
conda create -n pointcept python=3.8 -y
conda activate pointcept
conda install ninja -y
conda install pytorch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 pytorch-cuda=11.8 -c pytorch -c nvidia -y
conda install h5py pyyaml -c anaconda -y
conda install sharedarray tensorboard tensorboardx yapf addict einops scipy plyfile termcolor timm -c conda-forge -y
conda install pytorch-cluster pytorch-scatter pytorch-sparse -c pyg -y
pip install torch-geometric
```

## 9. 测试计划

| 测试文件 | 覆盖内容 | 是否需要 GPU |
|---|---|---|
| `tests/test_template_bank.py` | template loading、ranking、entropy | 否 |
| `tests/test_registration_confidence.py` | confidence 公式、边界值、缺字段错误 | 否 |
| `tests/test_positive_aware_calibration.py` | margin、calibration 不抬 positive | 否 |
| `tests/test_pseudo_anomaly.py` | 法向扰动、patch corruption、seed 复现 | 否 |
| `tests/test_discriminative_sdf.py` | margin loss、batch shape、NaN guard | 可 CPU |
| `tests/test_run_p7_multitemplate_cli.py` | CLI dry-run、输出文件 | 否 |

必须坚持：

- P7-A/P7-B 先 TDD，纯函数单测优先。
- 真实实验失败不能用“单测通过”掩盖，stage record 必须写真实指标。
- P7-C 训练 smoke 必须记录 seed、GPU、耗时和 loss 曲线。

## 10. 风险清单与规避策略

| 风险 | 触发条件 | 规避 |
|---|---|---|
| PASDF 环境被破坏 | torch/numpy/open3d 被升级 | 任何安装前先 `conda list --export`，安装后 `pip check` |
| PyTorch3D ABI 不匹配 | torch 或 CUDA 版本变化 | 主环境不升级 torch；新 torch 用新 env |
| NumPy 2 ABI 破坏 | pip 自动升级 NumPy | 固定 `numpy<2` |
| Open3D import 失败 | Open3D 旧版 + NumPy 2 | 降 NumPy 或升 Open3D，但优先降 NumPy |
| MinkowskiEngine 编译失败 | CUDA_HOME/GCC/openblas 不匹配 | 单独 env，按官方命令，失败记录 |
| PTv3 FlashAttention 失败 | CUDA <11.6 或 torch 不匹配 | 关闭 FlashAttention 或独立新环境 |
| scikit-learn 拉高 SciPy/NumPy | pip 安装最新版 | 使用当前版本或 conda 安装，避免 `-U` |
| point-cloud-utils 源码编译 | 没有 wheel 或 Python 版本不匹配 | 使用 cp310 manylinux wheel；否则不升级 |

## 11. 下一步开发顺序

建议顺序：

1. 写 `P7_A_template_bank_and_registration_confidence_plan.md`。
2. 实现 `src/pcdad/prototypes/template_bank.py` 与 `registration_confidence.py`。
3. 跑 `cap3` targeted multi-template smoke。
4. 写 `P7_B_positive_aware_calibration_plan.md`。
5. 实现 `src/pcdad/calibration/positive_aware.py`。
6. 跑四类 calibration smoke。
7. 再决定是否进入 P7-C 的 discriminative SDF training。

这个顺序的好处是：先用低风险模块吃掉 `cap3` 的已知 failure，再决定是否投入 GPU-heavy training。

## 12. References

1. PyTorch previous versions. https://pytorch.org/get-started/previous-versions/
2. PyTorch3D INSTALL.md. https://github.com/facebookresearch/pytorch3d/blob/main/INSTALL.md
3. NumPy 2.0 migration guide. https://numpy.org/doc/stable/numpy_2_0_migration_guide.html
4. SciPy Toolchain Roadmap. https://docs.scipy.org/doc/scipy/dev/toolchain.html
5. Open3D getting started 0.19.0. https://www.open3d.org/docs/release/getting_started.html
6. scikit-learn installing guide. https://scikit-learn.org/stable/install.html
7. trimesh installation docs. https://trimesh.org/install.html
8. point-cloud-utils PyPI release files. https://pypi.org/project/point-cloud-utils/
9. PO3AD official GitHub. https://github.com/yjnanan/PO3AD
10. MinkowskiEngine official GitHub. https://github.com/NVIDIA/MinkowskiEngine
11. Point Transformer V3 official GitHub. https://github.com/Pointcept/PointTransformerV3
12. Pointcept official GitHub README. https://github.com/Pointcept/Pointcept/blob/main/README.md
