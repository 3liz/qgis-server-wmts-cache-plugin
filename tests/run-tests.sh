#!/bin/bash

set -e

# Add /.local to path
export PATH=$PATH:/.local/bin

echo "Installing required packages..."
pip3 install -q -U --prefer-binary --user -r tests/requirements.txt

# Disable qDebug stuff that bloats test outputs
export QT_LOGGING_RULES="*.debug=false;*.warning=false"

# Disable python hooks/overrides
export QGIS_DISABLE_MESSAGE_HOOKS=1
export QGIS_NO_OVERRIDE_IMPORT=1

cd tests

export QGIS_WMTS_CACHE_ROOTDIR=/src/tests/__wmts_cache__
mkdir -p $QGIS_WMTS_CACHE_ROOTDIR

py.test -v --qgis-plugins=/src  $@

