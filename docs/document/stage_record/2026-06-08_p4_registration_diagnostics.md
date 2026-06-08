# P4 PASDF Registration 诊断记录

## 记录范围

- 运行日志：`experiments/E1_pasdf_baseline/full_40cls/run.log`
- 官方 voxel size 配置：`third_party/PASDF/config_files/voxel_sizes.yaml`
- Open3D warning 事件数：53

## 优先类别

| 类别 | Pixel AUROC | Object AUROC | Warning 数 | Warning 样本数 | 官方 Voxel | Sweep Voxel |
|---|---:|---:|---:|---:|---:|---|
| cap3 | 0.846928 | 0.550877 | 8 | 1 | 0.030 | 0.020, 0.030, 0.040, 0.050 |
| cap4 | 0.863803 | 0.628070 | 6 | 1 | 0.020 | 0.020, 0.030, 0.040, 0.050 |
| tap1 | 0.903394 | 0.766667 | 0 | 0 | 0.040 | 0.020, 0.030, 0.040, 0.050 |
| helmet2 | 0.834360 | 0.776812 | 0 | 0 | 0.030 | 0.020, 0.030, 0.040, 0.050 |
| microphone0 | 0.907773 | 0.780952 | 0 | 0 | 0.015 | 0.020, 0.030, 0.040, 0.050 |
| shelf0 | 0.859357 | 0.791304 | 0 | 0 | 0.015 | 0.020, 0.030, 0.040, 0.050 |
| cap5 | 0.899016 | 0.796491 | 0 | 0 | 0.015 | 0.020, 0.030, 0.040, 0.050 |

## Warning 样本

| 类别 | 样本 | Warning 数 | Correspondence 范围 | 路径 |
|---|---|---:|---|---|
| bowl4 | bowl4_positive1.pcd | 12 | 51-90 | `/workspace/code_folder/area1/Anomaly/data/Anomaly-ShapeNet-v2/dataset/16384/bowl4/test/bowl4_positive1.pcd` |
| bag0 | bag0_positive6.pcd | 8 | 115-168 | `/workspace/code_folder/area1/Anomaly/data/Anomaly-ShapeNet-v2/dataset/16384/bag0/test/bag0_positive6.pcd` |
| bowl2 | bowl2_positive7.pcd | 8 | 74-99 | `/workspace/code_folder/area1/Anomaly/data/Anomaly-ShapeNet-v2/dataset/16384/bowl2/test/bowl2_positive7.pcd` |
| cap3 | cap3_positive9.pcd | 8 | 75-107 | `/workspace/code_folder/area1/Anomaly/data/Anomaly-ShapeNet-v2/dataset/16384/cap3/test/cap3_positive9.pcd` |
| cap4 | cap4_positive14.pcd | 6 | 92-117 | `/workspace/code_folder/area1/Anomaly/data/Anomaly-ShapeNet-v2/dataset/16384/cap4/test/cap4_positive14.pcd` |
| bottle3 | bottle3_positive7.pcd | 4 | 60-124 | `/workspace/code_folder/area1/Anomaly/data/Anomaly-ShapeNet-v2/dataset/16384/bottle3/test/bottle3_positive7.pcd` |
| bowl5 | bowl5_positive14.pcd | 3 | 93-143 | `/workspace/code_folder/area1/Anomaly/data/Anomaly-ShapeNet-v2/dataset/16384/bowl5/test/bowl5_positive14.pcd` |
| vase0 | vase0_bulge4.pcd | 2 | 133-138 | `/workspace/code_folder/area1/Anomaly/data/Anomaly-ShapeNet-v2/dataset/16384/vase0/test/vase0_bulge4.pcd` |
| bottle1 | bottle1_broken2.pcd | 1 | 154-154 | `/workspace/code_folder/area1/Anomaly/data/Anomaly-ShapeNet-v2/dataset/16384/bottle1/test/bottle1_broken2.pcd` |
| vase3 | vase3_concavity6.pcd | 1 | 70-70 | `/workspace/code_folder/area1/Anomaly/data/Anomaly-ShapeNet-v2/dataset/16384/vase3/test/vase3_concavity6.pcd` |

## Voxel Sweep 命令

```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes cap3 --voxel-size 0.02 --output-dir experiments/P4_registration_sweep/cap3/vs_0p020
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes cap3 --voxel-size 0.03 --output-dir experiments/P4_registration_sweep/cap3/vs_0p030
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes cap3 --voxel-size 0.04 --output-dir experiments/P4_registration_sweep/cap3/vs_0p040
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes cap3 --voxel-size 0.05 --output-dir experiments/P4_registration_sweep/cap3/vs_0p050
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes cap4 --voxel-size 0.02 --output-dir experiments/P4_registration_sweep/cap4/vs_0p020
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes cap4 --voxel-size 0.03 --output-dir experiments/P4_registration_sweep/cap4/vs_0p030
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes cap4 --voxel-size 0.04 --output-dir experiments/P4_registration_sweep/cap4/vs_0p040
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes cap4 --voxel-size 0.05 --output-dir experiments/P4_registration_sweep/cap4/vs_0p050
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes tap1 --voxel-size 0.02 --output-dir experiments/P4_registration_sweep/tap1/vs_0p020
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes tap1 --voxel-size 0.03 --output-dir experiments/P4_registration_sweep/tap1/vs_0p030
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes tap1 --voxel-size 0.04 --output-dir experiments/P4_registration_sweep/tap1/vs_0p040
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes tap1 --voxel-size 0.05 --output-dir experiments/P4_registration_sweep/tap1/vs_0p050
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes helmet2 --voxel-size 0.02 --output-dir experiments/P4_registration_sweep/helmet2/vs_0p020
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes helmet2 --voxel-size 0.03 --output-dir experiments/P4_registration_sweep/helmet2/vs_0p030
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes helmet2 --voxel-size 0.04 --output-dir experiments/P4_registration_sweep/helmet2/vs_0p040
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes helmet2 --voxel-size 0.05 --output-dir experiments/P4_registration_sweep/helmet2/vs_0p050
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes microphone0 --voxel-size 0.02 --output-dir experiments/P4_registration_sweep/microphone0/vs_0p020
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes microphone0 --voxel-size 0.03 --output-dir experiments/P4_registration_sweep/microphone0/vs_0p030
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes microphone0 --voxel-size 0.04 --output-dir experiments/P4_registration_sweep/microphone0/vs_0p040
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes microphone0 --voxel-size 0.05 --output-dir experiments/P4_registration_sweep/microphone0/vs_0p050
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes shelf0 --voxel-size 0.02 --output-dir experiments/P4_registration_sweep/shelf0/vs_0p020
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes shelf0 --voxel-size 0.03 --output-dir experiments/P4_registration_sweep/shelf0/vs_0p030
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes shelf0 --voxel-size 0.04 --output-dir experiments/P4_registration_sweep/shelf0/vs_0p040
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes shelf0 --voxel-size 0.05 --output-dir experiments/P4_registration_sweep/shelf0/vs_0p050
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes cap5 --voxel-size 0.02 --output-dir experiments/P4_registration_sweep/cap5/vs_0p020
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes cap5 --voxel-size 0.03 --output-dir experiments/P4_registration_sweep/cap5/vs_0p030
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes cap5 --voxel-size 0.04 --output-dir experiments/P4_registration_sweep/cap5/vs_0p040
```
```bash
PYTHONPATH=src python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --classes cap5 --voxel-size 0.05 --output-dir experiments/P4_registration_sweep/cap5/vs_0p050
```
