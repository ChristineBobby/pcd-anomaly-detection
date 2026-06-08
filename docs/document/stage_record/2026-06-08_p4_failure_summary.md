# P4 PASDF Failure Analysis Summary

## Scope

- Results CSV: `experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv`
- Run log: `experiments/E1_pasdf_baseline/full_40cls/run.log`
- Classes: 40

## Metric Summary

- mean_pixel_auc: `0.896009030694`
- mean_object_auc: `0.900214149779`
- min_pixel: `helmet1` = `0.622745369843`
- min_object: `cap3` = `0.550877192982`

## Threshold Failures

- pixel_auc < 0.85: `helmet1`, `bowl2`, `helmet0`, `vase1`, `helmet2`, `headset1`, `cap3`
- object_auc < 0.8: `cap3`, `cap4`, `tap1`, `helmet2`, `microphone0`, `shelf0`, `cap5`

## Open3D Warning Summary

- total_too_few_correspondences: 53
- unattributed_warnings: 0

## P4 Priority Classes

`cap3`, `cap4`, `tap1`, `helmet2`, `microphone0`, `shelf0`, `cap5`, `helmet1`, `bowl2`, `helmet0`, `vase1`, `headset1`

## Failure Table

| Class | Pixel AUROC | Object AUROC | Open3D Warnings |
|---|---:|---:|---:|
| cap3 | 0.846928 | 0.550877 | 8 |
| cap4 | 0.863803 | 0.628070 | 6 |
| tap1 | 0.903394 | 0.766667 | 0 |
| helmet2 | 0.834360 | 0.776812 | 0 |
| microphone0 | 0.907773 | 0.780952 | 0 |
| shelf0 | 0.859357 | 0.791304 | 0 |
| cap5 | 0.899016 | 0.796491 | 0 |
| helmet1 | 0.622745 | 0.957143 | 0 |
| bowl2 | 0.816268 | 1.000000 | 8 |
| helmet0 | 0.819070 | 0.855072 | 0 |
| vase1 | 0.829644 | 0.952381 | 0 |
| headset1 | 0.836092 | 0.861905 | 0 |
