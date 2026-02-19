.PHONY: lint coverage test arch gate release-check

lint:
	ruff check .

test:
	PYTHONPATH=. pytest -q

coverage:
	python scripts/quality_gate.py

arch:
	PYTHONPATH=. pytest -q tests/test_architecture_imports.py

gate:
	python scripts/quality_gate.py

release-check: gate
	python scripts/release/release.py
