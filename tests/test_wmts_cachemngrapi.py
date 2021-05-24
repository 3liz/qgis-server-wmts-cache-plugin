import sys
import os
import logging
import json
import lxml.etree

from shutil import rmtree

from qgis.core import Qgis, QgsProject
from qgis.server import (QgsBufferServerRequest,
                         QgsBufferServerResponse)

LOGGER = logging.getLogger('server')


def test_wmts_cachemngrapi_empty_cache(client):
    """ Test the API with empty cache
        /cachemngr.json
        /cachemngr/collections.json
    """
    # Get plugin
    plugin = client.getplugin('wmtsCacheServer')
    assert plugin is not None

    # Clear cache
    for c in plugin.rootpath.glob('*.inf'):
        rmtree(c.with_suffix(''))
        c.unlink()

    # Make a request
    qs = "/cachemngr.json"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'links' in json_content
    assert len(json_content['links']) == 1
    assert json_content['links'][0]['title'] == 'Cache collections'

    qs = "/cachemngr/collections.json"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'cache_layout' in json_content
    assert json_content['cache_layout'] == 'tc'
    assert 'collections' in json_content
    assert len(json_content['collections']) == 0
    assert 'links' in json_content


def test_wmts_cachemngrapi_cache_info(client):
    """ Test the API with cache
        /cachemngr.json
        /cachemngr/collections.json
        /cachemngr/collection/(?<collectionId>[^/]+?).json
        /cachemngr/collection/(?<collectionId>[^/]+?)/docs.json
        /cachemngr/collection/(?<collectionId>[^/]+?)/layers.json
        /cachemngr/collection/(?<collectionId>[^/]+?)/layers/(?<layerId>[^/]+?).json
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
    docpath = cachefilter._cache.get_document_cache(project.fileName(), parameters,'.xml').as_posix()

    assert not os.path.exists(docpath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())
    assert rv.status_code == 200

    # Test that document cache has been created
    assert os.path.exists(docpath)

    # Get project tiles root path
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
            "FORMAT": "image/png" }

    # Get the cached path from the request parameters
    tilepath = cachefilter._cache.get_tile_cache(project.fileName(),parameters).as_posix()

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

    # Cache manager API requests
    qs = "/cachemngr/collections.json"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'cache_layout' in json_content
    assert json_content['cache_layout'] == 'tc'

    assert 'collections' in json_content
    assert len(json_content['collections']) == 1

    assert 'links' in json_content
    assert len(json_content['links']) == 0

    collection = json_content['collections'][0]
    assert 'id' in collection
    assert 'links' in collection
    assert 'project' in collection
    assert collection['project'] == client.getprojectpath("france_parts.qgs").strpath

    qs = "/cachemngr/collections/{}.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'project' in json_content
    assert json_content['project'] == client.getprojectpath("france_parts.qgs").strpath

    assert 'links' in json_content
    assert len(json_content['links']) == 2

    qs = "/cachemngr/collections/{}/docs.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'project' in json_content
    assert json_content['project'] == client.getprojectpath("france_parts.qgs").strpath

    assert 'documents' in json_content
    assert json_content['documents'] == 1

    assert 'links' in json_content
    assert len(json_content['links']) == 0

    qs = "/cachemngr/collections/{}/layers.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'project' in json_content
    assert json_content['project'] == client.getprojectpath("france_parts.qgs").strpath

    assert 'layers' in json_content
    assert len(json_content['layers']) == 1

    assert 'links' in json_content
    assert len(json_content['links']) == 0

    layer = json_content['layers'][0]
    assert 'id' in layer
    assert 'links' in layer

    qs = "/cachemngr/collections/{}/layers/{}.json".format(collection['id'], layer['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == layer['id']

    assert 'links' in json_content
    assert len(json_content['links']) == 0


def test_wmts_cachemngrapi_delete_docs(client):
    """ Test the API with to remove docs cache
        /cachemngr/collections.json
        /cachemngr/collection/(?<collectionId>[^/]+?)/docs.json
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
    docpath = cachefilter._cache.get_document_cache(project.fileName(), parameters,'.xml').as_posix()

    assert not os.path.exists(docpath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())
    assert rv.status_code == 200

    # Test that document cache has been created
    assert os.path.exists(docpath)

    # Cache manager API requests
    qs = "/cachemngr/collections.json"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'collections' in json_content
    assert len(json_content['collections']) == 1

    collection = json_content['collections'][0]
    assert 'id' in collection
    assert 'links' in collection
    assert 'project' in collection
    assert collection['project'] == client.getprojectpath("france_parts.qgs").strpath

    # Get docs info
    qs = "/cachemngr/collections/{}/docs.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'project' in json_content
    assert json_content['project'] == client.getprojectpath("france_parts.qgs").strpath

    assert 'documents' in json_content
    assert json_content['documents'] == 1

    # Delete docs
    qs = "/cachemngr/collections/{}/docs.json".format(collection['id'])
    rv = client.delete(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    # Get docs info
    qs = "/cachemngr/collections/{}/docs.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'project' in json_content
    assert json_content['project'] == client.getprojectpath("france_parts.qgs").strpath

    assert 'documents' in json_content
    assert json_content['documents'] == 0

    # Test that document cache has been deleted
    assert not os.path.exists(docpath)


def test_wmts_cachemngrapi_delete_layer(client):
    """ Test the API with to remove docs cache
        /cachemngr/collections.json
        /cachemngr/collection/(?<collectionId>[^/]+?)/layers.json
        /cachemngr/collection/(?<collectionId>[^/]+?)/layers/(?<layerId>[^/]+?).json
    """
    plugin = client.getplugin('wmtsCacheServer')
    assert plugin is not None

    # Create a filter
    cachefilter = plugin.create_filter()

    # Delete document
    project = QgsProject()
    project.setFileName(client.getprojectpath("france_parts.qgs").strpath)

    # Get project tiles root path
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
            "FORMAT": "image/png" }

    # Get the cached path from the request parameters
    tilepath = cachefilter._cache.get_tile_cache(project.fileName(),parameters).as_posix()

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

    # Cache manager API requests
    qs = "/cachemngr/collections.json"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'collections' in json_content
    assert len(json_content['collections']) == 1

    collection = json_content['collections'][0]
    assert 'id' in collection
    assert 'links' in collection
    assert 'project' in collection
    assert collection['project'] == client.getprojectpath("france_parts.qgs").strpath

    qs = "/cachemngr/collections/{}/layers.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'layers' in json_content
    assert len(json_content['layers']) == 1

    layer = json_content['layers'][0]
    assert 'id' in layer

    qs = "/cachemngr/collections/{}/layers/{}.json".format(collection['id'], layer['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == layer['id']

    # Delete layer tiles
    qs = "/cachemngr/collections/{}/layers/{}.json".format(collection['id'], layer['id'])
    rv = client.delete(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    # Get layer tiles info
    qs = "/cachemngr/collections/{}/layers/{}.json".format(collection['id'], layer['id'])
    rv = client.get(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type') == 'application/json'

    # Get layers info
    qs = "/cachemngr/collections/{}/layers.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'layers' in json_content
    assert len(json_content['layers']) == 0

    # Test that tiles cache has been deleted
    assert not os.path.exists(tilepath)

def test_wmts_cachemngrapi_delete_layers(client):
    """ Test the API with to remove docs cache
        /cachemngr/collections.json
        /cachemngr/collection/(?<collectionId>[^/]+?)/layers.json
    """
    plugin = client.getplugin('wmtsCacheServer')
    assert plugin is not None

    # Create a filter
    cachefilter = plugin.create_filter()

    # Delete tiles
    project = QgsProject()
    project.setFileName(client.getprojectpath("france_parts.qgs").strpath)

    # Get project tiles root path
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
            "FORMAT": "image/png" }

    # Get the cached path from the request parameters
    tilepath = cachefilter._cache.get_tile_cache(project.fileName(),parameters).as_posix()

    assert not os.path.exists(tilepath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())

    original_content = rv.content

    if rv.status_code != 200:
        LOGGER.error(lxml.etree.tostring(rv.xml, pretty_print=True))

    assert rv.status_code == 200

    # Test that tile cache has been created
    assert os.path.exists(tilepath)

    # Cache manager API requests
    qs = "/cachemngr/collections.json"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'collections' in json_content
    assert len(json_content['collections']) == 1

    collection = json_content['collections'][0]
    assert 'id' in collection
    assert 'links' in collection
    assert 'project' in collection
    assert collection['project'] == client.getprojectpath("france_parts.qgs").strpath

    # Get layers info
    qs = "/cachemngr/collections/{}/layers.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'layers' in json_content
    assert len(json_content['layers']) == 1

    # Delete layers tiles
    qs = "/cachemngr/collections/{}/layers.json".format(collection['id'])
    rv = client.delete(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    # Get layers info
    qs = "/cachemngr/collections/{}/layers.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'layers' in json_content
    assert len(json_content['layers']) == 0

    # Test that tiles cache has been deleted
    assert not os.path.exists(tilepath)


def test_wmts_cachemngrapi_delete_collection(client):
    """ Test the API with to remove docs cache
        /cachemngr/collections.json
        /cachemngr/collection/(?<collectionId>[^/]+?).json
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
    docpath = cachefilter._cache.get_document_cache(project.fileName(), parameters,'.xml').as_posix()

    assert not os.path.exists(docpath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())
    assert rv.status_code == 200

    # Test that document cache has been created
    assert os.path.exists(docpath)

    # Get project tiles root path
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
            "FORMAT": "image/png" }

    # Get the cached path from the request parameters
    tilepath = cachefilter._cache.get_tile_cache(project.fileName(),parameters).as_posix()

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

    # Cache manager API requests
    qs = "/cachemngr/collections.json"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'collections' in json_content
    assert len(json_content['collections']) == 1

    collection = json_content['collections'][0]
    assert 'id' in collection
    assert 'links' in collection
    assert 'project' in collection
    assert collection['project'] == client.getprojectpath("france_parts.qgs").strpath

    # Get docs info
    qs = "/cachemngr/collections/{}/docs.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'project' in json_content
    assert json_content['project'] == client.getprojectpath("france_parts.qgs").strpath

    assert 'documents' in json_content
    assert json_content['documents'] == 1

    # Get layers info
    qs = "/cachemngr/collections/{}/layers.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'layers' in json_content
    assert len(json_content['layers']) == 1

    # Delete collection documents and layers tiles
    qs = "/cachemngr/collections/{}.json".format(collection['id'])
    rv = client.delete(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    # Get docs info
    qs = "/cachemngr/collections/{}/docs.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type') == 'application/json'

    # Test that document cache has been deleted
    assert not os.path.exists(docpath)

    # Get layers info
    qs = "/cachemngr/collections/{}/layers.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type') == 'application/json'

    # Test that tiles cache has been deleted
    assert not os.path.exists(tilepath)

    # Get collections info
    qs = "/cachemngr/collections.json"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'collections' in json_content
    assert len(json_content['collections']) == 0


def test_wmts_cachemngrapi_layerid_error(client):
    """ Test the API with empty cache
        /cachemngr/collection/(?<collectionId>[^/]+?).json
        /cachemngr/collection/(?<collectionId>[^/]+?)/layers.json
        /cachemngr/collection/(?<collectionId>[^/]+?)/layers/(?<layerId>[^/]+?).json
    """

    plugin = client.getplugin('wmtsCacheServer')
    assert plugin is not None

    # Create a filter
    cachefilter = plugin.create_filter()

    # Delete tiles
    project = QgsProject()
    project.setFileName(client.getprojectpath("france_parts.qgs").strpath)

    # Get project tiles root path
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
            "FORMAT": "image/png" }

    # Get the cached path from the request parameters
    tilepath = cachefilter._cache.get_tile_cache(project.fileName(),parameters).as_posix()

    assert not os.path.exists(tilepath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())

    original_content = rv.content

    if rv.status_code != 200:
        LOGGER.error(lxml.etree.tostring(rv.xml, pretty_print=True))

    assert rv.status_code == 200

    # Test that tile cache has been created
    assert os.path.exists(tilepath)

    # Cache manager API requests
    qs = "/cachemngr/collections.json"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'collections' in json_content
    assert len(json_content['collections']) == 1

    collection = json_content['collections'][0]
    assert 'id' in collection
    assert 'links' in collection
    assert 'project' in collection
    assert collection['project'] == client.getprojectpath("france_parts.qgs").strpath

    # Get layers info
    qs = "/cachemngr/collections/{}/layers.json".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'layers' in json_content
    assert len(json_content['layers']) == 1

    qs = "/cachemngr/collections/{}/layers/{}.json".format(collection['id'], 'foobar')
    rv = client.delete(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'code' in json_content
    assert json_content['code'] == 'API not found error'


def test_wmts_cachemngrapi_collectionid_error(client):
    """ Test the API with empty cache
        /cachemngr/collection/(?<collectionId>[^/]+?).json
        /cachemngr/collection/(?<collectionId>[^/]+?)/docs.json
        /cachemngr/collection/(?<collectionId>[^/]+?)/layers.json
        /cachemngr/collection/(?<collectionId>[^/]+?)/layers/(?<layerId>[^/]+?).json
    """

    qs = "/cachemngr/collections/{}.json".format('foobar')
    rv = client.delete(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'code' in json_content
    assert json_content['code'] == 'API not found error'

    qs = "/cachemngr/collections/{}/docs.json".format('foobar')
    rv = client.delete(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'code' in json_content
    assert json_content['code'] == 'API not found error'

    qs = "/cachemngr/collections/{}/layers.json".format('foobar')
    rv = client.delete(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'code' in json_content
    assert json_content['code'] == 'API not found error'

    qs = "/cachemngr/collections/{0}/layers/{0}.json".format('foobar')
    rv = client.delete(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type') == 'application/json'

    json_content = json.loads(rv.content)
    assert 'code' in json_content
    assert json_content['code'] == 'API not found error'