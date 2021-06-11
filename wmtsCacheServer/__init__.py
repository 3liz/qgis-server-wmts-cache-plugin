""" QGIS server plugin filter - Cache WMTS output on disk

    author: David Marteau (3liz)
    Copyright: (C) 2019 3Liz
"""

from qgis.server import QgsServerInterface


def serverClassFactory(serverIface: 'QgsServerInterface'):
    """ Plugin entry point
    """
    # save reference to the QGIS interface
    from .wmtsCacheServer import wmtsCacheServer
    return wmtsCacheServer(serverIface)
