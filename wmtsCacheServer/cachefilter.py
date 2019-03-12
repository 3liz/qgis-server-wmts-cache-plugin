""" QGIS server plugin filter - Cache WMTS output on disk

    author: David Marteau (3liz)
    Copyright: (C) 2019 3Liz
"""

import os
import traceback

from qgis.core import Qgis, QgsMessageLog
from qgis.server import QgsServerCacheFilter
from qgis.PyQt.QtCore import QByteArray
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtGui import QImage

from pathlib import Path
from typing import Union, Mapping, TypeVar
from contextlib import contextmanager
from hashlib import md5
from shutil import rmtree

from .layouts import layouts

Hash = Typevar('Hash')


def get_image_sfx(fmt: str) -> str:
    """ Return suffix from mimetype
    """
    # XXX: We handle only jpeg and png: do we need
    #    to handle anything else ?
 
    if fmt.startswith('image/jpeg'):
        return '.jpg'
    if fmt.startswith('image/png'):
        return '.png'
    else:
        raise ValueError("Unknown image type %s" % fmt)


@contextmanager
def trap():
    """ Define a trap context for catchinf exception
        and send them to error log
    """
    try:
        yield
    except Exception as e:
        QgsMessageLog("WMTS Cache exception: %s\n%s" % (e,traceback.format_exc()) ,"wmtsCache",Qgis.Critical)


class DiskCacheMngr:

    def __init__(self, rootdir: Path, layout: str) -> None:
        self.rootdir = rootdir
        self.tiledir = rootdir / 'tiles'
        self._tile_location = layouts.get(layout)
        if self._tile_location is None:
            raise ValueError("Unknown tile layout %s" % layout)

    def get_project_hash(self, project: 'QgsProject') -> Hash:
        """ Attempt to create a hash from project infos

            XXX: We are faced to the problem that there is no unambiguous
            way to define unique identifier for a QgsProject except.
            
            This prevent us now for caching data from projects not related to file - like
            dynamically built projects.
        """
        ident = project.filename()
        if not ident:
            raise ValueError("Project with no filename is not supported")
        m = md5()
        m.update(project.filename().encode())
        return m

    def get_document_cache(self, project: 'QgsProject', request: 'QgsServerRequest', suffix: str='xml', create_dir: bool=False) -> Path:
        """ Create a cache path for the document
        """
        params = request.parameters()

        h = self.get_project_hash(project)
        h.update("&".join("%s=%s" % item for items in params.items()).encode())
        
        digest = h.hexdigest()

        # Create subdirs by taking the first letter of the digest
        p = self.rootdir / digest[0]
        if create_dir:
            p.mkdir(mode=0o750, parents=True, exists_ok=True)

        return p / (digest + suffix)

    def get_documents_root(self, project: 'QgsProject') -> Path:
        """ Return base path for documents
        """
        h = self.get_project_hash(project)
        return self.rootdir / h.hexdigest()

    def get_tiles_root(self, project: 'QgsProject') -> Path:
        """ Return base path for tiles
        """
        h = self.get_project_hash(project)
        return self.tiledir / h.hexdigest()

    def get_tile_cache(self, project: 'QgsProject', request: 'QgsServerRequest', create_dir: bool=False) -> Path:
        """ Create a cache path for tile

            The path is computed according to the folowing parameters:

            LAYER (couche, groupe ou projet complet en fonction de la configuration)
            TILEMATRIXSET (le CRS)
            TILEMATRIX (z en tms)
            TILEROW (x en tms)
            TILECOL (y en tms)
            STYLE (le style)
            FORMAT (sous la forme image/*)
        """
        params = request.parameters()

        h = self.get_project_hash(project)
        cache_dir = self.tiledir / h.hexdigest()

        h.update(params.get('LAYER','').encode())
        h.update(params.get('TILEMATRIXSET','').encode())
        h.update(params.get('STYLE','').encode())

        digest = h.hexdigest()

        x,y,z= params['TILEROW'],params['TILECOL'],params['TILEMATRIX']

        # Retrieve file suffix from FORMAT spec
        fmt = params.get('FORMAT')
        file_ext = get_image_sfx(fmt) if fmt else '.png'

        p = self._tile_location(cache_dir / digest, x,y,z,file_ext)

        if create_dir:
            p.parent.mkdir(mode=0o750, exists_ok=True)

        return p


class DiskCacheFilter(QgsServerCacheFilter):

    def __init__(self, serverIface: 'QgsServerInterface', rootdir: Path, layout: str) -> None:
        super().__init__(serverIface)

        self._cache = DiskCacheMngr(rootdir, layout)

    def setCachedDocument(self, doc: QDomDocument, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> bool:
        if not doc:
            return False
        with trap():
            p = self._cache.get_document_cache(project,request, create_dir=True)
            with p.open(mode='w') as f:
                f.write(doc.toString())
        return True

    def getCachedDocument(self, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> QByteArray:
        with trap():
            p = self._cache.get_document_cache(project,request)
            if p.is_file():
                with p.open('r') as f:
                    statusOK, errorStr, errorLine, errorColumn = doc.setContent(f.read(), True)
                    if statusOK:
                        return doc.toByteArrary()
                    else:
                        QgsMessageLog.logMessage(
                                ("Failed to get document content:"
                                 "Error at line %d, column %d:\n%s\n"
                                 "File: %s") % (errorLine, errorColumn, errorStr,p.as_posix())
                                ,"wmtsCache", Qgis.Critical)

        return QByteArray()

    def deleteCachedDocument(self, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> bool:
        with trap():
            p = self._cache.get_document_cache(project,request)
            if p.is_file():
               p.unlink()
               return True
        return False

    def deleteCachedDocuments(self, project: 'QgsProject') -> bool:
        with trap():
            cachedir = self._cache.get_documents_root(project)
            if cachedir.is_dir():
                rmtree(cachedir.as_posix())
                return True
        return False

    def setCachedImage(self, img: Union[QByteArray, bytes, bytearray], 
            project: 'QgsProject', request: 'QgsServerRequest', key: str) -> bool:
        
        with trap():
            p = self._cache.get_tile_cache(project, request, create_dir=True)
            with p.open(mode='wb') as f:
                f.write(img)
                return True
        return False

    def getCachedImage(self, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> QByteArray:
        with trap():
            p = self._cache.get_tile_cache(project,request)
            if p.is_file():
                with p.open('rb') as f:
                    return QByteArray(f.read())

        return QByteArray()

    def deleteCachedImage(self, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> bool:
        with trap():
            p = self._cache.get_tile_cache(project,request)
            if p.is_file():
               p.unlink()
               return True
        return False

    def deleteCachedImages(self, project: 'QgsProject') -> bool:
        with trap():
            cachedir = self._cache.get_tiles_root(project)
            if cachedir.is_dir():
                rmtree(cachedir.as_posix())
                return True
        return False








