SHELL:=bash
#
# wmts plugin makefile
#

COMMITID=$(shell git rev-parse --short HEAD)

REGISTRY_URL ?= 3liz
REGISTRY_PREFIX=$(REGISTRY_URL)/

# Qgis version flavor
FLAVOR:=release

BECOME_USER:=$(shell id -u)

QGIS_IMAGE=$(REGISTRY_PREFIX)qgis-platform:$(FLAVOR)

LOCAL_HOME ?= $(shell pwd)

PYTHON:=python3

BUILDDIR:=build
DIST:=${BUILDDIR}/dist

manifest:

dirs:
	mkdir -p $(DIST)

# Build dependencies
wheel-deps: dirs
	pip wheel -w $(DIST) -r requirements.txt

wheel:
	mkdir -p $(DIST)
	$(PYTHON) setup.py bdist_wheel --dist-dir=$(DIST)

deliver:
	twine upload -r storage $(DIST)/*

dist: dirs
	rm -rf *.egg-info
	$(PYTHON) setup.py sdist --dist-dir=$(DIST)

clean:
	rm -rf *.egg-info
	rm -rf $(BUILDDIR)

# Checke setup.cfg for flake8 configuration
lint:
	@flake8

test: lint
	mkdir -p $$(pwd)/.local $(LOCAL_HOME)/.cache
	docker run --rm --name wmts-cache-test-$(COMMITID) -w /src \
		-u $(BECOME_USER) \
		-v $$(pwd):/src \
		-v $$(pwd)/.local:/.local \
		-v $(LOCAL_HOME)/.cache:/.cache \
		-e PIP_CACHE_DIR=/.cache \
		-e PYTEST_ADDOPTS="$(TEST_OPTS)" \
		$(QGIS_IMAGE) ./tests/run-tests.sh

