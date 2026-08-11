.PHONY: test build docs docker-build docker-build-rl docker-test lint clean reproduce

test:
	python -m pytest tests/ -v --tb=short --cov=src.nomos --cov-report=term-missing

build:
	pip install -e .

docs:
	mkdocs build --strict

NOMOS_IMAGE ?= ghcr.io/nomos-n4s/nomos

docker-build:
	docker build -t $(NOMOS_IMAGE):dev --target base .

docker-build-rl:
	docker build -t $(NOMOS_IMAGE):dev-rl --target with-rl .

docker-test:
	docker run --rm $(NOMOS_IMAGE):dev python -m pytest tests/ -x -q

lint:
	ruff check src/
	ruff format --check src/

reproduce: docker-build
	mkdir -p results
	docker run --rm -v "$(CURDIR)/results:/app/results" $(NOMOS_IMAGE):dev all --baselines --steps 1000 --seeds 20
	@echo "=== Reproducibility check complete ==="

clean:
	rm -rf site/ build/ dist/ .coverage* .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
