import logging
import os
import shutil
from pathlib import Path

import lxml.etree

from qgis.core import QgsProject

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
    project.setFileName(client.getprojectpath("france_parts.qgs").strpath)

    # Get project document root path
    docroot = cachefilter._cache.get_documents_root(project.fileName())

    cachefilter.deleteCachedDocuments(project)

    assert not os.path.exists(docroot.as_posix())

    parameters = {
            'MAP': project.fileName(),
            'REQUEST': 'GetCapabilities',
            'SERVICE': 'WMTS'
    }

    # Get the cached path from the request parameters
    docpath = cachefilter._cache.get_document_cache(
        project.fileName(), parameters, '.xml'
    ).as_posix()

    assert not os.path.exists(docpath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())
    assert rv.status_code == 200

    # Test that document cache has been created
    assert os.path.exists(docpath)

    original_content = rv.content

    # Make a second request and check for header
    rv = client.get(qs, project.fileName())
    assert rv.status_code == 200
    assert rv.headers.get('X-Qgis-Debug-Cache-Plugin') == 'wmtsCacheServer'
    assert rv.headers.get('X-Qgis-Debug-Cache-Path') == docpath

    cached_content = rv.content

    assert original_content == cached_content


def test_wmts_document_cache_time(client):
    """  Test getcapabilites response time
    """
    plugin = client.getplugin('wmtsCacheServer')
    assert plugin is not None

    # Create a filter
    cachefilter = plugin.create_filter()

    # Copy project
    shutil.copy(
        client.getprojectpath("france_parts.qgs"),
        client.getprojectpath("france_parts_copy.qgs")
    )

    # Delete document
    project = QgsProject()
    project.setFileName(client.getprojectpath("france_parts_copy.qgs").strpath)

    # Get project document root path
    docroot = cachefilter._cache.get_documents_root(project.fileName())

    cachefilter.deleteCachedDocuments(project)

    assert not os.path.exists(docroot.as_posix())

    parameters = {
            'MAP': project.fileName(),
            'REQUEST': 'GetCapabilities',
            'SERVICE': 'WMTS'
    }

    # Get the cached path from the request parameters
    docpath = cachefilter._cache.get_document_cache(
        project.fileName(), parameters, '.xml'
    ).as_posix()

    assert not os.path.exists(docpath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())
    assert rv.status_code == 200

    # Test that document cache has been created
    assert os.path.exists(docpath)

    # Get time of document cache creation
    docmtime = os.stat(docpath).st_mtime
    projmtime = project.lastModified().toMSecsSinceEpoch() / 1000.0

    assert projmtime < docmtime

    project.write()
    projmtime = project.lastModified().toMSecsSinceEpoch() / 1000.0

    assert projmtime > docmtime

    # Make a second request
    rv = client.get(qs, project.fileName())
    assert rv.status_code == 200

    ndocmtime = os.stat(docpath).st_mtime
    projmtime = project.lastModified().toMSecsSinceEpoch() / 1000.0

    assert projmtime < ndocmtime
    assert docmtime < ndocmtime

    # Clean files after testing
    Path(client.getprojectpath("france_parts_copy.qgs")).unlink()


def test_wmts_document_tile(client):
    """  Test WMTS tile response
    """
    plugin = client.getplugin('wmtsCacheServer')
    assert plugin is not None

    # Create a filter
    cachefilter = plugin.create_filter()

    # Delete document
    project = QgsProject()
    project.setFileName(client.getprojectpath("france_parts.qgs").strpath)

    # Get project document root path
    tileroot = cachefilter._cache.get_tiles_root(project.fileName())

    cachefilter.deleteCachedImages(project)

    assert not os.path.exists(tileroot.as_posix())

    parameters = {
            "MAP": project.fileName(),
            "SERVICE": "WMTS",
            "VERSION": "1.0.0",
            "REQUEST": "GetTile",
            "LAYER": "france_parts",
            "STYLE": "",
            "TILEMATRIXSET": "EPSG:4326",
            "TILEMATRIX": "0",
            "TILEROW": "0",
            "TILECOL": "0",
            "FORMAT": "image/png"
    }

    # Get the cached path from the request parameters
    tilepath = cachefilter._cache.get_tile_cache(
        project.fileName(), parameters
    ).as_posix()

    assert not os.path.exists(tilepath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())

    original_content = rv.content

    if rv.status_code != 200:
        LOGGER.error(lxml.etree.tostring(rv.xml, pretty_print=True))

    assert rv.status_code == 200

    # Test that document cache has been created
    assert os.path.exists(tilepath)

    # Make a second request and check for header
    rv = client.get(qs, project.fileName())
    assert rv.status_code == 200
    assert rv.headers.get('X-Qgis-Debug-Cache-Plugin') == 'wmtsCacheServer'
    assert rv.headers.get('X-Qgis-Debug-Cache-Path') == tilepath

    cached_content = rv.content

    assert original_content == cached_content
