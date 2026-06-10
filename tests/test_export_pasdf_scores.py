from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "export_pasdf_scores.py"
    spec = importlib.util.spec_from_file_location("export_pasdf_scores_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeTensor:
    def __init__(self, data):
        self._data = data

    def flatten(self):
        return self

    def numpy(self):
        return np.asarray(self._data)

    def item(self):
        return int(np.asarray(self._data).reshape(-1)[0])


def test_export_pasdf_scores_cli_writes_summary_with_fake_runtime(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    config_path = tmp_path / "pasdf.yaml"
    config_path.write_text(
        "\n".join(
            [
                "seed: 42",
                "dataset:",
                "  name: ShapeNetAD",
                "  cls_name: [tap1]",
                "infer:",
                "  top_k: 2",
                "",
            ]
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "scores"
    summary_md = tmp_path / "summary.md"
    summary_csv = tmp_path / "summary.csv"

    fake_batch = {
        "sample_path": "/data/tap1/test/broken/tap1_broken2.pcd",
        "points": np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float32),
        "mask": _FakeTensor([0, 1]),
        "label": _FakeTensor([1]),
        "template_points": np.array([[0.0, 0.0, 0.0]], dtype=np.float32),
    }

    class FakeTorch:
        @staticmethod
        def from_numpy(array):
            return np.asarray(array)

    class FakeRuntime:
        Dataset_ShapeNetAD_test = object
        SDFScorer = object
        torch = FakeTorch

        @staticmethod
        def register_point_clouds(points, template_points, *, voxel_size, cd_threshold):
            return points, None, None

    monkeypatch.setattr(module, "_load_pasdf_runtime", lambda pasdf_root: FakeRuntime)
    monkeypatch.setattr(module, "_iter_pasdf_batches", lambda runtime, cfg, cls_name: [fake_batch])
    monkeypatch.setattr(module, "_build_scorer", lambda runtime, cfg, cls_name: object())
    monkeypatch.setattr(
        module,
        "_score_registered_points",
        lambda runtime, scorer, points: ([0.2, 0.8], [0.5]),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "export_pasdf_scores.py",
            "--config",
            str(config_path),
            "--pasdf-root",
            str(tmp_path / "PASDF"),
            "--classes",
            "tap1",
            "--output-dir",
            str(output_dir),
            "--summary-md",
            str(summary_md),
            "--summary-csv",
            str(summary_csv),
            "--save-point-scores",
        ],
    )

    module.main()

    assert summary_md.read_text(encoding="utf-8").startswith("# P5 PASDF 样本级分数导出摘要")
    class_csv = output_dir / "tap1" / "sample_scores.csv"
    assert class_csv.exists()
    assert "tap1,tap1_broken2,/data/tap1/test/broken/tap1_broken2.pcd,1,2,0.5" in (
        class_csv.read_text(encoding="utf-8")
    )
    csv_text = summary_csv.read_text(encoding="utf-8")
    assert "tap1,tap1_broken2,/data/tap1/test/broken/tap1_broken2.pcd,1,2,0.5" in csv_text
    point_npz = output_dir / "tap1" / "points" / "tap1_broken2.npz"
    assert point_npz.exists()
    with np.load(point_npz) as payload:
        assert payload["points"].shape == (2, 3)
        assert payload["point_scores"].tolist() == [0.2, 0.8]
        assert payload["mask"].tolist() == [0, 1]
    stdout = capsys.readouterr().out
    assert f"Wrote PASDF score markdown to {summary_md}" in stdout
    assert f"Wrote PASDF score CSV to {summary_csv}" in stdout


def test_build_scorer_temporarily_runs_from_pasdf_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_script_module()
    start_cwd = Path.cwd()
    observed_cwd: list[Path] = []

    class FakeScorer:
        def __init__(self, cfg, cls_name, device):
            observed_cwd.append(Path.cwd())

    class FakeRuntime:
        SDFScorer = FakeScorer
        pasdf_root = tmp_path

    scorer = module._build_scorer(FakeRuntime, {"device": "cpu"}, "cap3")

    assert isinstance(scorer, FakeScorer)
    assert observed_cwd == [tmp_path]
    assert Path.cwd() == start_cwd
