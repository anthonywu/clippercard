sync:
	uv sync --group dev

test-cli:
	uv run python -m clippercard.test_cli $(ARGS)

test:
	uv run nox -s test

test-all:
	uv run nox -s test_all

lint:
	uv run nox -s lint

format:
	uv run nox -s format

build-dist:
	uv run nox -s build

upload-test: build-dist
	uv run twine upload -r pypitest dist/*

upload-live: build-dist
	uv run twine upload -r pypi dist/

publish: build-dist
	uv publish dist/*
