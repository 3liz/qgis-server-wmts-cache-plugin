import json
import logging
import os

from shutil import rmtree

import lxml.etree

from qgis.core import QgsProject

LOGGER = logging.getLogger('server')


def test_wmts_cachemngrapi_empty_cache(client):
    """ Test the API with empty cache
        /wmtscache
        /wmtscache/collections
    """
    # Get plugin
    plugin = client.getplugin('wmtsCacheServer')
    assert plugin is not None

    # Clear cache
    for c in plugin.rootpath.glob('*.inf'):
        rmtree(c.with_suffix(''))
        c.unlink()

    # Make a request
    qs = "/wmtscache"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'links' in json_content
    assert len(json_content['links']) == 2
    assert json_content['links'][0]['title'] == 'WMTS Cache manager LandingPage as JSON'
    assert json_content['links'][0]['rel'] == 'self'
    assert json_content['links'][1]['title'] == 'WMTS Cache manager Collections as JSON'
    assert json_content['links'][1]['rel'] == 'data'

    qs = "/wmtscache/collections"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'cache_layout' in json_content
    assert json_content['cache_layout'] == 'tc'
    assert 'collections' in json_content
    assert len(json_content['collections']) == 0
    assert 'links' in json_content
    assert len(json_content['links']) == 1
    assert json_content['links'][0]['title'] == 'WMTS Cache manager Collections as JSON'
    assert json_content['links'][0]['rel'] == 'self'


def test_wmts_cachemngrapi_cache_info(client):
    """ Test the API with cache
        /wmtscache
        /wmtscache/collections
        /wmtscache/collection/(?<collectionId>[^/]+?)
        /wmtscache/collection/(?<collectionId>[^/]+?)/docs
        /wmtscache/collection/(?<collectionId>[^/]+?)/layers
        /wmtscache/collection/(?<collectionId>[^/]+?)/layers/(?<layerId>[^/]+?)
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
        "FORMAT": "image/png"
    }

    # Get the cached path from the request parameters
    tilepath = cachefilter._cache.get_tile_cache(project.fileName(),parameters).as_posix()

    assert not os.path.exists(tilepath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())

    # original_content = rv.content

    if rv.status_code != 200:
        LOGGER.error(lxml.etree.tostring(rv.xml, pretty_print=True))

    assert rv.status_code == 200

    # Test that document cache has been created
    assert os.path.exists(tilepath)

    # Cache manager API requests
    qs = "/wmtscache/collections"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'cache_layout' in json_content
    assert json_content['cache_layout'] == 'tc'

    assert 'collections' in json_content
    assert len(json_content['collections']) == 1

    assert 'links' in json_content
    assert len(json_content['links']) == 1
    assert json_content['links'][0]['title'] == 'WMTS Cache manager Collections as JSON'
    assert json_content['links'][0]['rel'] == 'self'

    collection = json_content['collections'][0]
    assert 'id' in collection
    assert 'links' in collection
    assert 'project' in collection
    assert collection['project'] == client.getprojectpath("france_parts.qgs").strpath

    qs = "/wmtscache/collections/{}".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'project' in json_content
    assert json_content['project'] == client.getprojectpath("france_parts.qgs").strpath

    assert 'links' in json_content
    assert len(json_content['links']) == 3
    assert json_content['links'][0]['title'] == 'WMTS Cache manager ProjectCollection as JSON'
    assert json_content['links'][0]['rel'] == 'self'

    qs = "/wmtscache/collections/{}/docs".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'project' in json_content
    assert json_content['project'] == client.getprojectpath("france_parts.qgs").strpath

    assert 'documents' in json_content
    assert json_content['documents'] == 1

    assert 'links' in json_content
    assert len(json_content['links']) == 1
    assert json_content['links'][0]['title'] == 'WMTS Cache manager DocumentCollection as JSON'
    assert json_content['links'][0]['rel'] == 'self'

    qs = "/wmtscache/collections/{}/layers".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'project' in json_content
    assert json_content['project'] == client.getprojectpath("france_parts.qgs").strpath

    assert 'layers' in json_content
    assert len(json_content['layers']) == 1

    assert 'links' in json_content
    assert len(json_content['links']) == 1
    assert json_content['links'][0]['title'] == 'WMTS Cache manager LayerCollection as JSON'
    assert json_content['links'][0]['rel'] == 'self'

    layer = json_content['layers'][0]
    assert 'id' in layer
    assert 'links' in layer

    qs = "/wmtscache/collections/{}/layers/{}".format(collection['id'], layer['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == layer['id']

    assert 'links' in json_content
    assert len(json_content['links']) == 1
    assert json_content['links'][0]['title'] == 'WMTS Cache manager LayerCache as JSON'
    assert json_content['links'][0]['rel'] == 'self'


def test_wmts_cachemngrapi_delete_docs(client):
    """ Test the API with to remove docs cache
        /wmtscache/collections
        /wmtscache/collection/(?<collectionId>[^/]+?)/docs
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
    qs = "/wmtscache/collections"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'collections' in json_content
    assert len(json_content['collections']) == 1

    collection = json_content['collections'][0]
    assert 'id' in collection
    assert 'links' in collection
    assert 'project' in collection
    assert collection['project'] == client.getprojectpath("france_parts.qgs").strpath

    # Get docs info
    qs = "/wmtscache/collections/{}/docs".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'project' in json_content
    assert json_content['project'] == client.getprojectpath("france_parts.qgs").strpath

    assert 'documents' in json_content
    assert json_content['documents'] == 1

    # Delete docs
    qs = "/wmtscache/collections/{}/docs".format(collection['id'])
    rv = client.delete(qs)
    assert rv.status_code == 200

    # Get docs info
    qs = "/wmtscache/collections/{}/docs".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

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
        /wmtscache/collections
        /wmtscache/collection/(?<collectionId>[^/]+?)/layers
        /wmtscache/collection/(?<collectionId>[^/]+?)/layers/(?<layerId>[^/]+?)
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
        "FORMAT": "image/png"
    }

    # Get the cached path from the request parameters
    tilepath = cachefilter._cache.get_tile_cache(project.fileName(),parameters).as_posix()

    assert not os.path.exists(tilepath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())

    # original_content = rv.content

    if rv.status_code != 200:
        LOGGER.error(lxml.etree.tostring(rv.xml, pretty_print=True))

    assert rv.status_code == 200

    # Test that document cache has been created
    assert os.path.exists(tilepath)

    # Cache manager API requests
    qs = "/wmtscache/collections"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'collections' in json_content
    assert len(json_content['collections']) == 1

    collection = json_content['collections'][0]
    assert 'id' in collection
    assert 'links' in collection
    assert 'project' in collection
    assert collection['project'] == client.getprojectpath("france_parts.qgs").strpath

    qs = "/wmtscache/collections/{}/layers".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'layers' in json_content
    assert len(json_content['layers']) == 1

    layer = json_content['layers'][0]
    assert 'id' in layer

    qs = "/wmtscache/collections/{}/layers/{}".format(collection['id'], layer['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == layer['id']

    # Delete layer tiles
    qs = "/wmtscache/collections/{}/layers/{}".format(collection['id'], layer['id'])
    rv = client.delete(qs)
    assert rv.status_code == 200

    # Get layer tiles info
    qs = "/wmtscache/collections/{}/layers/{}".format(collection['id'], layer['id'])
    rv = client.get(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    # Get layers info
    qs = "/wmtscache/collections/{}/layers".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'layers' in json_content
    assert len(json_content['layers']) == 0

    # Test that tiles cache has been deleted
    assert not os.path.exists(tilepath)

def test_wmts_cachemngrapi_delete_layers(client):
    """ Test the API with to remove docs cache
        /wmtscache/collections
        /wmtscache/collection/(?<collectionId>[^/]+?)/layers
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
        "FORMAT": "image/png"
    }

    # Get the cached path from the request parameters
    tilepath = cachefilter._cache.get_tile_cache(project.fileName(),parameters).as_posix()

    assert not os.path.exists(tilepath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())

    # original_content = rv.content

    if rv.status_code != 200:
        LOGGER.error(lxml.etree.tostring(rv.xml, pretty_print=True))

    assert rv.status_code == 200

    # Test that tile cache has been created
    assert os.path.exists(tilepath)

    # Cache manager API requests
    qs = "/wmtscache/collections"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'collections' in json_content
    assert len(json_content['collections']) == 1

    collection = json_content['collections'][0]
    assert 'id' in collection
    assert 'links' in collection
    assert 'project' in collection
    assert collection['project'] == client.getprojectpath("france_parts.qgs").strpath

    # Get layers info
    qs = "/wmtscache/collections/{}/layers".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'layers' in json_content
    assert len(json_content['layers']) == 1

    # Delete layers tiles
    qs = "/wmtscache/collections/{}/layers".format(collection['id'])
    rv = client.delete(qs)
    assert rv.status_code == 200

    # Get layers info
    qs = "/wmtscache/collections/{}/layers".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'layers' in json_content
    assert len(json_content['layers']) == 0

    # Test that tiles cache has been deleted
    assert not os.path.exists(tilepath)


def test_wmts_cachemngrapi_delete_collection(client):
    """ Test the API with to remove docs cache
        /wmtscache/collections
        /wmtscache/collection/(?<collectionId>[^/]+?)
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
        "FORMAT": "image/png"
    }

    # Get the cached path from the request parameters
    tilepath = cachefilter._cache.get_tile_cache(project.fileName(),parameters).as_posix()

    assert not os.path.exists(tilepath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())

    # original_content = rv.content

    if rv.status_code != 200:
        LOGGER.error(lxml.etree.tostring(rv.xml, pretty_print=True))

    assert rv.status_code == 200

    # Test that document cache has been created
    assert os.path.exists(tilepath)

    # Cache manager API requests
    qs = "/wmtscache/collections"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'collections' in json_content
    assert len(json_content['collections']) == 1

    collection = json_content['collections'][0]
    assert 'id' in collection
    assert 'links' in collection
    assert 'project' in collection
    assert collection['project'] == client.getprojectpath("france_parts.qgs").strpath

    # Get docs info
    qs = "/wmtscache/collections/{}/docs".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'project' in json_content
    assert json_content['project'] == client.getprojectpath("france_parts.qgs").strpath

    assert 'documents' in json_content
    assert json_content['documents'] == 1

    # Get layers info
    qs = "/wmtscache/collections/{}/layers".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'layers' in json_content
    assert len(json_content['layers']) == 1

    # Delete collection documents and layers tiles
    qs = "/wmtscache/collections/{}".format(collection['id'])
    rv = client.delete(qs)
    assert rv.status_code == 200

    # Get docs info
    qs = "/wmtscache/collections/{}/docs".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    # Test that document cache has been deleted
    assert not os.path.exists(docpath)

    # Get layers info
    qs = "/wmtscache/collections/{}/layers".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    # Test that tiles cache has been deleted
    assert not os.path.exists(tilepath)

    # Get collections info
    qs = "/wmtscache/collections"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'collections' in json_content
    assert len(json_content['collections']) == 0


def test_wmts_cachemngrapi_layerid_error(client):
    """ Test the API with empty cache
        /wmtscache/collection/(?<collectionId>[^/]+?)
        /wmtscache/collection/(?<collectionId>[^/]+?)/layers
        /wmtscache/collection/(?<collectionId>[^/]+?)/layers/(?<layerId>[^/]+?)
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
        "FORMAT": "image/png"
    }

    # Get the cached path from the request parameters
    tilepath = cachefilter._cache.get_tile_cache(project.fileName(),parameters).as_posix()

    assert not os.path.exists(tilepath)

    # Make a request
    qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
    rv = client.get(qs, project.fileName())

    # original_content = rv.content

    if rv.status_code != 200:
        LOGGER.error(lxml.etree.tostring(rv.xml, pretty_print=True))

    assert rv.status_code == 200

    # Test that tile cache has been created
    assert os.path.exists(tilepath)

    # Cache manager API requests
    qs = "/wmtscache/collections"
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'collections' in json_content
    assert len(json_content['collections']) == 1

    collection = json_content['collections'][0]
    assert 'id' in collection
    assert 'links' in collection
    assert 'project' in collection
    assert collection['project'] == client.getprojectpath("france_parts.qgs").strpath

    # Get layers info
    qs = "/wmtscache/collections/{}/layers".format(collection['id'])
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == collection['id']

    assert 'layers' in json_content
    assert len(json_content['layers']) == 1

    qs = "/wmtscache/collections/{}/layers/{}".format(collection['id'], 'foobar')
    rv = client.delete(qs)
    assert rv.status_code == 404

    json_content = json.loads(rv.content)
    assert 'error' in json_content
    assert json_content['error'].get('message') == "Layer 'foobar' not found"


def test_wmts_cachemngrapi_collectionid_error(client):
    """ Test the API with empty cache
        /wmtscache/collection/(?<collectionId>[^/]+?)
        /wmtscache/collection/(?<collectionId>[^/]+?)/docs
        /wmtscache/collection/(?<collectionId>[^/]+?)/layers
        /wmtscache/collection/(?<collectionId>[^/]+?)/layers/(?<layerId>[^/]+?)
    """

    qs = "/wmtscache/collections/{}".format('foobar')
    rv = client.delete(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'error' in json_content
    assert json_content['error'].get('message') == "Collection 'foobar' not found"

    qs = "/wmtscache/collections/{}/docs".format('foobar')
    rv = client.delete(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'error' in json_content
    assert json_content['error'].get('message') == "Collection 'foobar' not found"

    qs = "/wmtscache/collections/{}/layers".format('foobar')
    rv = client.delete(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'error' in json_content
    assert json_content['error'].get('message') == "Collection 'foobar' not found"

    qs = "/wmtscache/collections/{0}/layers/{0}".format('foobar')
    rv = client.delete(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'error' in json_content
    assert json_content['error'].get('message') == "Collection 'foobar' not found"

