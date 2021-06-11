import json

from pathlib import Path
from shutil import rmtree

from qgis.PyQt.QtCore import QRegularExpression
from qgis.server import (
    QgsServerOgcApi,
    QgsServerOgcApiHandler,
    QgsServerRequest,
)

from .helper import CacheHelper


def read_metadata(rootdir: Path) -> dict:
    """ Read metadata
    """

    metadata = rootdir / 'wmts.json'
    if not metadata.exists():
        raise Exception('Cannot read cache metadata!')

    metadata = json.loads(metadata.read_text())

    data = {}
    for c in rootdir.glob('*.inf'):
        d = c.with_suffix('')
        h = d.name

        tiledir = d / 'tiles'
        layers = [layer.name for layer in tiledir.glob('*') if layer.is_dir()]

        data[h] = {
            'project': c.read_text(),
            'layers': layers,
        }
    # metadata.update(data=data)
    metadata['data'] = data
    return metadata


class QgsServerApiException:

    def __init__(self, code, message, mime_type = 'application/json', response_code = 200):
        self.code = code
        self.message = message
        self.mime_type = mime_type
        self.response_code = response_code

    def formatResponse(self):
        return json.dumps({
            'code': self.code,
            'description': self.what()
        }), self.mime_type

    def responseCode(self):
        return self.response_code

    def what(self):
        return self.message


class QgsServerApiNotFoundError(QgsServerApiException):

    def __init__(self, message, mime_type = 'application/json', response_code = 404):
        super().__init__('API not found error', message, mime_type, response_code)


class CacheMngrApiHandler(QgsServerOgcApiHandler):

    def __init__(self, rootdir):
        super().__init__()
        self.setContentTypes([QgsServerOgcApi.JSON, QgsServerOgcApi.HTML])

        self.rootdir = rootdir

    def sendException(self, ex, context):
        resp_content, mime_type = ex.formatResponse()
        resp = context.response()
        resp.clear()
        resp.setStatusCode(ex.responseCode())
        resp.setHeader("Content-Type", mime_type)
        resp.write(resp_content)


class CacheMngrLandingPageHandler(CacheMngrApiHandler):
    """Project listing handler"""

    def path(self):
        return QRegularExpression(r"(\.json|\.html|/)")

    def operationId(self):
        return "getLandingPage"

    def summary(self):
        return "WMTS Cache Manager landing page"

    def description(self):
        return "WMTS Cache Manager landing page"

    def linkTitle(self):
        return "WMTS Cache Manager landing page"

    def linkType(self):
        return QgsServerOgcApi.items

    def handleRequest(self, context):
        """List projects"""

        data = {
            "links": []  # self.links(context)
        }
        data['links'].append({
            "href": self.href(context, "/collections"),
            "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.data),
            "type": QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
            "title": "Cache collections",
        })

        html_metadata = {
            "pageTitle": self.linkTitle(),
            "navigation": []
        }

        self.write(data, context, html_metadata)

    def templatePath(self, context):
        # No templates!
        return ''

    def parameters(self, context):
        return []


class CacheMngrCollectionsHandler(CacheMngrApiHandler):
    """Project listing handler"""

    def path(self):
        return QRegularExpression(r"/collections(\.json|\.html|/)")

    def operationId(self):
        return "describeCollections"

    def summary(self):
        return "WMTS Cache Collections (Projects)"

    def description(self):
        return "WMTS Cache Collections (Projects)"

    def linkTitle(self):
        return "WMTS Cache Collections (Projects)"

    def linkType(self):
        return QgsServerOgcApi.items

    def handleRequest(self, context):
        """List projects"""

        metadata = read_metadata(self.rootdir)

        data = {
            "cache_layout": metadata['layout'],
            "collections": [],
            "links": []  # self.links(context),
        }

        for h, v in metadata['data'].items():
            data['collections'].append({
                'id': h,
                'project': v['project'],
                'links': [{
                    "href": self.href(context, "/{}".format(h), QgsServerOgcApi.contentTypeToExtension(QgsServerOgcApi.JSON)),
                    "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                    "type": QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                    "title": "Cache collection",
                }]
            })

        html_metadata = {
            "pageTitle": self.linkTitle(),
            "navigation": [{
                'title': 'Landing page',
                'href': self.parentLink(context.request().url(), 1)
            }]
        }

        self.write(data, context, html_metadata)

    def templatePath(self, context):
        # No templates!
        return ''

    def parameters(self, context):
        return []


class CacheMngrCollectionHandler(CacheMngrApiHandler):
    """Project listing handler"""

    def path(self):
        return QRegularExpression(r"/collections/(?<collectionId>[^/]+?)(\.json|\.html|/)")

    def operationId(self):
        return "describeCollection"

    def summary(self):
        return "WMTS Cache Collection (Project)"

    def description(self):
        return "WMTS Cache Collection (Project)"

    def linkTitle(self):
        return "WMTS Cache Collection (Project)"

    def linkType(self):
        return QgsServerOgcApi.items

    def handleRequest(self, context):
        """List projects"""

        match = self.path().match(context.request().url().path())
        if not match.hasMatch():
            self.sendException(QgsServerApiNotFoundError("Collection was not found"), context)
            return

        collection_id = match.captured('collectionId')

        metadata = read_metadata(self.rootdir)

        if collection_id not in metadata['data']:
            self.sendException(QgsServerApiNotFoundError("Collection was not found"), context)
            return

        collection_data = {h: v for h, v in metadata['data'].items() if h == collection_id}

        if context.request().method() == QgsServerRequest.DeleteMethod:
            cache = CacheHelper(self.rootdir, metadata['layout'])
            for h, v in collection_data.items():
                project = v['project']
                # Remove docs
                docroot = cache.get_documents_root(project)
                if docroot.exists():
                    rmtree(docroot.as_posix())
                # Remove tiles
                tileroot = cache.get_tiles_root(project)
                if tileroot.exists():
                    rmtree(tileroot.as_posix())
                # Remove medatata infos
                cachedir = self.rootdir / h
                inf = cachedir.with_suffix('.inf')
                if inf.exists():
                    inf.unlink()
                self.write({}, context)
        else:
            data = {
            }
            for h, v in collection_data.items():
                data['id'] = h
                data['project'] = v['project']
                data['layers'] = []
                for layer in v['layers']:
                    data['layers'].append({
                        'id': layer,
                        'links': [{
                            "href": self.href(
                                context,
                                "/layers/{}".format(layer),
                                QgsServerOgcApi.contentTypeToExtension(QgsServerOgcApi.JSON)
                            ),
                            "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                            "type": QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                            "title": "Cache layer",
                        }]
                    })
            data['links'] = []  # self.links(context)
            data['links'].append({
                "href": self.href(context, "/docs", QgsServerOgcApi.contentTypeToExtension(QgsServerOgcApi.JSON)),
                "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                "type": QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                "title": "Cache collection documents",
            })
            data['links'].append({
                "href": self.href(context, "/layers", QgsServerOgcApi.contentTypeToExtension(QgsServerOgcApi.JSON)),
                "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                "type": QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                "title": "Cache collection layers",
            })

            html_metadata = {
                "pageTitle": self.linkTitle(),
                "navigation": [{
                    'title': 'Landing page',
                    'href': self.parentLink(context.request().url(), 2)
                }, {
                    'title': 'Collections',
                    'href': self.parentLink(context.request().url(), 1)
                }]
            }

            self.write(data, context, html_metadata)

    def templatePath(self, context):
        # No templates!
        return ''

    def parameters(self, context):
        return []


class CacheMngrCollectionDocsHandler(CacheMngrApiHandler):
    """Project listing handler"""

    def path(self):
        return QRegularExpression(r"/collections/(?<collectionId>[^/]+?)/docs(\.json|\.html|/)")

    def operationId(self):
        return "describeDocs"

    def summary(self):
        return "WMTS Cache Collection (Project) Documents"

    def description(self):
        return "WMTS Cache Collection (Project) Documents"

    def linkTitle(self):
        return "WMTS Cache Collection (Project) Documents"

    def linkType(self):
        return QgsServerOgcApi.items

    def handleRequest(self, context):
        """List projects"""

        match = self.path().match(context.request().url().path())
        if not match.hasMatch():
            self.sendException(QgsServerApiNotFoundError("Collection was not found"), context)
            return

        collection_id = match.captured('collectionId')

        metadata = read_metadata(self.rootdir)

        if collection_id not in metadata['data']:
            self.sendException(QgsServerApiNotFoundError("Collection was not found"), context)
            return

        collection_data = {h: v for h, v in metadata['data'].items() if h == collection_id}

        cache = CacheHelper(self.rootdir, metadata['layout'])

        data = {}
        for h, v in collection_data.items():
            project = v['project']
            if context.request().method() == QgsServerRequest.DeleteMethod:
                # Remove docs
                docroot = cache.get_documents_root(project)
                if docroot.exists():
                    rmtree(docroot.as_posix())
                self.write(data, context)
            else:

                data['id'] = h
                data['project'] = project
                data['documents'] = 0
                data['links'] = []  # self.links(context)

                docroot = cache.get_documents_root(project)
                for _ in docroot.glob('*.xml'):
                    data['documents'] += 1

                html_metadata = {
                    "pageTitle": self.linkTitle(),
                    "navigation": [{
                        'title': 'Landing page',
                        'href': self.parentLink(context.request().url(), 3)
                    }, {
                        'title': 'Collections',
                        'href': self.parentLink(context.request().url(), 2)
                    }, {
                        'title': 'Collection',
                        'href': self.parentLink(context.request().url(), 1)
                    }]
                }

                self.write(data, context, html_metadata)

    def templatePath(self, context):
        # No templates!
        return ''

    def parameters(self, context):
        return []


class CacheMngrCollectionLayersHandler(CacheMngrApiHandler):
    """Project listing handler"""

    def path(self):
        return QRegularExpression(r"/collections/(?<collectionId>[^/]+?)/layers(\.json|\.html|/)")

    def operationId(self):
        return "describeLayers"

    def summary(self):
        return "WMTS Cache Collection (Project) layers"

    def description(self):
        return "WMTS Cache Collection (Project) layers"

    def linkTitle(self):
        return "WMTS Cache Collection (Project) layers"

    def linkType(self):
        return QgsServerOgcApi.items

    def handleRequest(self, context):
        """List projects"""

        match = self.path().match(context.request().url().path())
        if not match.hasMatch():
            self.sendException(QgsServerApiNotFoundError("Collection was not found"), context)
            return

        collection_id = match.captured('collectionId')

        metadata = read_metadata(self.rootdir)

        if collection_id not in metadata['data']:
            self.sendException(QgsServerApiNotFoundError("Collection was not found"), context)
            return

        collection_data = {h: v for h, v in metadata['data'].items() if h == collection_id}

        cache = CacheHelper(self.rootdir, metadata['layout'])

        data = {}
        for h, v in collection_data.items():
            if context.request().method() == QgsServerRequest.DeleteMethod:
                project = v['project']
                # Remove tiles
                tileroot = cache.get_tiles_root(project)
                if tileroot.exists():
                    rmtree(tileroot.as_posix())
                self.write(data, context)
            else:
                data['id'] = h
                data['project'] = v['project']
                data['layers'] = []
                for layer in v['layers']:
                    data['layers'].append({
                        'id': layer,
                        'links': [{
                            "href": self.href(
                                context,
                                "/layers/{}".format(layer),
                                QgsServerOgcApi.contentTypeToExtension(QgsServerOgcApi.JSON)
                            ),
                            "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                            "type": QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                            "title": "Cache layer",
                        }]
                    })
                data['links'] = []  # self.links(context)

                html_metadata = {
                    "pageTitle": self.linkTitle(),
                    "navigation": [{
                        'title': 'Landing page',
                        'href': self.parentLink(context.request().url(), 3)
                    }, {
                        'title': 'Collections',
                        'href': self.parentLink(context.request().url(), 2)
                    }, {
                        'title': 'Collection',
                        'href': self.parentLink(context.request().url(), 1)
                    }]
                }

                self.write(data, context, html_metadata)

    def templatePath(self, context):
        # No templates!
        return ''

    def parameters(self, context):
        return []


class CacheMngrCollectionLayerHandler(CacheMngrApiHandler):
    """Project listing handler"""

    def path(self):
        return QRegularExpression(r"/collections/(?<collectionId>[^/]+?)/layers/(?<layerId>[^/]+?)(\.json|\.html|/)")

    def operationId(self):
        return "describeLayer"

    def summary(self):
        return "WMTS Cache Collection (Project) layer"

    def description(self):
        return "WMTS Cache Collection (Project) layer"

    def linkTitle(self):
        return "WMTS Cache Collection (Project) layer"

    def linkType(self):
        return QgsServerOgcApi.items

    def handleRequest(self, context):
        """List projects"""

        match = self.path().match(context.request().url().path())
        if not match.hasMatch():
            self.sendException(QgsServerApiNotFoundError("Collection was not found"), context)
            return

        collection_id = match.captured('collectionId')

        metadata = read_metadata(self.rootdir)

        if collection_id not in metadata['data']:
            self.sendException(QgsServerApiNotFoundError("Collection was not found"), context)
            return

        collection_data = {h: v for h, v in metadata['data'].items() if h == collection_id}

        layer_id = match.captured('layerId')

        cache = CacheHelper(self.rootdir, metadata['layout'])

        data = {}
        for _, v in collection_data.items():
            if layer_id not in v['layers']:
                self.sendException(QgsServerApiNotFoundError("Layer was not found"), context)
                return

            if context.request().method() == QgsServerRequest.DeleteMethod:
                project = v['project']
                # Remove tiles
                tileroot = cache.get_tiles_root(project)
                cachedir = tileroot / layer_id
                if cachedir.exists():
                    rmtree(cachedir.as_posix())
                self.write(data, context)
            else:
                data['id'] = layer_id
                data['links'] = []  # self.links(context)

                html_metadata = {
                    "pageTitle": self.linkTitle(),
                    "navigation": [{
                        'title': 'Landing page',
                        'href': self.parentLink(context.request().url(), 4)
                    }, {
                        'title': 'Collections',
                        'href': self.parentLink(context.request().url(), 3)
                    }, {
                        'title': 'Collection',
                        'href': self.parentLink(context.request().url(), 2)
                    }, {
                        'title': 'Layers',
                        'href': self.parentLink(context.request().url(), 1)
                    }]
                }

                self.write(data, context, html_metadata)

    def templatePath(self, context):
        # No templates!
        return ''

    def parameters(self, context):
        return []


class CacheMngrApi(QgsServerOgcApi):

    def __init__(self, serverIface, rootpath):
        super().__init__(serverIface, '/cachemngr',
                         'cache manager api', 'a cache manager api',
                         '1.0')
        self.registerHandler(CacheMngrCollectionLayerHandler(rootpath))
        self.registerHandler(CacheMngrCollectionLayersHandler(rootpath))
        self.registerHandler(CacheMngrCollectionDocsHandler(rootpath))
        self.registerHandler(CacheMngrCollectionHandler(rootpath))
        self.registerHandler(CacheMngrCollectionsHandler(rootpath))
        self.registerHandler(CacheMngrLandingPageHandler(rootpath))
        self.rootpath = rootpath
