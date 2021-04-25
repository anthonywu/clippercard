virtualenv:
	mkdir -p ~/.virtualenvs/clippercard
	virtualenv --no-site-packages ~/.virtualenvs/clippercard
	bash -c 'source ~/.virtualenvs/clippercard/bin/activate && pip install -r ./requirements.txt'

build-dist:
	rm -rf ./dist && python setup.py sdist

upload-test: build-dist
	twine upload -r pypitest dist/*

upload-live: build-dist
	twine upload -r pypi dist/*
