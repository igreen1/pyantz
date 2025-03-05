test:
	uv run pytest -n 16 --cov=src

build:
	uv build