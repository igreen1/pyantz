

test:
	cd docs && uv run make doctest && echo "**** Document Tests Successful! ****"
	uv run pytest

doc:
	cd docs && uv run make html

build:
	rm -rf dist
	uvx bumpver update --patch
	uv build

publish:
	uvx twine upload dist/*