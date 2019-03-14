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
from typing import Union, Mapping, TypeVar, Dict
from contextlib import contextmanager
from hashlib import md5
from shutil import rmtree

from .layouts import layouts

Hash = TypeVar('Hash')


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
        QgsMessageLog.logMessage("WMTS Cache exception: %s\n%s" % (e,traceback.format_exc()) ,"wmtsCache",Qgis.Critical)


class CacheHelper:

    def __init__(self, rootdir: Path, layout: str) -> None:
        self.rootdir = rootdir
        self.tiledir = rootdir / 'tiles'
        self._tile_location = layouts.get(layout)
        if self._tile_location is None:
            raise ValueError("Unknown tile layout %s" % layout)

    def get_project_hash(self, ident: str) -> Hash:
        """ Attempt to create a hash from project infos
        """
        if not ident:
            raise ValueError("Missing ident value")
        m = md5()
        m.update(ident.encode())
        return m

    def get_document_cache(self, project: str, params: Dict[str,str], suffix: str='.xml', create_dir: bool=False) -> Path:
        """ Create a cache path for the document
        """
        h = self.get_project_hash(project)
        p = self.rootdir / h.hexdigest()

        # XXX: Take care that that order of items is random !
        qs = "&".join("%s=%s" % (k,params[k]) for k in sorted(params.keys())).encode()
        h.update(qs)
        
        digest = h.hexdigest()

        # Create subdirs by taking the first letter of the digest
        if create_dir:
            p.mkdir(mode=0o750, parents=True, exist_ok=True)

        return p / (digest + suffix)

    def get_documents_root(self, project: str) -> Path:
        """ Return base path for documents
        """
        h = self.get_project_hash(project)
        return self.rootdir / h.hexdigest()

    def get_tiles_root(self, project: str) -> Path:
        """ Return base path for tiles
        """
        h = self.get_project_hash(project)
        return self.tiledir / h.hexdigest()

    def get_tile_cache(self, project: str, params: Dict[str,str], create_dir: bool=False) -> Path:
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

        p = self._tile_location(cache_dir / digest, int(x), int(y), z, file_ext)

        if create_dir:
            p.parent.mkdir(mode=0o750, parents=True, exist_ok=True)

        return p


class DiskCacheFilter(QgsServerCacheFilter):

    def __init__(self, serverIface: 'QgsServerInterface', rootdir: Path, layout: str) -> None:
        super().__init__(serverIface)

        self._iface = serverIface
        self._cache = CacheHelper(rootdir, layout)

    def get_document_cache( self, project: 'QgsProject', request: 'QgsServerRequest' , create_dir=False) -> Path:
        return self._cache.get_document_cache(project.fileName(),request.parameters(),create_dir=create_dir)

    def setCachedDocument(self, doc: QDomDocument, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> bool:
        if not doc:
            return False
        with trap():
            p = self.get_document_cache(project,request, create_dir=True)
            with p.open(mode='w') as f:
                f.write(doc.toString())
        return True

    def getCachedDocument(self, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> QByteArray:
        with trap():
            p = self.get_document_cache(project,request)
            if p.is_file():
                with p.open('r') as f:
                    doc = QDomDocument()
                    statusOK, errorStr, errorLine, errorColumn = doc.setContent(f.read(), True)
                    if statusOK:
                        return doc.toByteArray()
                    else:
                        QgsMessageLog.logMessage(
                                ("Failed to get document content:"
                                 "Error at line %d, column %d:\n%s\n"
                                 "File: %s") % (errorLine, errorColumn, errorStr,p.as_posix())
                                ,"wmtsCache", Qgis.Critical)

        return QByteArray()

    def deleteCachedDocument(self, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> bool:
        with trap():
            p = self.get_document_cache(project,request)
            if p.is_file():
               p.unlink()
               return True
        return False

    def deleteCachedDocuments(self, project: 'QgsProject') -> bool:
        with trap():
            cachedir = self._cache.get_documents_root(project.fileName())
            if cachedir.is_dir():
                rmtree(cachedir.as_posix())
                return True
        return False

    def get_tile_cache(self, project: 'QgsProject', request: 'QgsServerRequest' , create_dir=False) -> Path:
        return self._cache.get_tile_cache(project.fileName(),request.parameters(),create_dir=create_dir)

    def setCachedImage(self, img: Union[QByteArray, bytes, bytearray], 
            project: 'QgsProject', request: 'QgsServerRequest', key: str) -> bool:
       
        if request.parameters().get('SERVICE','').upper() != 'WMTS':
            return False

        with trap():
            p = self.get_tile_cache(project, request, create_dir=True)
            with p.open(mode='wb') as f:
                f.write(img)
                return True
        return False

    def getCachedImage(self, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> QByteArray:

        if request.parameters().get('SERVICE','').upper() != 'WMTS':
            return QByteArray()

        with trap():
            p = self.get_tile_cache(project,request)
            if p.is_file():
                with p.open('rb') as f:
                    return QByteArray(f.read())

        return QByteArray()

    def deleteCachedImage(self, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> bool:

        if request.parameters().get('SERVICE','').upper() != 'WMTS':
            return False
        
        with trap():
            p = self.get_tile_cache(project,request)
            if p.is_file():
               p.unlink()
               return True
        return False

    def deleteCachedImages(self, project: 'QgsProject') -> bool:

        with trap():
            cachedir = self._cache.get_tiles_root(project.fileName())
            if cachedir.is_dir():
                rmtree(cachedir.as_posix())
                return True
        return False








