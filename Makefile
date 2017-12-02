# -*- coding: utf-8; mode: makefile-gmake -*-

.DEFAULT = help
DEBUG ?= --pdb
TEST ?= .

# python version to use
PY       ?=3
# list of python packages (folders) or modules (files) of this build
PYOBJECTS = konfig
# folder where the python distribution takes place
PYDIST   ?= dist
# folder where the python intermediate build files take place
PYBUILD  ?= build

SYSTEMPYTHON = `which python$(PY) python | head -n 1`
VIRTUALENV   = virtualenv --python=$(SYSTEMPYTHON)
VENV_OPTS   = "--no-site-packages"
TEST_FOLDER  = ./konfig/tests

ENV     = ./local/py$(PY)
ENV_BIN = $(ENV)/bin


PHONY += help
help::
	@echo  'usage:'
	@echo
	@echo  '  build     - build virtualenv ($(ENV)) and install *developer mode*'
	@echo  '  lint      - run pylint within "build" (developer mode)'
	@echo  '  test      - run tests for all supported environments (tox)'
	@echo  '  debug     - run tests within a PDB debug session'
	@echo  '  dist      - build packages in "$(PYDIST)/"'
	@echo  '  publish   - upload "$(PYDIST)/*" files to PyPi'
	@echo  '  clean	    - remove most generated files'
	@echo
	@echo  'options:'
	@echo
	@echo  '  PY=3      - python version to use (default 3)'
	@echo  '  TEST=.    - choose test from $(TEST_FOLDER) (default "." runs all)'
	@echo  '  DEBUG=    - target "debug": do not invoke PDB on errors'
	@echo
	@echo  'When using target "debug", set breakpoints within py-source by adding::'
	@echo  '    ...'
	@echo  '    DEBUG()'
	@echo  '    ...'
	@echo
	@echo  'Example; a clean and fresh build (in local/py3), run all tests (py27, py35, lint)::'
	@echo
	@echo  '  make clean build test'
	@echo
	@echo  'Example; debug "test_<name>.py" within a python2 session (in local/py2)::'
	@echo
	@echo  '  make PY=2 TEST=test_<name>.py debug'
	@echo


PHONY += build
build: $(ENV)
	$(ENV_BIN)/pip -v install -e .


PHONY += lint
lint: $(ENV)
	$(ENV_BIN)/pylint $(PYOBJECTS) --rcfile pylintrc

PHONY += test
test:  $(ENV)
	$(ENV_BIN)/tox -vv

# set breakpoint with:
#    DEBUG()
# e.g. to run tests in debug mode in emacs use:
#   'M-x pdb' ... 'make debug'

PHONY += debug
debug: build
	DEBUG=$(DEBUG) $(ENV_BIN)/pytest $(DEBUG) -v $(TEST_FOLDER)/$(TEST)

$(ENV):
	$(VIRTUALENV) $(VENV_OPTS) $(ENV)
	$(ENV_BIN)/pip install -r requirements.txt

# for distribution, use python from virtualenv
PHONY += dist
dist:  clean-dist $(ENV)
	$(ENV_BIN)/python setup.py \
		sdist -d $(PYDIST)  \
		bdist_wheel --bdist-dir $(PYBUILD) -d $(PYDIST)

PHONY += publish
publish: dist
	$(ENV_BIN)/twine upload $(PYDIST)/*

PHONY += clean-dist
clean-dist:
	rm -rf ./$(PYBUILD) ./$(PYDIST)


PHONY += clean
clean: clean-dist
	rm -rf ./local ./.cache
	rm -rf *.egg-info .coverage
	rm -rf .eggs .tox html
	find . -name '*~' -exec echo rm -f {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name __pycache__ -exec rm -rf {} +

# END of Makefile
.PHONY: $(PHONY)
