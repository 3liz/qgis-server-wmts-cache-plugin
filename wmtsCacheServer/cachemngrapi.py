import json
import mimetypes

from pathlib import Path
from shutil import rmtree

from typing import Optional, Tuple, Iterable, Dict, Any

from qgis.server import QgsServerOgcApi

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
                if ct != QgsServerOgcApi.JSON:
                    # Collections only implement JSON
                    continue
                yield {
                    "href": self.href("/collections", QgsServerOgcApi.contentTypeToExtension(ct) if ct != QgsServerOgcApi.JSON else ''),
                    "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.data),
                    "type": QgsServerOgcApi.mimeType(ct),
                    "title": 'WMTS Cache manager Collections as '+QgsServerOgcApi.contentTypeToString(ct),
                }

        data = {
            'links': self.links() + list(extra_links())
        }
        self.write(data)


class Collections(RequestHandler):
    """ Project listing handler
    """
    def get(self) -> None:
        """ List projects
        """
        metadata, coll = read_metadata_collection(self.rootdir)

        def collection_links(name):
            """ Build links to collection
            """
            for ct in self._parent.contentTypes():
                if ct != QgsServerOgcApi.JSON:
                    # ProjectCollection only implement JSON
                    continue
                yield {
                    "href": self.href(f"/{name}", QgsServerOgcApi.contentTypeToExtension(ct) if ct != QgsServerOgcApi.JSON else ''),
                    "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                    "type": QgsServerOgcApi.mimeType(ct),
                    "title": 'WMTS Cache manager ProjectCollection as '+QgsServerOgcApi.contentTypeToString(ct),
                }

        def collections():
            for name,project in coll:
                yield { 'id': name,
                        'project': project,
                        'links': list(collection_links(name))
                        }

        data = {
            "cache_layout": metadata['layout'],
            "collections": list(collections()),
            "links": self.links(),
        }

        self.write(data)


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

        def layer_collections():
            for layer in layers:
                yield { 'id': layer,
                        'links': [{
                            'href': self.href(f"/layers/{layer}"),
                            'rel': QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                            'type': QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                            'title': "Cache layer",
                        }]}

        data = {
            'id': collectionid,
            'project': project,
            'layers' : list(layer_collections()),
            'links'  : self.links() + [
                {
                    "href": self.href("/docs"),
                    "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                    "type": QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                    "title": "Cache collection documents",
                },
                {
                    "href": self.href("/layers"),
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

        self.write({ 'deleted': collectionid, 'project': project })


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

        self.write({ 'deleted': collectionid, 'documents': str(docroot) })


class LayerCollection(RequestHandler,MetadataMixIn):
    """
    """

    def get(self, collectionid):
        """ Layer info
        """
        metadata,project,layers = self.get_metadata(collectionid)

        def layer_collections():
            for layer in layers:
                yield { 'id': layer,
                        'links': [{
                            'href': self.href(f"/{layer}"),
                            'rel': QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                            'type': QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                            'title': "Cache layer",
                        }]}

        data = {
            'id': collectionid,
            'project': project,
            'layers' : list(layer_collections()),
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

        self.write({ 'deleted': collectionid, 'tiles': str(tileroot) })


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

        self.write({ 'deleted': collectionid, 'tiles': str(cachedir) })
#
# Web Manager
#

class WebManager(RequestHandler,MetadataMixIn):
    """ Manage UI
    """
    def initialize(self, staticpath: Path, **kwargs: Any ) -> None:
        """ May be overrided
        """
        self.staticpath = staticpath

    def get_content_type(self, resource: Path) -> str:
        """Returns the ``Content-Type`` header to be used for this request.
        """
        mime_type, encoding = mimetypes.guess_type(str(resource))
        # per RFC 6713, use the appropriate type for a gzip compressed file
        if encoding == "gzip":
            return "application/gzip"
        # As of 2015-07-21 there is no bzip2 encoding defined at
        # http://www.iana.org/assignments/media-types/media-types.xhtml
        # So for that (and any other encoding), use octet-stream.
        elif encoding is not None:
            return "application/octet-stream"
        elif mime_type is not None:
            return mime_type
        # if mime_type not detected, use application/octet-stream
        else:
            return "application/octet-stream"

    def head( self, path: Optional[str] = None) -> None:
        """ HEAD request
        """
        self.get(path, write_content=False)

    def get( self, path: Optional[str] = None, write_content: bool = True ) -> None:
        """ Return static file
        """
        if not path:
            if not self._request.url().path().endswith('/'):
                # Redirect permanently
                self.set_header('Location','/wmtscache/manager/');
                self.set_status(301)
                return
            else:
                path = "index.html"

        resource = self.staticpath / path
        if not resource.is_absolute():
            raise HTTPError(403)
        if not resource.is_file():
            raise HTTPError(404)

        stat = resource.stat()

        # Set Headers
        self.set_header('Content-Type'   , self.get_content_type(resource))
        self.set_header('Content-Length' , str(stat.st_size))

        if write_content:
            with resource.open('rb') as fp:
                content = fp.read()
            self.write(content)   



def init_cache_api(serverIface, cacherootdir: Path) -> None:
    """ Initialize the cache manager API
    """
    collectionid = r"collections/(?P<collectionid>[^/]+)"

    kwargs = dict(rootdir=cacherootdir)

    # Because the way plugin are installed in Qgis we cannot rely on pkg_resources
    # Do it the old way
    staticpath = Path(__file__).parent / "resources" / "www"

    handlers = [
        (rf"/{collectionid}/layers/(?P<layerid>[^/]+)/?", LayerCache, kwargs),
        (rf"/{collectionid}/layers/?", LayerCollection, kwargs),
        (rf"/{collectionid}/docs/?", DocumentCollection, kwargs),
        (rf"/{collectionid}/?", ProjectCollection,  kwargs),
        (r"/collections/?", Collections, kwargs),
        (r"/manager/(?P<path>.+)", WebManager, {'staticpath': staticpath}),
        (r"/manager/?", WebManager, {'staticpath': staticpath}),
        (r"/?", LandingPage, kwargs),
    ]

    register_api_handlers(serverIface, '/wmtscache', 'WMTSCacheManagment', handlers)


