SHELL = bash
.ONESHELL:
.PHONY: env

#
# wmts plugin makefile
#

COMMITID=$(shell git rev-parse --short HEAD)

REGISTRY_URL ?= 3liz
REGISTRY_PREFIX=$(REGISTRY_URL)/

# Qgis version flavor
FLAVOR:=release

BECOME_USER:=$(shell id -u)
BECOME_GROUP:=$(shell id -g)

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

BECOME_USER:=$(shell id -u)
BECOME_GROUP:=$(shell id -g)
CACHEDIR:=.wmts_cache

run: env
	cd tests && docker-compose up -V --force-recreate

stop:
	cd tests && docker-compose down -v --remove-orphans

env:
	@echo "Creating environment file for docker-compose"
	@mkdir tests/$(CACHEDIR)
	@cat <<-EOF > tests/.env
		WORKDIR=$(shell pwd)
		CACHEDIR=$(CACHEDIR)
		QGIS_VERSION=$(FLAVOR)
		QGIS_USER_ID=$(BECOME_USER)
		QGIS_USER_GID=$(BECOME_GROUP)
		SERVER_HTTP_PORT=127.0.0.1:8888
		SERVER_MANAGEMENT_PORT=127.0.0.1:19876
		EOF

