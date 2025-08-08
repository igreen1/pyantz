test:
	uv run pytest -n 16 --cov=src

format:
	uv run isort src
	uv run ruff check src --fix
	uv run ruff format src
	uv run isort tests
	uv run ruff format tests

lint:
	uv run ruff check src
	uv run pylint src

type:
	uv run mypy src

build:
	uv build

sync:
	uv sync --all-extras