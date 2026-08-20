default:
    just --list

sync:
    uv sync --group dev

test-cli *args:
    uv run python -m clippercard.test_cli {{args}}

test:
    uv run nox -s test

test-all:
    uv run nox -s test_all

lint:
    uv run ruff check .

format:
    uv run ruff format .

build-dist:
    uv build

publish-test: build-dist
    uv publish --publish-url https://test.pypi.org/legacy/ dist/*

publish: build-dist
    uv publish dist/*
