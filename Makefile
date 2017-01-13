.PHONY: build test coverage clean

SYSTEMPYTHON = `which python3 python | head -n 1`
VIRTUALENV = virtualenv --python=$(SYSTEMPYTHON)
VTENV_OPTS = "--no-site-packages"
ENV = ./local
ENV_BIN = $(ENV)/bin

build: $(ENV_BIN)/python
	$(ENV_BIN)/python setup.py develop

test:	$(ENV_BIN)/tox
	$(ENV_BIN)/tox

coverage: $(ENV_BIN)/nosetests
	$(ENV_BIN)/nosetests --with-coverage --cover-html --cover-html-dir=html --cover-package=konfig

$(ENV_BIN)/python:
	$(VIRTUALENV) $(VTENV_OPTS) $(ENV)

$(ENV_BIN)/nosetests: $(ENV_BIN)/python
	$(ENV_BIN)/pip install nose

$(ENV_BIN)/coverage: $(ENV_BIN)/python
	$(ENV_BIN)/pip install coverage

$(ENV_BIN)/tox: $(ENV_BIN)/python
	$(ENV_BIN)/pip install tox

clean:
	rm -rf $(ENV)
	rm -rf konfig.egg-info
	rm -rf .tox
	rm -rf html
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name __pycache__ -exec rm -rf {} +
