upload-test:
	python setup.py sdist upload -r pypitest

upload-live:
	python setup.py sdist upload -r pypi
