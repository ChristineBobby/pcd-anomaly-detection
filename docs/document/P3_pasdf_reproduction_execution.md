# P3 PASDF 复现执行计划与记录

撰写日期：2026-06-08
适用阶段：P3 PASDF 官方权重复现
执行地点：Linux GPU 服务器 + Docker 容器 `boring_goldstine`

---

## 0. 阶段目标

P3 的目标是用 PASDF 官方预处理资产和官方权重，在 P2 产出的
`data/Anomaly-ShapeNet-v2/dataset/16384` 上复现 Anomaly-ShapeNet / ShapeNetAD
基线结果。执行顺序是：

1. 先固定可维护代码接口，只做项目胶水层，不改 `third_party/PASDF` 源码。
2. 先跑 1 类 smoke evaluation，确认环境、官方资产、数据口径和输出链路正确。
3. 再扩展到 40 类全量评估，并沉淀结果表、配置、命令和日志。

P3 不从头训练 PASDF。官方 README 明确提供预处理 SDF 样本与权重时可以跳过 SDF 提取和训练，直接
运行 `Test/AD_test.py`。

---

## 1. Entry 条件复核

### 1.1 P1 环境

当前容器：

```text
container_id: 2114d157b2cf
container_name: boring_goldstine
image: continuumio/miniconda3:latest
repo_mount: /workspace/code_folder/area1/Anomaly
conda_env: pasdf
```

P1 已知在新容器中需要再次确认 Open3D 系统库。若出现：

```text
OSError: libGL.so.1: cannot open shared object file
```

按 P1 执行手册安装：

```bash
apt-get update
apt-get install -y --no-install-recommends libgl1 libgomp1 libc++1
```

随后重新验证：

```bash
conda activate pasdf
python - <<'PY'
import torch
import pytorch3d
import open3d
import pybullet
print("torch", torch.__version__, "cuda", torch.version.cuda, torch.cuda.is_available())
print("pytorch3d", pytorch3d.__version__)
print("open3d", open3d.__version__)
print("pybullet imported")
PY
```

### 1.2 P2 数据

P2 已闭合，P3 使用固定 16,384 点 PASDF 输入目录：

```text
data/Anomaly-ShapeNet-v2/dataset/16384
```

当前实测：

```text
size: 1.2G
classes: 40
pcd_files: 1472
point_count: all 16384
manifest: data/Anomaly-ShapeNet-v2/dataset/16384/preprocess_manifest.json
```

关键口径：

- 输入目录沿用 PASDF 官方 `test_ShapeNetAD.yaml` 的 `normalize: False`。
- P2 已把 GT 转成 PASDF `ShapeNetAD.py` 可读取的空格分隔 `x y z label`。
- P2 对原始 GT/PCD 顺序不一致样本使用坐标最近邻对齐后再采样。

### 1.3 官方 PASDF 资产

PASDF README 要求下载 Google Drive 文件夹：

```text
https://drive.google.com/drive/folders/1-aeND5tZ_dFp-7BhZHPyZSofDgxRTYRQ?usp=sharing
```

放置到：

```text
third_party/PASDF/data/ShapeNetAD
third_party/PASDF/results/ShapeNetAD/runs_sdf/
third_party/PASDF/results/ShapeNetAD/samples_dict_ShapeNetAD.npy
```

最低可运行检查：

```bash
test -d third_party/PASDF/data/ShapeNetAD
test -f third_party/PASDF/results/ShapeNetAD/runs_sdf/settings.yaml
test -d third_party/PASDF/results/ShapeNetAD/runs_sdf/ashtray0
test -f third_party/PASDF/results/ShapeNetAD/runs_sdf/ashtray0/weights.pt
```

`data/`、`results/`、`*.pt`、`*.npy` 均不入 git。

---

## 2. 架构与接口规划

P3 只在本项目中新增 PASDF 适配层。第三方评估逻辑保持官方实现，所有可变项通过生成 YAML 控制。

### 2.1 文件职责

```text
src/pcdad/models/pasdf_adapter.py
```

职责：

- 定义 ShapeNetAD 官方 40 类顺序。
- 生成 PASDF 官方 `Test/AD_test.py` 可直接读取的 YAML dict。
- 将 YAML 写入实验目录，避免修改 `third_party/PASDF/config_files/test_ShapeNetAD.yaml`。
- 生成可审计的 subprocess 命令。
- 读取官方 `evaluation_results.csv`，输出结构化结果。

```text
scripts/evaluate.py
```

职责：

- 保持薄 CLI，只解析参数和调用 `pcdad.models.pasdf_adapter`。
- 支持 `--dry-run` 只生成配置和命令，不启动官方推理。
- 支持 `--classes ashtray0 ...` 做 smoke eval。
- 支持 `--dataset-dir`、`--pasdf-root`、`--output-dir` 覆盖本地路径。

```text
tests/test_pasdf_adapter.py
```

职责：

- 测配置生成字段、路径口径、类别过滤和 CSV 解析。
- 不 import PASDF，不下载权重，不跑 GPU。

```text
tests/test_evaluate.py
```

职责：

- 测 CLI dry-run 行为，确保脚本只做薄封装。

```text
docs/document/P3_pasdf_reproduction_execution.md
```

职责：

- 记录 P3 的设计、命令、执行状态、阻塞和验证证据。

### 2.2 数据结构

```python
@dataclass(frozen=True)
class PasdfPaths:
    pasdf_root: Path
    dataset_dir: Path
    output_dir: Path
    template_path: str = "data/ShapeNetAD"
    checkpoint_path: str = "results/ShapeNetAD/runs_sdf/"
    settings_path: str = "results/ShapeNetAD/runs_sdf/settings.yaml"
```

`template_path`、`checkpoint_path`、`settings_path` 保持 PASDF 官方相对路径，因为官方源码会基于
`third_party/PASDF/Test` 拼接这些字段。`dataset_dir` 和 `output_dir` 写成绝对路径，避免工作目录变化
导致结果落错位置。

```python
@dataclass(frozen=True)
class PasdfEvalOptions:
    classes: tuple[str, ...]
    seed: int = 42
    device: str = "cuda"
    batch_size: int = 1
    num_workers: int = 0
    voxel_size: float = 0.03
    top_k: int = 1
    shuffle: bool = False
    cd_threshold: float = 1.6
    normalize: bool = False
    scale_factor: float = 1.0
```

```python
@dataclass(frozen=True)
class PasdfEvaluationResult:
    class_name: str
    pixel_auc: float
    object_auc: float
```

### 2.3 函数接口

```python
def normalize_shape_net_classes(classes: Iterable[str] | None) -> tuple[str, ...]:
    """Return validated ShapeNetAD class names in requested order or the official 40-class order."""
```

验证规则：

- `classes is None`：返回官方 40 类。
- 空列表：抛 `ValueError("At least one ShapeNetAD class is required")`。
- 类名不在官方 40 类：抛 `ValueError("Unknown ShapeNetAD classes: ...")`。

```python
def build_shapenetad_eval_config(paths: PasdfPaths, options: PasdfEvalOptions) -> dict[str, Any]:
    """Build a PASDF-compatible ShapeNetAD evaluation YAML payload."""
```

输出字段与官方 `config_files/test_ShapeNetAD.yaml` 对齐：

```yaml
seed: 42
device: cuda
dataset:
  name: ShapeNetAD
  dataset_dir: /abs/path/to/data/Anomaly-ShapeNet-v2/dataset/16384
  cls_name: [ashtray0]
  normalize: false
  scale_factor: 1.0
  template_path: data/ShapeNetAD
infer:
  batch_size: 1
  num_workers: 0
  voxel_size: 0.03
  top_k: 1
  shuffle: false
  cd_threshold: 1.6
  checkpoint_path: results/ShapeNetAD/runs_sdf/
  output_dir: /abs/path/to/experiments/E1_pasdf_baseline/smoke_ashtray0
  settings_path: results/ShapeNetAD/runs_sdf/settings.yaml
```

```python
def write_eval_config(config: Mapping[str, Any], path: str | Path) -> Path:
    """Create parent directories and safe-dump YAML with stable key order."""
```

```python
def build_pasdf_command(pasdf_root: str | Path, config_path: str | Path, python: str = "python") -> list[str]:
    """Return the command that runs official PASDF evaluation from pasdf_root."""
```

```python
def parse_evaluation_results(path: str | Path) -> tuple[PasdfEvaluationResult, ...]:
    """Read PASDF evaluation_results.csv and validate required columns."""
```

```python
def summarize_results(results: Iterable[PasdfEvaluationResult]) -> dict[str, float]:
    """Return mean_pixel_auc, mean_object_auc, and class_count."""
```

### 2.4 CLI 设计

默认命令：

```bash
PYTHONPATH=src python scripts/evaluate.py \
  --config configs/experiment/E1_pasdf_baseline.yaml \
  --classes ashtray0 \
  --output-dir experiments/E1_pasdf_baseline/smoke_ashtray0
```

只生成配置不运行：

```bash
PYTHONPATH=src python scripts/evaluate.py \
  --config configs/experiment/E1_pasdf_baseline.yaml \
  --classes ashtray0 \
  --output-dir experiments/E1_pasdf_baseline/smoke_ashtray0 \
  --dry-run
```

容器内真实 smoke eval：

```bash
docker exec 2114d157b2cf bash -lc '
cd /workspace/code_folder/area1/Anomaly
conda activate pasdf
PYTHONPATH=src python scripts/evaluate.py \
  --config configs/experiment/E1_pasdf_baseline.yaml \
  --classes ashtray0 \
  --output-dir experiments/E1_pasdf_baseline/smoke_ashtray0
'
```

全量 40 类：

```bash
docker exec 2114d157b2cf bash -lc '
cd /workspace/code_folder/area1/Anomaly
conda activate pasdf
PYTHONPATH=src python scripts/evaluate.py \
  --config configs/experiment/E1_pasdf_baseline.yaml \
  --output-dir experiments/E1_pasdf_baseline/full_40cls
'
```

---

## 3. 执行计划

### Task 1：固化 P3 适配层文档

- [x] 创建本文件，明确 P3 范围、接口、执行命令、DoD。
- [x] 更新 `docs/document/README.md`，加入 P3 文档索引。

### Task 2：TDD 实现 PASDF adapter

- [x] 先写 `tests/test_pasdf_adapter.py`，覆盖类别验证、YAML 字段、命令生成、CSV 解析。
- [x] 运行目标测试，确认失败原因是模块未实现。
- [x] 实现 `src/pcdad/models/pasdf_adapter.py`。
- [x] 运行目标测试并通过。

### Task 3：TDD 实现 evaluate CLI

- [x] 先写 `tests/test_evaluate.py`，覆盖 `--dry-run` 生成 YAML 和命令输出。
- [x] 运行目标测试，确认失败原因是当前 placeholder。
- [x] 改造 `scripts/evaluate.py` 为薄 CLI。
- [x] 运行目标测试并通过。

### Task 4：当前容器环境验证

- [x] 安装当前容器缺失的 Open3D 系统库。
- [x] 验证 `torch/pytorch3d/open3d/pybullet` import。
- [x] 验证 CUDA matmul。
- [x] 验证 PyTorch3D chamfer CUDA op。

### Task 5：官方资产获取与校验

- [x] 检查容器代理：当前容器 proxy 指向 `127.0.0.1:7890`，若下载失败，改用宿主反向端口
  `127.0.0.1:7891`。
- [x] 下载并校验 `third_party/PASDF/data/ShapeNetAD`。
- [x] 下载并校验 smoke 所需 `runs_sdf/settings.yaml` 和 `ashtray0/weights.pt`。
- [x] 批量下载剩余 39 类 `weights.pt`，用于 full 40-class evaluation。

### Task 6：1 类 smoke eval

- [x] 生成 `experiments/E1_pasdf_baseline/smoke_ashtray0/pasdf_test_ShapeNetAD.yaml`。
- [x] 运行官方 `python Test/AD_test.py --config <generated-yaml>`。
- [x] 记录 stdout/stderr 到 `experiments/E1_pasdf_baseline/smoke_ashtray0/run.log`。
- [x] 读取 `evaluation_results.csv`，记录 pixel/object AUROC。

### Task 7：全量 40 类评估

- [x] 生成 `experiments/E1_pasdf_baseline/full_40cls/pasdf_test_ShapeNetAD.yaml`。
- [x] 运行官方 40 类评估。
- [x] 输出 `evaluation_results.csv` 和 mean 汇总。
- [x] 若单类失败，保留完整日志，标注失败类别和原因。

### Task 8：质量门

- [x] `make lint` 等价命令：`ruff check .`、`black --check .`、`mypy src/pcdad`
- [x] `make test` 等价命令：`PYTHONPATH=src pytest -q`
- [x] `pre-commit run --all-files`
- [x] 更新本文档执行状态与验证证据。

---

## 4. DoD

P3 smoke DoD：已完成。

- 当前 Docker 容器能 import PASDF 评估所需包，CUDA 和 PyTorch3D smoke 均通过。
- 官方 PASDF 资产已放置并校验。
- `scripts/evaluate.py --dry-run --classes ashtray0` 能生成可审计 YAML 和官方命令。
- `ashtray0` 真实评估跑完，`evaluation_results.csv` 可解析。

P3 full DoD：已完成。

- 官方 40 类评估跑完。
- 结果表包含每类 `pixel_auc` 与 `object_auc`。
- mean O-AUROC 与论文指标差距可解释。
- 配置、命令、日志路径和关键结论记录在本文档中。

---

## 5. 当前执行记录

### 2026-06-08 初始复核

仓库状态：

```text
branch: main
remote: origin/main
working_tree: clean before P3 edits
```

P2 产物：

```text
data/Anomaly-ShapeNet-v2/dataset/16384 size: 1.2G
class dirs: 40
pcd files: 1472
```

当前容器代理：

```text
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

注意：用户常用宿主反向代理端口是 `7891`。Google Drive 下载失败时，先改容器内 proxy 到
`127.0.0.1:7891` 后重试。

### 2026-06-08 环境验证

当前容器首次 import Open3D 报：

```text
OSError: libGL.so.1: cannot open shared object file: No such file or directory
```

处理：

```bash
docker exec -u root 2114d157b2cf bash -lc \
  'apt-get update && apt-get install -y --no-install-recommends libgl1 libgomp1 libc++1'
```

验证结果：

```text
torch 1.11.0 cuda 11.3 True
pytorch3d 0.7.4
open3d 0.18.0
pybullet imported
matmul ok (3, 3) NVIDIA GeForce RTX 4090 (8, 9)
pytorch3d chamfer ok 0.1692332625389099
```

### 2026-06-08 TDD 与代码接口

新增：

```text
src/pcdad/models/pasdf_adapter.py
tests/test_pasdf_adapter.py
tests/test_evaluate.py
```

改造：

```text
scripts/evaluate.py
```

红灯记录：

```text
tests/test_pasdf_adapter.py 初次失败：ModuleNotFoundError: pcdad.models.pasdf_adapter
tests/test_evaluate.py 初次失败：evaluate.py 不识别 --pasdf-root/--classes/--output-dir/--dry-run
```

绿灯记录：

```bash
docker exec 2114d157b2cf bash -lc \
  'cd /workspace/code_folder/area1/Anomaly && conda activate pasdf && \
   PYTHONPATH=src pytest tests/test_pasdf_adapter.py tests/test_evaluate.py -q'
```

结果：

```text
9 passed in 0.05s
```

### 2026-06-08 官方资产下载记录

`data/ShapeNetAD` 下载命令：

```bash
gdown --folder --continue \
  "https://drive.google.com/drive/folders/1EwgkUo_mxJvF5EFjh6ZIIp3i7MdtzUBB" \
  -O third_party/PASDF/data/
```

校验：

```text
third_party/PASDF/data/ShapeNetAD size: 148M
class dirs: 40
obj files: 40
ashtray0_template0.obj: present
```

注意：

- 直接下载顶层 Google Drive folder 并指定 `-O third_party/PASDF/` 时，`gdown` 会自动创建一层
  `third_party/PASDF/PASDF/`，目录层级不适合直接使用。本次已删除该误下载目录。
- `gdown --folder` 下载 `results/ShapeNetAD` 时在第一个 `optimizer_model_state.pt` 上失败。真实评估不
  需要 optimizer state，因此 smoke eval 改用单文件 ID 下载 `settings.yaml` 和 `ashtray0/weights.pt`。
- 单文件下载需要加 `--no-cookies`，否则 `gdown` 会报 public link 获取失败。

smoke 资产下载：

```bash
gdown --no-cookies --continue 1W2Yu9Bh4x0pEckwWwydzN_SYVnKXGClQ \
  -O third_party/PASDF/results/ShapeNetAD/runs_sdf/settings.yaml
gdown --no-cookies --continue 1t6uqb9ppPkDcIlPS_nuNSUY02qe_8j2S \
  -O third_party/PASDF/results/ShapeNetAD/runs_sdf/ashtray0/weights.pt
```

校验：

```text
third_party/PASDF/results/ShapeNetAD/runs_sdf/settings.yaml size: 374
third_party/PASDF/results/ShapeNetAD/runs_sdf/ashtray0/weights.pt size: 1,593,699
torch.load(weights.pt, map_location="cpu"): OrderedDict, 22 tensors
```

### 2026-06-08 `ashtray0` smoke eval

Dry-run：

```bash
PYTHONPATH=src python scripts/evaluate.py \
  --config configs/experiment/E1_pasdf_baseline.yaml \
  --classes ashtray0 \
  --output-dir experiments/E1_pasdf_baseline/smoke_ashtray0 \
  --dry-run
```

生成配置：

```text
experiments/E1_pasdf_baseline/smoke_ashtray0/pasdf_test_ShapeNetAD.yaml
```

真实运行：

```bash
PYTHONPATH=src CUDA_VISIBLE_DEVICES=0 python scripts/evaluate.py \
  --config configs/experiment/E1_pasdf_baseline.yaml \
  --classes ashtray0 \
  --output-dir experiments/E1_pasdf_baseline/smoke_ashtray0
```

输出：

```text
experiments/E1_pasdf_baseline/smoke_ashtray0/run.log
experiments/E1_pasdf_baseline/smoke_ashtray0/evaluation_results.csv
```

结果：

```csv
class,pixel_auc,object_auc
ashtray0,0.9184445496911406,1.0
```

官方脚本实测跑了 `ashtray0` 的 29 个 test PCD 样本，无异常退出。

### 2026-06-08 full 40-class 权重下载

权重 ID 提取：

```bash
awk '/^Retrieving folder / {cls=$NF} /^Processing file .* weights\.pt$/ {print cls "\t" $3}' \
  experiments/env_logs/20260608_pasdf_shapenetad_results_gdown.log \
  > experiments/env_logs/20260608_pasdf_shapenetad_weight_ids.tsv
```

校验：

```text
weight ids: 40
```

批量下载命令：

```bash
awk '{print $1, $2}' experiments/env_logs/20260608_pasdf_shapenetad_weight_ids.tsv | \
while read cls file_id; do
  out="third_party/PASDF/results/ShapeNetAD/runs_sdf/${cls}/weights.pt"
  mkdir -p "$(dirname "$out")"
  if [ -s "$out" ]; then
    echo "SKIP $cls $(stat -c%s "$out")"
    continue
  fi
  gdown --no-cookies --continue "$file_id" -O "$out"
done 2>&1 | tee experiments/env_logs/20260608_pasdf_shapenetad_weights_batch_gdown.log
```

权重校验：

```text
weights.pt files: 40
all weights.pt size: 1,593,699 bytes
runs_sdf size: 62M
torch.load(ashtray0/vase9 weights): OrderedDict, 22 tensors
```

### 2026-06-08 full 40-class evaluation

命令：

```bash
PYTHONPATH=src CUDA_VISIBLE_DEVICES=0 python scripts/evaluate.py \
  --config configs/experiment/E1_pasdf_baseline.yaml \
  --output-dir experiments/E1_pasdf_baseline/full_40cls
```

输出：

```text
experiments/E1_pasdf_baseline/full_40cls/pasdf_test_ShapeNetAD.yaml
experiments/E1_pasdf_baseline/full_40cls/run.log
experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv
```

结果摘要：

```text
classes: 40
mean_pixel_auc: 0.896009030694
mean_object_auc: 0.900214149779
min_pixel: helmet1 = 0.6227453698428423
min_object: cap3 = 0.5508771929824561
max_pixel: bowl0 = 0.9680143724369973
max_object: 多类达到 1.0，首个为 ashtray0
```

结果文件首尾校验：

```text
evaluation_results.csv size: 1651 bytes
run.log size: 355764 bytes
AUROC rows in run.log: 40
```

说明：

- mean object AUROC `0.900214` 与 SOP 中论文 O-AUROC 90.0 的目标一致。
- mean pixel AUROC `0.896009` 可作为 P4/P5 几何增强的 P-AUROC baseline。
- 部分类别 object AUROC 偏低，例如 `cap3=0.5509`、`cap4=0.6281`。这些类别应在后续误差分析中优先检查
  registration、voxel size 和模板匹配。

完整 40 类结果表：

| Class | Pixel AUROC | Object AUROC |
|---|---:|---:|
| ashtray0 | 0.921846 | 1.000000 |
| bag0 | 0.938900 | 0.980952 |
| bottle0 | 0.949622 | 1.000000 |
| bottle1 | 0.933604 | 1.000000 |
| bottle3 | 0.939708 | 1.000000 |
| bowl0 | 0.968014 | 1.000000 |
| bowl1 | 0.905584 | 0.985185 |
| bowl2 | 0.816268 | 1.000000 |
| bowl3 | 0.933009 | 1.000000 |
| bowl4 | 0.917347 | 0.992593 |
| bowl5 | 0.905312 | 0.891228 |
| bucket0 | 0.870027 | 0.965079 |
| bucket1 | 0.907215 | 0.857143 |
| cap0 | 0.947014 | 0.881481 |
| cap3 | 0.846928 | 0.550877 |
| cap4 | 0.863803 | 0.628070 |
| cap5 | 0.899016 | 0.796491 |
| cup0 | 0.949613 | 0.876190 |
| cup1 | 0.884425 | 0.842857 |
| eraser0 | 0.928919 | 0.833333 |
| headset0 | 0.857644 | 1.000000 |
| headset1 | 0.836092 | 0.861905 |
| helmet0 | 0.819070 | 0.855072 |
| helmet1 | 0.622745 | 0.957143 |
| helmet2 | 0.834360 | 0.776812 |
| helmet3 | 0.948183 | 0.860606 |
| jar0 | 0.948482 | 1.000000 |
| microphone0 | 0.907773 | 0.780952 |
| shelf0 | 0.859357 | 0.791304 |
| tap0 | 0.890841 | 0.851515 |
| tap1 | 0.903394 | 0.766667 |
| vase0 | 0.950879 | 1.000000 |
| vase1 | 0.829644 | 0.952381 |
| vase2 | 0.950860 | 1.000000 |
| vase3 | 0.892182 | 0.809091 |
| vase4 | 0.898047 | 0.903030 |
| vase5 | 0.920669 | 1.000000 |
| vase7 | 0.946034 | 1.000000 |
| vase8 | 0.933713 | 0.906061 |
| vase9 | 0.864220 | 0.854545 |

### 2026-06-08 质量门

当前 Docker 容器未安装 `make`：

```text
bash: line 1: make: command not found
```

因此按 Makefile 展开执行等价命令。

Lint 等价命令：

```bash
ruff check .
black --check .
mypy src/pcdad
```

结果：

```text
ruff: All checks passed!
black: 23 files would be left unchanged.
mypy: Success: no issues found in 12 source files
```

Test 等价命令：

```bash
PYTHONPATH=src pytest -q
```

结果：

```text
28 passed in 1.90s
```

Pre-commit：

```bash
pre-commit run --all-files
```

结果：

```text
trim trailing whitespace Passed
fix end of files Passed
check yaml Passed
check toml Passed
check for added large files Passed
ruff Passed
ruff-format Passed
black Passed
nbstripout Skipped
```
