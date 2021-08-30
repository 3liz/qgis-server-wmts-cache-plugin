import json
import os

from pathlib import Path
from shutil import rmtree

from typing import Optional, Tuple, Iterable, Dict

from qgis.server import QgsServerOgcApi, QgsServerOgcApiHandler
from qgis.core import Qgis, QgsMessageLog

from .helper import CacheHelper
from .apiutils import HTTPError, RequestHandler, register_api_handlers


def read_wmts_metadata( rootdir ) -> Dict:
    """ Read metadata
    """
    metadata = rootdir / 'wmts.json'
    if not metadata.exists():
        raise Exception('Cannot read cache metadata!')

    return json.loads(metadata.read_text())


def read_metadata_collection(rootdir: Path) -> Tuple[dict,Iterable]:
    """ Read metadata
    """
    metadata = read_wmts_metadata(rootdir)

    def collect():
        for inf in rootdir.glob('*.inf'):
            name = inf.with_suffix('').name
            project = inf.read_text()
            # (name, project)
            yield (name,project)

    return (metadata, collect())


def read_project_metadata( rootdir: Path, name: str ) -> Optional[Tuple[dict,Iterable]]:
    """ Collect metadata about project
    """
    path = rootdir / f"{name}.inf"
    if not path.exists():
        raise FileNotFoundError(name)

    project = path.read_text()

    tiledir = path.with_suffix('') / "tiles"
    layers  = (layer.name for layer in tiledir.glob('*') if layer.is_dir())
    # (project, layers)
    return (project, layers)


#
# WMTS API Handlers
#

class LandingPage(RequestHandler):
    """ Project collections listing handler
    """
    def get(self) -> None:

        def extra_links():
            """ Build links to collections
            """
            for ct in self._parent.contentTypes():
                yield {
                    "href": self.href("/collections", QgsServerOgcApi.contentTypeToExtension(ct) if ct != QgsServerOgcApi.JSON else ''),
                    "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.data),
                    "type": QgsServerOgcApi.mimeType(ct),
                    "title": "Cache collections",
                }

        data = {
            'links': self.links() + list(extra_links())
        }
        self.write(data)

    def link_title(self):
        return 'Cache manager landing page'

    def template_path(self) -> str:
        return os.path.join(os.path.dirname(__file__), 'resources', 'landing_page.html')

    def html_metadata(self) -> dict:
        return {
            'pageTitle': self.link_title(),
            'navigation': []
        }


class CacheCollections(RequestHandler):
    """ Project listing handler
    """
    def get(self) -> None:
        """ List projects
        """
        metadata, coll = read_metadata_collection(self.rootdir)
        current_ct = self._parent.contentTypeFromRequest(self._request)

        def collection_links(name):
            """ Build links to collection
            """
            for ct in self._parent.contentTypes():
                yield {
                    "href": self.href(f"/{name}", QgsServerOgcApi.contentTypeToExtension(ct) if ct != QgsServerOgcApi.JSON else ''),
                    "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                    "type": QgsServerOgcApi.mimeType(ct),
                    "title": f"Cache collection {name}",
                }

        def collections():
            for name, project in coll:
                yield { 'id': name,
                        'project': project,
                        'links': list(collection_links(name))}

        data = {
            "cache_layout": metadata['layout'],
            "collections": list(collections()),
            "links": self.links(),
        }

        self.write(data)

    def link_title(self):
        return 'Cache collections'

    def template_path(self) -> str:
        return os.path.join(os.path.dirname(__file__), 'resources', 'collections.html')

    def html_metadata(self) -> dict:
        return {
            'pageTitle': self.link_title(),
            'navigation': [{
                'title': 'Landing page',
                'href': self.html_parent_link(1)
            }]
        }


class MetadataMixIn:

    def get_metadata(self, collectionid: str):
        """ Return project metadata
        """
        try:
            project, layers = read_project_metadata(self.rootdir, collectionid)
        except FileNotFoundError:
            raise HTTPError(404,reason=f"Collection '{collectionid}' not found") from None

        metadata = read_wmts_metadata(self.rootdir)
        return metadata, project, layers

    def cache_helper(self, metadata):
        """ Return cache helper
        """
        return CacheHelper(self.rootdir, metadata['layout'])


class ProjectCollection(RequestHandler,MetadataMixIn):
    """ Project listing handler
    """

    def get(self, collectionid: str):
        """ Return project metadata
        """
        metadata, project, layers = self.get_metadata(collectionid)

        def links():
            for layer in layers:
                yield { 'id': layer,
                        'links': [{
                            'href': self.href(f"/layers/{layer})", \
                                              QgsServerOgcApi.contentTypeToExtension(QgsServerOgcApi.JSON)),
                            'rel': QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                            'type': QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                            'title': "Cache layer",
                        }]}

        data = {
            'id': collectionid,
            'project': project,
            'layers' : list(links()),
            'links'  : self.links() + [
                {
                    "href": self.href("/docs", QgsServerOgcApi.contentTypeToExtension(QgsServerOgcApi.JSON)),
                    "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                    "type": QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                    "title": "Cache collection documents",
                },
                {
                    "href": self.href("/layers", QgsServerOgcApi.contentTypeToExtension(QgsServerOgcApi.JSON)),
                    "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                    "type": QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                    "title": "Cache collection layers",
                },
            ],
        }

        self.write(data)

    def delete(self, collectionid) -> None:
        """ Clear cache
        """
        metadata,project,_ = self.get_metadata(collectionid)
        cache = self.cache_helper(metadata)

        # Remove docs
        docroot = cache.get_documents_root(project)
        if docroot.exists():
            rmtree(docroot.as_posix())
            # Remove tiles
        tileroot = cache.get_tiles_root(project)
        if tileroot.exists():
            rmtree(tileroot.as_posix())
        # Remove medatata infos
        inf = (self.rootdir / collectionid).with_suffix('.inf')
        if inf.exists():
            inf.unlink()

    def link_title(self):
        return 'Cache collection'

    def template_path(self) -> str:
        return os.path.join(os.path.dirname(__file__), 'resources', 'collection.html')

    def html_metadata(self) -> dict:
        return {
            'pageTitle': self.link_title(),
            'navigation': [{
                'title': 'Landing page',
                'href': self.html_parent_link(2)
            },{
                'title': 'Cache collections',
                'href': self.html_parent_link(1)
            }]
        }

class DocumentCollection(RequestHandler,MetadataMixIn):
    """ Return documentation about project
    """

    def get(self, collectionid):
        """ Get documents count
        """
        metadata,project,_ = self.get_metadata(collectionid)
        cache = self.cache_helper(metadata)

        docroot = cache.get_documents_root(project)
        data = {
            'id': collectionid,
            'project': project,
            'documents': sum( 1 for _ in docroot.glob('*.xml')),
            'links': self.links(),
        }

        self.write(data)


    def delete(self, collectionid ) -> None:
        """ Delete item from cache
        """
        metadata,project,_ = self.get_metadata(collectionid)
        cache = self.cache_helper(metadata)

        docroot = cache.get_documents_root(project)
        if docroot.exists():
            rmtree(docroot.as_posix())


class LayerCollection(RequestHandler,MetadataMixIn):
    """
    """

    def get(self, collectionid):
        """ Layer info
        """
        metadata,project,layers = self.get_metadata(collectionid)

        def links():
            for layer in layers:
                yield { 'id': layer,
                        'links': [{
                            'href': self.href(f"/layers/{layer})", \
                                              QgsServerOgcApi.contentTypeToExtension(QgsServerOgcApi.JSON)),
                            'rel': QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                            'type': QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                            'title': "Cache layer",
                        }]}

        data = {
            'id': collectionid,
            'project': project,
            'layers' : list(links()),
            'links'  : self.links(),
        }

        self.write(data)

    def delete(self, collectionid) -> None:
        """  Delete layer tiles
        """
        metadata,project,_ = self.get_metadata(collectionid)
        cache = self.cache_helper(metadata)

        # Remove tiles
        tileroot = cache.get_tiles_root(project)
        if tileroot.exists():
            rmtree(tileroot.as_posix())


class LayerCache(RequestHandler,MetadataMixIn):
    """ Handle cached layer
    """

    def get( self, collectionid: str, layerid: str) -> None:
        """
        """
        metadata, project, layers = self.get_metadata(collectionid)
        if layerid not in layers:
            raise HTTPError(404,reason=f"Layer '{layerid}' not found")

        data = {
            'id': layerid,
            'links':self.links(),
        }
        self.write(data)


    def delete( self, collectionid: str, layerid: str) -> None:
        """ List projects
        """
        metadata, project, layers = self.get_metadata(collectionid)
        if layerid not in layers:
            raise HTTPError(404,reason=f"Layer '{layerid}' not found")

        cache = self.cache_helper(metadata)
        cache = CacheHelper(self.rootdir, metadata['layout'])

        # Remove tiles
        cachedir = cache.get_tiles_root(project) / layerid
        if cachedir.exists():
            rmtree(cachedir.as_posix())


def init_cache_api(serverIface, cacherootdir: Path) -> None:
    """ Initialize the cache manager API
    """
    collectionid = r"collections/(?P<collectionid>[^/]+)"

    # kwargs without content types for handlers only return JSON
    kwargs = dict(rootdir=cacherootdir)
    # kwargs with content types for handlers return JSON and HTML
    extra_kwargs = dict(
        rootdir=cacherootdir,
        content_types=[QgsServerOgcApi.JSON, QgsServerOgcApi.HTML]
    )

    handlers = [
        (rf"/{collectionid}/layers/(?P<layerid>[^/]+)/?", LayerCache, kwargs),
        (rf"/{collectionid}/layers/?", LayerCollection, kwargs),
        (rf"/{collectionid}/docs/?", DocumentCollection, kwargs),
        (rf"/{collectionid}/?", ProjectCollection,  kwargs),
        (rf"/collections/?", CacheCollections, extra_kwargs)),
        (rf"/?", LandingPage, extra_kwargs)),
    ]

    register_api_handlers(serverIface, '/wmtscache', 'CacheManagment', handlers,
                          activate_static_handler=True)


