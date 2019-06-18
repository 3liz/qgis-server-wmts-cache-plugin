""" Cache helper

    author: David Marteau (3liz)
    Copyright: (C) 2019 3Liz
"""
import os
import json
from pathlib import Path
from typing import Union, Mapping, TypeVar, Dict
from hashlib import md5

from .layouts import layouts

Hash = TypeVar('Hash')

METADATA_VERSION = '1.0'

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


class CacheHelper:

    def __init__(self, rootdir: Path, layout: str) -> None:
        self.rootdir = rootdir
        self._tile_location = layouts.get(layout)
        if self._tile_location is None:
            raise ValueError("Unknown tile layout %s" % layout)

        metadata = rootdir / 'wmts.json'
        metadata.write_text(json.dumps({
                'layout': layout,
            }))

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
        cachedir = self.rootdir / h.hexdigest()
        p = cachedir / "docs"

        # XXX: Take care that that order of items is random !
        qs = "&".join("%s=%s" % (k,params[k]) for k in sorted(params.keys())).encode()
        h.update(qs)
        
        digest = h.hexdigest()

        # Create subdirs by taking the first letter of the digest
        if create_dir:
            p.mkdir(mode=0o750, parents=True, exist_ok=True)
            inf = cachedir.with_suffix('.inf')
            if not inf.exists():
                inf.write_text(project)

        return (p / digest).with_suffix(suffix)

    def get_documents_root(self, project: str) -> Path:
        """ Return base path for documents
        """
        h = self.get_project_hash(project)
        return self.rootdir / h.hexdigest() / "docs"

    def get_tiles_root(self, project: str) -> Path:
        """ Return base path for tiles
        """
        h = self.get_project_hash(project)
        return self.rootdir / h.hexdigest() / "tiles"

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
        cachedir = self.rootdir / h.hexdigest()
        tiledir  = cachedir / 'tiles'

        layer = params.get('LAYER','_none')

        h.update(layer.encode())
        h.update(params.get('TILEMATRIXSET','').encode())
        h.update(params.get('STYLE','').encode())

        digest = h.hexdigest()

        x,y,z= params['TILEROW'],params['TILECOL'],params['TILEMATRIX']

        # Retrieve file suffix from FORMAT spec
        fmt = params.get('FORMAT')
        file_ext = get_image_sfx(fmt) if fmt else '.png'

        p = self._tile_location(tiledir / layer / digest, int(x), int(y), z, file_ext)

        if create_dir:
            p.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
            inf = cachedir.with_suffix('.inf')
            if not inf.exists():
                inf.write_text(project)

        return p

