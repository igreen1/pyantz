

test:
	cd docs && uv run make doctest && echo "**** Document Tests Successful! ****"
	uv run pytest

doc:
	cd docs && uv run make html

build:
	rm -rf dist
	uvx bumpver update --patch
	uv build --all-packages

publish:
	uvx twine upload dist/*

format-check:
	uv run ruff format --check

frontend-check:
	cd frontend/pyantz && npm ci && npm run check

# needs `npx playwright install --with-deps chromium` once
e2e:
	cd frontend/pyantz && npm run e2e

# put the built web ui in packages/pyantz-frontend, so that `uv run pyantz-frontend`
# works in a checkout (after `uv sync --extra frontend`)
frontend-bundle:
	cd frontend/pyantz && npm ci && npm run build
	rm -rf packages/pyantz-frontend/src/pyantz_frontend/static
	cp -r frontend/pyantz/dist packages/pyantz-frontend/src/pyantz_frontend/static
