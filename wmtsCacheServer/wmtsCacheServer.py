""" QGIS server plugin filter - Cache WMTS output on disk

    author: David Marteau (3liz)
    Copyright: (C) 2019 3Liz
"""

import os
import tempfile

from pathlib import Path

from qgis.core import Qgis, QgsMessageLog
from qgis.server import QgsServerInterface

from .cachefilter import DiskCacheFilter
from .cachemngrapi import init_cache_api


class wmtsCacheServer:
    """ Plugin for QGIS server
    """

    def __init__(self, serverIface: 'QgsServerInterface') -> None:
        # save reference to the QGIS interface
        self.serverIface = serverIface

        # Ensure that configuration is OK
        rootpathstr = os.getenv('QGIS_WMTS_CACHE_ROOTDIR')
        if not rootpathstr:
            # Create cache in /tmp/org.qgis.wmts/cache
            rootpathstr = os.path.join(tempfile.gettempdir(),'org.qgis.wmts')

        self.rootpath = Path(rootpathstr)
        self.rootpath.mkdir(mode=0o750, parents=True, exist_ok=True)

        QgsMessageLog.logMessage('Cache directory set to %s' % rootpathstr,'wmtsCache',Qgis.Info)

        # Get tile layout
        layout = os.getenv('QGIS_WMTS_CACHE_LAYOUT', 'tc')

        # Debug headers
        debug_headers = os.getenv('QGIS_WMTS_CACHE_DEBUG_HEADERS', '').lower() in ('1','yes','y','true')

        serverIface.registerServerCache( DiskCacheFilter(serverIface, self.rootpath, layout,
                                         debug=debug_headers), 50 )

        # Cache Manager API
        init_cache_api(serverIface, self.rootpath)

    def create_filter(self, layout: str=None) -> DiskCacheFilter:
        """ Create a new filter instance
        """
        return DiskCacheFilter(self.serverIface, self.rootpath, layout or 'tc')

