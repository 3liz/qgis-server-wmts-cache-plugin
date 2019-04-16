SHELL:=bash
#
# wmts plugin makefile
#

COMMITID=$(shell git rev-parse --short HEAD)

ifdef REGISTRY_URL
»   REGISTRY_PREFIX=$(REGISTRY_URL)/
endif

# Qgis version flavor
FLAVOR:=3.4

BECOME_USER:=$(shell id -u)

QGIS_IMAGE=$(REGISTRY_PREFIX)qgis-platform:$(FLAVOR)

LOCAL_HOME ?= $(shell pwd)

test:
	mkdir -p $(LOCAL_HOME)/.local $(LOCAL_HOME)/.cache/pip
	docker run --rm --name qgis-py-server-test-$(COMMITID) -w /src \
		-u $(BECOME_USER) \
		-v $(shell pwd):/src \
		-v $(LOCAL_HOME)/.local:/.local \
		-v $(LOCAL_HOME)/.cache/pip:/.pipcache \
		-e PIP_CACHE_DIR=/.pipcache \
		-e PYTEST_ADDOPTS="$(TEST_OPTS)" \
		$(QGIS_IMAGE) ./tests/run-tests.sh

