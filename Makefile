venv:
	python -m venv ./venv
	bash -c 'source ./venv/bin/activate && pip install -e .'

build-dist:
	rm -rf ./dist && python setup.py sdist

upload-test: build-dist
	twine upload -r pypitest dist/*

upload-live: build-dist
	twine upload -r pypi dist/*

test:
	pytest
