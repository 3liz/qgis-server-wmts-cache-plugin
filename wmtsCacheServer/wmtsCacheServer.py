""" QGIS server plugin filter - Cache WMTS output on disk

    author: David Marteau (3liz)
    Copyright: (C) 2019 3Liz
"""

import os

from qgis.core import Qgis, QgsMessageLog
from pathlib import Path

from .cachefilter import DiskCacheFilter

class wmtsCacheServer:
    """ Plugin for QGIS server
    """

    def __init__(self, serverIface: 'QgsServerInterface') -> None:
        # save reference to the QGIS interface         
        self.serverIface = serverIface

        # Ensure that configuration is OK
        rootpathstr = os.getenv('QGIS_WMTS_CACHE_ROOTDIR')
        if not rootpathstr:
            QgsMessageLog.logMessage('QGIS_WMTS_CACHE_ROOTDIR not defined, cache disabled','wmtsCache',Qgis.Critical)
            return

        rootpath = Path(rootpathstr)
        if not rootpath.is_dir():
            QgsMessageLog.logMessage('WMTS Cache directory %s must exists and must be a directory, cache disabled' % rootpathstr,
                   'wmtsCache',Qgis.Critical)
            return

        # Get tile layout
        layout = os.getenv('QGIS_WMTS_CACHE_LAYOUT', 'tc')

        serverIface.registerFilter( DiskCacheFilter(serverIface, rootpath, layout), 50 )

