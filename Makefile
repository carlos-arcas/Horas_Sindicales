.PHONY: lint coverage test

lint:
	ruff check .

test:
	PYTHONPATH=. pytest -q

coverage:
	PYTHONPATH=. pytest --cov=app --cov-report=term --cov-fail-under=80
