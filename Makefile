.DEFAULT_GOAL := all
isort = isort pydantic_odm tests
black = black -S -l 88 --target-version py37 pydantic_odm tests

# Makefile target args
args = $(filter-out $@,$(MAKECMDGOALS))

.PHONY: install
install:
	pip install -U poetry
	POETRY_VIRTUALENVS_IN_PROJECT=true poetry env use python3.8
	poetry install
	poetry run pip install -e .

.PHONY: build-cython-trace
build-cython-trace:
	python setup.py build_ext --force --inplace --define CYTHON_TRACE

.PHONY: build-cython
build-cython:
	python setup.py build_ext --inplace

.PHONY: format
format:
	$(isort)
	$(black)

.PHONY: lint
lint:
	flake8 pydantic_odm/ tests/
	$(isort) --check-only
	$(black) --check

.PHONY: check-dist
check-dist:
	python setup.py check -ms
	python setup.py sdist
	twine check dist/*

.PHONY: mypy
mypy:
	mypy pydantic_odm

.PHONY: test
test:
	pytest --cov=pydantic_odm

.PHONY: testwatch
testwatch: testwatch
	pytest --cov=pydantic_odm -fsvvl --ff --color=yes ${args}

.PHONY: testcov
testcov: test
	@echo "building coverage html"
	@coverage html

.PHONY: testcov-compile
testcov-compile: build-cython-trace test
	@echo "building coverage html"
	@coverage html

.PHONY: all
all: testcov lint mypy

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	rm -rf dist
	python setup.py clean
	rm -rf site
