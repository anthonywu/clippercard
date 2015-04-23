virtualenv:
	mkdir -p ~/.virtualenvs/clippercard
	virtualenv --no-site-packages ~/.virtualenvs/clippercard
	bash -c 'source ~/.virtualenvs/clippercard/bin/activate && pip install -r ./requirements.txt'

upload-test:
	python setup.py sdist upload -r pypitest

upload-live:
	python setup.py sdist upload -r pypi
