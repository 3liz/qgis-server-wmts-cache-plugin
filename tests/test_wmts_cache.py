import logging

LOGGER = logging.getLogger('server')

def test_wmts_getcapabilities(client):
    """  Test getcapabilites response
    """
    rv = client.get("?MAP=france_parts.qgs&SERVICE=WMTS&request=GetCapabilities","france_parts.qgs")
    assert rv.status_code == 200
    

