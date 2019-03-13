""" QGIS server plugin filter - Cache WMTS output on disk

    author: David Marteau (3liz)
    Copyright: (C) 2019 3Liz
"""

import os
import tempfile

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
            # Create cache in /tmp/org.qgis.wmts/cache
            rootpathstr = os.path.join(tempfile.gettempdir(),'org.qgis.wmts')
        
        rootpath = Path(rootpathstr)
        rootpath.mkdir(mode=0o750, parents=True, exist_ok=True)

        QgsMessageLog.logMessage('Cache directory set to %s' % rootpathstr,'wmtsCache',Qgis.Info)

        # Get tile layout
        layout = os.getenv('QGIS_WMTS_CACHE_LAYOUT', 'tc')

        serverIface.registerServerCache( DiskCacheFilter(serverIface, rootpath, layout), 50 )

