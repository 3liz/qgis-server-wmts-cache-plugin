import sys
import os
import logging
import lxml.etree

from qgis.core import Qgis, QgsProject
from qgis.server import (QgsBufferServerRequest,
                         QgsBufferServerResponse)

LOGGER = logging.getLogger('server')


def test_wmts_document_cache(client):
    """  Test getcapabilites response
    """
    plugin = client.getplugin('wmtsCacheServer')
    assert plugin is not None

    # Create a filter
    cachefilter = plugin.create_filter()

    # Delete document
    project = QgsProject()
    project.setFileName(client.getprojectpath("project.qgs").strpath)
 
    # Get project document root path
    docroot = cachefilter._cache.get_documents_root(project.fileName())

    cachefilter.deleteCachedDocuments(project)

    assert not os.path.exists(docroot.as_posix())

    parameters = { 
            'MAP': project.fileName(),
            'REQUEST': 'GetCapabilities',
            'SERVICE': 'WMTS' }

    # Get the cached path from the request parameters
    docpath = cachefilter._cache.get_document_cache(project.fileName(), parameters,'.xml').as_posix()

    assert not os.path.exists(docpath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())
    assert rv.status_code == 200
   
    # Test that document cache has been created
    assert os.path.exists(docpath)


def test_wmts_document_tile(client):
    """  Test WMTS tile response
    """
    plugin = client.getplugin('wmtsCacheServer')
    assert plugin is not None

    # Create a filter
    cachefilter = plugin.create_filter()

    # Delete document
    project = QgsProject()
    project.setFileName(client.getprojectpath("project.qgs").strpath)
 
    # Get project document root path
    tileroot = cachefilter._cache.get_tiles_root(project.fileName())

    cachefilter.deleteCachedImages(project)

    assert not os.path.exists(tileroot.as_posix())

    parameters = {
            "MAP": project.fileName(),
            "SERVICE": "WMTS",
            "VERSION": "1.0.0",
            "REQUEST": "GetTile",
            "LAYER": "Country",
            "STYLE": "",
            "TILEMATRIXSET": "EPSG:3857",
            "TILEMATRIX": "0",
            "TILEROW": "0",
            "TILECOL": "0",
            "FORMAT": "image/png" }

    # Get the cached path from the request parameters
    tilepath = cachefilter._cache.get_tile_cache(project.fileName(),parameters).as_posix()

    assert not os.path.exists(tilepath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())

    if rv.status_code != 200:
        LOGGER.error(lxml.etree.tostring(rv.xml, pretty_print=True))

    assert rv.status_code == 200
   
    # Test that document cache has been created
    assert os.path.exists(tilepath)


