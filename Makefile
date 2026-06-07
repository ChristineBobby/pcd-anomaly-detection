.PHONY: setup lint format test data eval train

PYTHON ?= $(shell if command -v python3 >/dev/null 2>&1; then command -v python3; elif command -v python >/dev/null 2>&1; then command -v python; elif [ -x /opt/conda/bin/python ]; then echo /opt/conda/bin/python; else echo python; fi)
PROJECT_PYTHONPATH ?= src
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
	PYTHONPATH=$(PROJECT_PYTHONPATH) pytest

data:
	PYTHONPATH=$(PROJECT_PYTHONPATH) $(PYTHON) scripts/prepare_data.py --stat

eval:
	PYTHONPATH=$(PROJECT_PYTHONPATH) $(PYTHON) scripts/evaluate.py --config $(CFG)

train:
	PYTHONPATH=$(PROJECT_PYTHONPATH) $(PYTHON) scripts/train.py --config $(CFG)
