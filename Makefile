.PHONY: setup lint format test data eval train

PYTHON ?= $(shell if command -v python3 >/dev/null 2>&1; then command -v python3; elif command -v python >/dev/null 2>&1; then command -v python; elif [ -x /opt/conda/bin/python ]; then echo /opt/conda/bin/python; else echo python; fi)
CFG ?= configs/experiment/E1_pasdf_baseline.yaml

setup:
	$(PYTHON) -m pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check .
	black --check .
	mypy src/pcdad

format:
	ruff check --fix .
	ruff format .
	black .

test:
	pytest

data:
	$(PYTHON) scripts/prepare_data.py --stat

eval:
	$(PYTHON) scripts/evaluate.py --config $(CFG)

train:
	$(PYTHON) scripts/train.py --config $(CFG)
