""" QGIS server plugin filter - Cache WMTS output on disk

    author: David Marteau (3liz)
    Copyright: (C) 2019 3Liz
"""

def serverClassFactory(serverIface: 'QgsServerInterface') -> 'wmtsCacheServer':
    """ Load wfsOutputExtensionServer class from file wfsOutputExtension.
    """
    # save reference to the QGIS interface                 
    from .wmtsCacheServer import wmtsCacheServer
    return wmtsCacheServer(serverIface)

