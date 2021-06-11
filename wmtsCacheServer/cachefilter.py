""" QGIS server plugin filter - Cache WMTS output on disk

    author: David Marteau (3liz)
    Copyright: (C) 2019 3Liz
"""

import traceback

from qgis.core import Qgis, QgsMessageLog, QgsProject
from qgis.server import QgsServerCacheFilter, QgsServerRequest, QgsServerInterface
from qgis.PyQt.QtCore import QByteArray
from qgis.PyQt.QtXml import QDomDocument

from pathlib import Path
from typing import Union, TypeVar
from contextlib import contextmanager
from shutil import rmtree
from datetime import datetime

from .helper import CacheHelper

Hash = TypeVar('Hash')


@contextmanager
def trap():
    """ Define a trap context for catchinf exception
        and send them to error log
    """
    try:
        yield
    except Exception as e:
        QgsMessageLog.logMessage("WMTS Cache exception: %s\n%s" % (e,traceback.format_exc()) ,"wmtsCache",Qgis.Critical)


class DiskCacheFilter(QgsServerCacheFilter):

    def __init__(self, serverIface: 'QgsServerInterface', rootdir: Path, layout: str,
                 debug: bool=False) -> None:
        super().__init__(serverIface)

        self._iface = serverIface
        self._cache = CacheHelper(rootdir, layout)
        self._debug  = debug

    def set_debug_headers(self, path: str) -> None:
        """ Add a response header to tag cached response
        """
        if not self._debug:
            return

        rh = self._iface.requestHandler()
        if rh:
            rh.setResponseHeader("X-Qgis-Debug-Cache-Plugin" ,"wmtsCacheServer")
            rh.setResponseHeader("X-Qgis-Debug-Cache-Path"   , path.as_posix())

    def get_document_cache( self, project: 'QgsProject', request: 'QgsServerRequest' , create_dir=False) -> Path:
        """ Return cache location for document
        """
        last_modified = datetime.fromtimestamp(project.lastModified().toMSecsSinceEpoch() / 1000.0)
        return self._cache.get_document_cache(
            project.fileName(), request.parameters(),
            create_dir=create_dir, last_modified=last_modified
        )

    def setCachedDocument(self, doc: QDomDocument, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> bool:
        """ Override QgsServerCacheFilter::setCachedDocument
        """
        if not doc or request.parameters().get('SERVICE','').upper() != 'WMTS' :
            return False
        with trap():
            p = self.get_document_cache(project,request, create_dir=True)
            with p.open(mode='w') as f:
                f.write(doc.toString())
        return True

    def getCachedDocument(self, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> QByteArray:
        """ Override QgsServerCacheFilter::getCachedDocument
        """
        if request.parameters().get('SERVICE','').upper() != 'WMTS':
            return QByteArray()

        with trap():
            p = self.get_document_cache(project,request)
            if p.is_file():
                with p.open('rb') as f:
                    self.set_debug_headers(path=p)
                    return QByteArray(f.read())

        return QByteArray()

    def deleteCachedDocument(self, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> bool:
        """ Override QgsServerCacheFilter::deleteCachedDocument
        """
        with trap():
            p = self.get_document_cache(project,request)
            if p.is_file():
               p.unlink()
               return True

        return False

    def deleteCachedDocuments(self, project: 'QgsProject') -> bool:
        """ Override QgsServerCacheFilter::deleteCachedDocuments
        """
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
        """ Override QgsServerCacheFilter::setCachedImage
        """
        if request.parameters().get('SERVICE','').upper() == 'WMTS':
            with trap():
                p = self.get_tile_cache(project, request, create_dir=True)
                with p.open(mode='wb') as f:
                    f.write(img)
                    return True

        return False

    def getCachedImage(self, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> QByteArray:
        """ Override QgsServerCacheFilter::getCachedImage
        """
        if request.parameters().get('SERVICE','').upper() == 'WMTS':
            with trap():
                p = self.get_tile_cache(project,request)
                if p.is_file():
                    with p.open('rb') as f:
                        self.set_debug_headers(path=p)
                        return QByteArray(f.read())

        return QByteArray()

    def deleteCachedImage(self, project: 'QgsProject', request: 'QgsServerRequest', key: str) -> bool:
        """ Override QgsServerCacheFilter::deleteCachedImage
        """
        if request.parameters().get('SERVICE','').upper() == 'WMTS':
            with trap():
                p = self.get_tile_cache(project,request)
                if p.is_file():
                   p.unlink()
                   return True

        return False

    def deleteCachedImages(self, project: 'QgsProject') -> bool:
        """ Override QgsServerCacheFilter::deleteCachedImages
        """
        with trap():
            cachedir = self._cache.get_tiles_root(project.fileName())
            if cachedir.is_dir():
                rmtree(cachedir.as_posix())
                return True

        return False
