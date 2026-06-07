# P1 环境配置执行手册

撰写日期：2026-06-07
适用阶段：P1 环境搭建
执行地点：Linux GPU 服务器 + Docker/Conda 容器
主目标：优先打通 PASDF 官方权重评估环境；PO3AD 单独排期，绝不阻塞主线。

---

## 0. 总原则

1. **主力环境和对照环境必须隔离**：PASDF 不依赖 MinkowskiEngine；PO3AD 依赖
   MinkowskiEngine。两者不能装在同一个 conda 环境里。
2. **先评估，后训练**：PASDF 官方 README 提供预处理 SDF 样本和权重。P1/P3 的第一目标是
   “下载权重 + import 检查 + 1-2 类评估”，不是从头训练。
3. **先按官方锁定版本复现，再处理 4090 兼容分支**：官方 PASDF `install.sh` 强制安装
   PyTorch 1.11.0 + CUDA 11.3 + PyTorch3D 0.7.4。这个组合在 conda 频道可解，但 RTX
   4090 属于 Ada / compute capability 8.9，CUDA 11.8 才正式引入 Ada Lovelace GPU 家族支持。
   因此 P1 必须设置运行时验证门槛，不能只以 “import 成功” 作为完成。
4. **Docker 负责运行环境，宿主负责 GitHub 凭据**：容器用于 conda、依赖、训练、评估、测试；
   `git push/pull/fetch` 优先在宿主终端执行。
5. **所有命令、失败日志和环境锁必须落盘**：环境搭建日志放到
   `experiments/env_logs/`，最终锁文件提交到仓库根目录的 `environment.yml` 和
   `requirements-lock.txt`。

---

## 1. 当前服务器与容器基线

已实测容器：`upbeat_jemison`，镜像 `continuumio/miniconda3:latest`。实际执行时容器名可能变化，
建议先设置变量：

```bash
export CONTAINER=upbeat_jemison
```

```bash
docker exec "$CONTAINER" bash -lc 'nvidia-smi'
```

硬件观测：

- GPU：7 张 NVIDIA GeForce RTX 4090
- 单卡显存：约 49140 MiB
- 驱动：580.159.03
- Driver CUDA capability：13.0

容器观测：

```bash
docker exec "$CONTAINER" bash -lc 'conda --version; conda info --envs'
```

- `conda 26.1.1`
- base Python 是 3.13，不适合直接跑本项目；必须创建独立 conda 环境。

---

## 2. 资料核实摘要

### 2.1 PASDF 官方仓库

仓库：`https://github.com/ZZZBBBZZZ/PASDF`

当前 `master` HEAD（2026-06-07 查询）：

```text
fea90dbce1998ef7bda266e388c34a6079c1bc5e
```

关键文件：

- `README.md`
- `install.sh`
- `environment_linux.yaml`
- `config_files/test_ShapeNetAD.yaml`
- `config_files/voxel_sizes.yaml`

PASDF README 明确流程：

- `conda create -n PASDF python=3.10`
- `bash install.sh PASDF`
- 下载 Google Drive 中的 `data/` 和 `results/`
- 若已有预处理 SDF 和权重，可跳过 SDF 提取与训练，直接运行
  `python Test/AD_test.py --config config_files/test_ShapeNetAD.yaml`

PASDF `install.sh` 行为：

```bash
pip install -e .
conda env update -n $env_name --file environment_linux.yaml
conda install pytorch==1.11.0 torchvision==0.12.0 torchaudio==0.11.0 cudatoolkit=11.3 -c pytorch
conda install pytorch3d==0.7.4 -c pytorch3d
```

PASDF `environment_linux.yaml` 关键锁：

- Python 3.10.9
- PyTorch 1.11.0
- torchvision 0.12.0
- torchaudio 0.11.0
- cudatoolkit 11.3.1
- PyTorch3D 0.7.4
- numpy 1.23.5
- point-cloud-utils 0.29.6
- scikit-image 0.21.0
- scipy 1.11.1
- trimesh 3.22.4
- pybullet 3.2.5

注意：PASDF 环境文件没有显式列出 Open3D，但 PASDF 当前代码的 `Test/infer.py`、
`dataset/*.py`、`utils/utils_process.py` 都直接 `import open3d`。P1 必须把 `open3d`
列为官方评估必需依赖，而不是可选可视化依赖。

### 2.2 PyTorch 与 PyTorch3D

PyTorch 官方 previous versions 页面确认 PyTorch 1.11.0 支持 CUDA 11.3 安装口径。

本机 conda 查询已确认这些包在公开 channel 中存在：

- `pytorch 1.11.0 py3.10_cuda11.3_cudnn8.2.0_0`
- `torchvision 0.12.0 py310_cu113`
- `pytorch3d 0.7.4 py310_cu113_pyt1110`

这说明 PASDF 官方锁在 Python 3.10 + CUDA 11.3 + PyTorch3D 0.7.4 上**可以解包**。

PyTorch3D 安装文档的风险点：

- PyTorch3D 有 CUDA/C++ 扩展，GPU 支持依赖 PyTorch/CUDA 匹配。
- 若从源码构建，PyTorch3D 安装文档要求 CUDA 版本与 PyTorch 支持版本一致；CUDA < 11.7
  源码构建还可能涉及 CUB。
- 文档提到旧版 wheel 示例覆盖 Python 3.8/3.9；但 conda channel 已查到 py310/cu113/pyt1110
  构建，所以 P1 优先走 conda 包，不走源码编译。

### 2.3 RTX 4090 / Ada 风险

NVIDIA CUDA GPUs 页面显示 RTX 4090 属于 Ada 一代，compute capability 8.9。NVIDIA CUDA
11.8 release notes 写明 CUDA 11.8 引入 Hopper 和 Ada Lovelace GPU 家族支持。

结论：

- PASDF 官方 CUDA 11.3 环境**可能可以 import**，也可能在实际 CUDA kernel 运行时报
  `no kernel image is available for execution on the device` 或类似架构不兼容问题。
- 不能在安装前直接改成 CUDA 11.8，因为 PASDF 锁依赖 PyTorch3D 0.7.4 + PyTorch 1.11；
  PyTorch3D 的兼容矩阵和 PASDF 代码需要先验证。
- 正确策略是设置两条路径：
  - 路径 A：官方锁，目标是复现论文环境。
  - 路径 B：4090 兼容锁，仅在路径 A 出现 GPU kernel 架构错误时启用。

### 2.4 PO3AD / MinkowskiEngine

PO3AD 仓库：`https://github.com/yjnanan/PO3AD`

PO3AD README 指定环境：

- Python 3.8
- PyTorch 1.9.0
- CUDA toolkit 11.1
- RTX 3090 上运行
- 依赖 MinkowskiEngine

PO3AD README 安装片段：

```bash
conda create -n PO3AD python=3.8
conda activate PO3AD
conda install -c pytorch -c nvidia -c conda-forge pytorch=1.9.0 cudatoolkit=11.1 torchvision
conda install openblas-devel -c anaconda
pip install -U git+https://github.com/NVIDIA/MinkowskiEngine -v --no-deps \
  --install-option="--blas_include_dirs=${CONDA_PREFIX}/include" \
  --install-option="--blas=openblas"
```

MinkowskiEngine 官方 README 强调：

- CUDA 版本必须和 PyTorch 使用的 CUDA 版本匹配。
- 安装需要 `openblas`、`ninja` 和编译工具链。
- PyTorch 1.8/1.9 + CUDA 11 的历史安装问题建议用 conda 路线。
- 稀疏卷积输入点数变化会造成 PyTorch 显存缓存碎片，必要时要定期 `torch.cuda.empty_cache()`。

MinkowskiEngine issue 风险：

- #619：PyTorch 1.9.0 与 `openblas-devel`/`nomkl` 可能出现 MKL/OpenBLAS solver 冲突。
- #629：`numpy.distutils.system_info` 与 BLAS 参数检测报错，建议 `python setup.py install --blas=openblas --force_cuda`。
- #617：`setup.py install`、`easy_install` 等旧安装路径在新 setuptools/pip 下容易触发弃用/构建问题。
- #633：PyTorch 2.x + CUDA 12.x 虽可能编译，但性能可能比 PyTorch 1.9 + CUDA 11.x 慢。

结论：PO3AD 是对照锚点，不是主力。MinkowskiEngine 若半天内不通，记录失败日志，先用论文报告值
作为对照，不阻塞 PASDF。

---

## 3. 推荐目录与日志

本项目仓库：

```bash
cd /workspace/code_folder/area1/Anomaly
```

建议数据和权重路径：

```text
data/
├── anomaly_shapenet/
├── pasdf_artifacts/
│   ├── data/
│   └── results/
└── checkpoints/
```

环境日志：

```text
experiments/env_logs/
├── 20260607_pasdf_official_create.log
├── 20260607_pasdf_official_import.log
├── 20260607_pasdf_official_gpu_smoke.log
├── 20260607_po3ad_attempt.log
└── README.md
```

`experiments/` 默认 git-ignored。若需要长期保留关键失败日志，应复制摘要到 `docs/document/` 或后续
P1 汇报文档中。

---

## 4. PASDF 环境路径 A：官方锁优先

### 4.1 创建环境

在容器中执行：

```bash
docker exec -it "$CONTAINER" bash
cd /workspace/code_folder/area1/Anomaly
mkdir -p experiments/env_logs

conda create -n pasdf python=3.10 -y 2>&1 | tee experiments/env_logs/20260607_pasdf_create.log
conda activate pasdf
python --version
```

预期：

```text
Python 3.10.x
```

### 4.2 添加 PASDF submodule

优先在宿主终端执行，因为 submodule add 需要访问 GitHub，宿主通常已经配置凭据和代理；push 也仍在
宿主执行。容器内只建议做 `git status`、`git diff`、`git log` 这类本地状态查询。

```bash
git submodule add https://github.com/ZZZBBBZZZ/PASDF.git third_party/PASDF
git submodule update --init --recursive
git -C third_party/PASDF rev-parse HEAD
```

记录 commit。2026-06-07 调研时 `master` 为：

```text
fea90dbce1998ef7bda266e388c34a6079c1bc5e
```

若 `git submodule add` 因网络慢失败，可先用 GitHub API/zip 下载排查，但最终 P0/P1 DoD 要求仍是
submodule 钉死 commit。

### 4.3 安装 PASDF 官方依赖

优先用官方脚本：

```bash
cd third_party/PASDF
bash install.sh pasdf 2>&1 | tee ../../experiments/env_logs/20260607_pasdf_install_official.log
```

如果 `install.sh` 中的 `pip install -e .` 因 PASDF 没有 `setup.py` 或 `pyproject.toml` 失败，不要
马上改第三方源码。改用手动路径：

```bash
conda env update -n pasdf --file environment_linux.yaml
conda install -n pasdf pytorch==1.11.0 torchvision==0.12.0 torchaudio==0.11.0 cudatoolkit=11.3 -c pytorch -y
conda install -n pasdf pytorch3d==0.7.4 -c pytorch3d -y
```

再回到仓库根目录，把 `third_party/PASDF` 加到 `PYTHONPATH` 做 import 验证：

```bash
cd /workspace/code_folder/area1/Anomaly
export PYTHONPATH="$PWD/third_party/PASDF:$PYTHONPATH"
```

### 4.3.1 本次实测修正记录

2026-06-07 在 `continuumio/miniconda3:latest` / Debian 13 容器 `upbeat_jemison`
中，官方脚本因为网络和依赖解析问题未直接跑完，改为手动安装。为了减少大包下载冲突，conda/pip
下载 PyTorch、PyTorch3D、Open3D、PyBullet 等大包时显式关闭代理并使用清华镜像；Git 操作仍在宿主机执行。

实测可用核心锁：

- Python 3.10.20
- PyTorch 1.11.0 / torchvision 0.12.0 / torchaudio 0.11.0 / cudatoolkit 11.3.1
- PyTorch3D 0.7.4，构建为 `py310_cu113_pyt1110`
- numpy 1.23.5
- mkl 2021.4.0 / intel-openmp 2021.4.0
- open3d 0.18.0
- point-cloud-utils 0.29.6
- pysdf 0.1.9
- scikit-image 0.21.0 / scipy 1.11.1 / scikit-learn 1.5.2
- trimesh 3.22.4
- pybullet 3.2.6

关键处理：

- `torch` 首次 import 遇到 `libtorch_cpu.so: cannot enable executable stack`，对当前环境内
  `libtorch_cpu.so` 清除了 `PT_GNU_STACK` 的 executable 标志，并保留
  `.bak_noexecstack` 备份。换新环境时若复现同样错误，需要重复该补丁。
- `torch` 随后遇到 `undefined symbol: iJIT_NotifyEvent`，根因是旧 PyTorch 1.11 与新
  `mkl/intel-openmp 2025` 不兼容；降级到 `mkl=2021.4.0`、`intel-openmp=2021.4.0`、
  `numpy=1.23.5` 后通过。
- PyPI 当前没有 `pybullet==3.2.5` 的 Python 3.10 manylinux wheel；为避免在该基础容器中源码编译，
  实测改用 `pybullet==3.2.6`。PASDF 使用到的是常规 pybullet API，import smoke test 已通过。
- `pysdf==0.1.9` 用 conda-forge 安装，避免 pip 源码编译。
- `meshplot=0.4.0` 用 conda-forge 安装；Python package metadata 会显示 `0.3.3`，这是上游包元数据差异。

Debian 13 容器还需要 Open3D 运行时系统库：

```bash
apt-get update
apt-get install -y --no-install-recommends libgl1 libgomp1 libc++1
```

实测安装后关键系统包版本：

```text
libc++1=1:19.0-63
libc++1-19=1:19.1.7-3+b1
libc++abi1-19=1:19.1.7-3+b1
libgl1=1.7.0-1+b2
libgl1-mesa-dri=25.0.7-2
libglvnd0=1.7.0-1+b2
libglx0=1.7.0-1+b2
libgomp1=14.2.0-19
```

### 4.4 安装项目开发依赖

PASDF 环境用于运行主线，也应能运行本项目最小测试：

```bash
cd /workspace/code_folder/area1/Anomaly
python -m pip install -e ".[dev]" 2>&1 | tee experiments/env_logs/20260607_project_dev_install.log
```

### 4.5 Import 验证

```bash
python - <<'PY' 2>&1 | tee experiments/env_logs/20260607_pasdf_import.log
import sys
import torch
import torchvision
import pytorch3d
import numpy
import trimesh
import skimage
import point_cloud_utils as pcu

print("python", sys.version)
print("torch", torch.__version__)
print("torch cuda", torch.version.cuda)
print("cuda available", torch.cuda.is_available())
print("device count", torch.cuda.device_count())
print("torchvision", torchvision.__version__)
print("pytorch3d", pytorch3d.__version__)
print("numpy", numpy.__version__)
print("trimesh", trimesh.__version__)
print("skimage", skimage.__version__)
print("pcu", getattr(pcu, "__version__", "unknown"))
PY
```

Open3D 必须验证：

```bash
python - <<'PY'
import open3d as o3d
print("open3d", o3d.__version__)
PY
```

若 Open3D 报 `libGL.so.1: cannot open shared object file`，先安装 4.3.1 中的 Debian 系统库。
如果不允许改容器系统层，可临时用 `LD_LIBRARY_PATH=$CONDA_PREFIX/lib` 诊断，但不要把它作为最终方案。

### 4.6 GPU smoke test

仅 import 成功不够，必须跑 CUDA kernel：

```bash
CUDA_VISIBLE_DEVICES=0 python - <<'PY' 2>&1 | tee experiments/env_logs/20260607_pasdf_gpu_smoke.log
import torch

assert torch.cuda.is_available(), "CUDA is not available"
x = torch.randn(4096, 3, device="cuda")
y = torch.mm(x.T, x)
torch.cuda.synchronize()
print("matmul ok", y.shape, torch.cuda.get_device_name(0))
print("capability", torch.cuda.get_device_capability(0))
PY
```

如果这里出现架构错误、kernel image 错误、非法指令或 CUDA launch failure，进入路径 B。

### 4.7 PyTorch3D CUDA smoke test

```bash
CUDA_VISIBLE_DEVICES=0 python - <<'PY' 2>&1 | tee experiments/env_logs/20260607_pytorch3d_smoke.log
import torch
from pytorch3d.loss import chamfer_distance

x = torch.randn(1, 1024, 3, device="cuda")
y = torch.randn(1, 1024, 3, device="cuda")
loss, _ = chamfer_distance(x, y)
loss.backward()
torch.cuda.synchronize()
print("pytorch3d chamfer ok", float(loss.detach().cpu()))
PY
```

这个测试比普通 `import pytorch3d` 更关键，因为 PASDF 的 PAM/距离计算依赖 CUDA 扩展。

---

## 5. PASDF 环境路径 B：RTX 4090 兼容分支

只有路径 A 在 GPU/PyTorch3D CUDA smoke test 失败时才启用。

### 5.1 失败判据

进入路径 B 的典型报错：

- `no kernel image is available for execution on the device`
- `CUDA error: invalid device function`
- `CUDA error: unspecified launch failure`
- PyTorch3D `_C` 扩展 import 成功但 CUDA op 运行失败

### 5.2 优先尝试：仍保持 PyTorch3D 0.7.4，但升级到更接近 Ada 的 CUDA 构建

先查询 conda 可用构建：

```bash
conda search -c pytorch3d pytorch3d=0.7.4 --info | grep -E 'pytorch3d 0.7.4|py310_cu|dependencies'
```

已查到的候选包括：

- `py310_cu115_pyt1110`
- `py310_cu116_pyt1120`
- `py310_cu116_pyt1121`
- `py310_cu116_pyt1130`

风险：CUDA 11.5/11.6 仍早于 CUDA 11.8，未必完全支持 Ada。若 `cu115/pyt1110` 能运行，优先
保持 PyTorch 1.11，减少 PASDF 代码风险；否则考虑 PyTorch 1.13 + CUDA 11.6。

### 5.3 次级尝试：PyTorch 1.13 + CUDA 11.6 + PyTorch3D 0.7.4

```bash
conda create -n pasdf_compat python=3.10 -y
conda activate pasdf_compat
conda install pytorch==1.13.0 torchvision torchaudio cudatoolkit=11.6 -c pytorch -y
conda install pytorch3d==0.7.4 -c pytorch3d -y
python -m pip install point-cloud-utils==0.29.6 scikit-image==0.21.0 scipy==1.11.1 trimesh==3.22.4 pybullet==3.2.6
```

然后重复 4.5-4.7 的 import/GPU/PyTorch3D smoke tests。

### 5.4 最后尝试：源码构建 PyTorch3D

仅在 conda 构建不可用时考虑。原则：

- 不直接改 PASDF 源码。
- 构建日志必须保存。
- 构建前记录 `torch.__version__`、`torch.version.cuda`、`CUDA_HOME`、`nvcc --version`、
  `TORCH_CUDA_ARCH_LIST`。

建议环境变量：

```bash
export FORCE_CUDA=1
export TORCH_CUDA_ARCH_LIST="8.9"
```

如果系统没有匹配的 CUDA toolkit/nvcc，不要在容器里盲目 apt 安装 CUDA。先汇报，由团队决定是否换
NVIDIA CUDA devel 镜像。

---

## 6. PO3AD 环境：单独排期

PO3AD 环境不作为 P1 主线 DoD。建议在 PASDF 官方权重评估能跑后，再开半天处理。

### 6.1 创建环境

```bash
conda create -n po3ad python=3.8 -y
conda activate po3ad
conda install -c pytorch -c nvidia -c conda-forge pytorch=1.9.0 cudatoolkit=11.1 torchvision -y
```

### 6.2 安装 BLAS 和编译工具

```bash
conda install openblas-devel -c anaconda -y
conda install ninja -c conda-forge -y
```

如果 solver 出现 MKL/OpenBLAS 冲突，按以下顺序排查：

1. 新建干净环境，不在已有 PASDF/base 环境里装。
2. 先装 PyTorch，再装 `openblas-devel`。
3. 避免显式安装 `nomkl`。
4. 如果 libmamba solver 失败，尝试 classic solver：

```bash
conda config --set solver classic
```

### 6.3 安装 MinkowskiEngine

优先本地 clone 后 `setup.py install`，因为 PO3AD README 中 `pip --install-option` 在新 pip/setuptools
下更容易失效。

```bash
mkdir -p third_party/PO3AD_lib
cd third_party/PO3AD_lib
git clone https://github.com/NVIDIA/MinkowskiEngine.git
cd MinkowskiEngine
export CUDA_HOME=/usr/local/cuda-11.1
python setup.py install --blas_include_dirs=${CONDA_PREFIX}/include --blas=openblas --force_cuda \
  2>&1 | tee ../../../../experiments/env_logs/20260607_minkowski_install.log
```

如果容器没有 `/usr/local/cuda-11.1` 或 `nvcc`，不要继续硬装；记录为阻塞。MinkowskiEngine 官方要求编译
CUDA 与 PyTorch CUDA 匹配。

### 6.4 PO3AD import 验证

```bash
python - <<'PY'
import torch
import MinkowskiEngine as ME
print("torch", torch.__version__, torch.version.cuda)
print("cuda", torch.cuda.is_available())
print("ME", ME.__version__)
PY
```

若失败，PO3AD 先转为论文报告值对照，不阻塞 PASDF。

---

## 7. 下载工具环境

你在下载数据时建议并行准备这些工具：

```bash
conda activate pasdf
python -m pip install gdown huggingface_hub
```

Anomaly-ShapeNet：

- Hugging Face：`https://huggingface.co/datasets/Chopper233/Anomaly-ShapeNet`
- Baidu Disk：提取码 `case`

PASDF 权重和预处理 SDF：

- Google Drive folder：PASDF README 中的 `1-aeND5tZ_dFp-7BhZHPyZSofDgxRTYRQ`
- 内容应包含 `data/` 与 `results/`

下载完成后的关键检查：

```bash
find data -maxdepth 4 -type f | head
find data -maxdepth 4 -type f | wc -l
du -sh data/*
```

不要把下载数据、权重、SDF 样本提交进 git。

---

## 8. P1 验收清单

PASDF 官方环境最低 DoD：

- [x] `conda activate pasdf`
- [x] `python -c "import torch, torchvision, pytorch3d"` 无报错
- [x] `python -c "import point_cloud_utils, trimesh, skimage, open3d"` 无报错
- [x] `torch.cuda.is_available()` 为 `True`
- [x] 普通 CUDA matmul smoke test 通过
- [x] PyTorch3D `chamfer_distance` CUDA smoke test 通过
- [x] PASDF submodule 已加入 `third_party/PASDF` 并钉死 commit
- [x] `environment.yml` 导出
- [x] `requirements-lock.txt` 导出
- [x] 环境日志保存到 `experiments/env_logs/`

可选 DoD：

- [x] PASDF 模块级 import 成功
- [ ] `Test/AD_test.py --help` 或 config 解析能运行
- [ ] 官方权重和预处理 SDF 已下载并校验目录结构

PO3AD DoD：

- [ ] `po3ad` 独立环境创建成功
- [ ] PyTorch 1.9.0 + CUDA 11.1 import 成功
- [ ] MinkowskiEngine import 成功
- [ ] 若失败，有日志和失败原因；PASDF 主线继续

---

## 9. 常见失败与处理

| 现象 | 优先判断 | 处理 |
|---|---|---|
| `conda env update` solver 很慢 | 环境文件锁太细、channel 多 | 先用官方脚本；失败后手动安装核心包，不一次性解完整 notebook 依赖 |
| `pip install -e .` 在 PASDF 失败 | PASDF 可能无打包文件 | 不改第三方源码；用 `PYTHONPATH=$PWD/third_party/PASDF` |
| `import pytorch3d` 失败 | PyTorch/PyTorch3D/CUDA 构建不匹配 | 检查 `conda list torch pytorch3d cudatoolkit` |
| PyTorch3D CUDA op 失败 | RTX 4090/Ada 与 CUDA 11.3 运行时不兼容 | 进入路径 B |
| `import torch` 报 executable stack | conda PyTorch 1.11 的 `libtorch_cpu.so` 在当前内核/挂载策略下要求可执行栈 | 清除该 so 的 `PT_GNU_STACK` executable 标志，保留备份并记录日志 |
| `undefined symbol: iJIT_NotifyEvent` | PyTorch 1.11 与 MKL/intel-openmp 2025 不兼容 | 降到 `mkl=2021.4.0`、`intel-openmp=2021.4.0`、`numpy=1.23.5` |
| Open3D 报 `libGL.so.1` 缺失 | 基础 Docker 镜像缺系统 OpenGL/C++ runtime | Debian 容器安装 `libgl1 libgomp1 libc++1` |
| `libc10.so` 找不到 | PyTorch 动态库路径问题或混装 pip/conda torch | 同一环境只保留一种 torch 来源，优先 conda |
| MinkowskiEngine BLAS 冲突 | MKL/OpenBLAS solver 冲突 | 先装 PyTorch，再装 openblas；必要时 classic solver |
| `--install-option` 不识别 | 新 pip 移除/弱化旧参数路径 | 改用本地 clone + `python setup.py install` |
| `numpy.distutils` 报错 | 新 numpy/setuptools 与旧构建脚本冲突 | 降 numpy/setuptools 或按 issue 用 `setup.py install --blas=openblas --force_cuda` |
| Real3D-AD 推理极慢 | 点数高、PAM/配准耗时 | 先只跑 Anomaly-ShapeNet；Real3D-AD 用下采样和少数类别 |
| 显存不足 | SDF/PAM 或高点数输入 | 降 batch、按类别单卡跑、先复现 16384 点版本 |

---

## 10. 推荐执行顺序

1. 在容器中确认 `nvidia-smi` 和 conda 可用。
2. 添加 PASDF submodule 并记录 commit。
3. 创建 `pasdf` 环境，先装官方锁。
4. 跑 import、CUDA matmul、PyTorch3D Chamfer 三个 smoke tests。
5. 若通过，导出锁文件；若失败，按路径 B 建 `pasdf_compat`。
6. 你并行下载 Anomaly-ShapeNet 和 PASDF artifacts。
7. 下载完成后核对 PASDF README 要求的 `data/`、`results/` 目录结构。
8. 再进入 P2 数据统计和 P3 官方权重 1-2 类评估。
9. PO3AD/MinkowskiEngine 另开半天；失败不影响主线。

---

## 11. 参考来源

- PASDF GitHub README：`https://github.com/ZZZBBBZZZ/PASDF`
- PASDF `install.sh`：`https://raw.githubusercontent.com/ZZZBBBZZZ/PASDF/master/install.sh`
- PASDF `environment_linux.yaml`：`https://github.com/ZZZBBBZZZ/PASDF/blob/master/environment_linux.yaml`
- PASDF `config_files/test_ShapeNetAD.yaml`
- PASDF `config_files/voxel_sizes.yaml`
- PyTorch previous versions：`https://pytorch.org/get-started/previous-versions/`
- PyTorch3D INSTALL：`https://github.com/facebookresearch/pytorch3d/blob/main/INSTALL.md`
- NVIDIA CUDA GPUs：`https://developer.nvidia.com/cuda-gpus`
- NVIDIA CUDA 11.8 release notes：`https://docs.nvidia.com/cuda/archive/11.8.0/cuda-toolkit-release-notes/index.html`
- PO3AD GitHub README：`https://github.com/yjnanan/PO3AD`
- MinkowskiEngine README：`https://github.com/NVIDIA/MinkowskiEngine`
- MinkowskiEngine issues：#617, #619, #621, #629, #633
- PASDF issues：#8, #9, #10, #11
