.PHONY: lint coverage test arch release-check

lint:
	ruff check .

test:
	PYTHONPATH=. pytest -q

coverage:
	PYTHONPATH=. pytest --cov=app --cov-report=term --cov-fail-under=80

arch:
	PYTHONPATH=. pytest -q tests/test_architecture_imports.py

release-check:
	python scripts/release/release.py
