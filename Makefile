.DEFAULT_GOAL := all
isort = isort -rc pydantic-odm tests
black = black -S -l 120 --target-version py37 pydantic-odm tests

.PHONY: install
install:
	pip install -U pipenv
	pipenv install --dev

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
	flake8 pydantic/ tests/
	$(isort) --check-only
	$(black) --check

.PHONY: check-dist
check-dist:
	python setup.py check -ms
	python setup.py sdist
	twine check dist/*

.PHONY: mypy
mypy:
	mypy pydantic

.PHONY: test
test:
	pytest --cov=pydantic
	@python tests/try_assert.py

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
