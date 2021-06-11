""" Tiles layouts models

    From https://github.com/mapproxy/mapproxy/blob/master/mapproxy/cache/path.py

    * `tc`: TileCache compatible layout, (`zz/xxx/xxx/xxx/yyy/yyy/yyy.format`)
    * `mp`: MapProxy layout (`zz/xxxx/xxxx/yyyy/yyyy.format`), moins de niveaux de repertoire
    * `tms`: TMS compatible layout (`zz/xxxx/yyyy.format`)
"""
# Original licence
# This file is part of the MapProxy project.
# Copyright (C) 2010-2016 Omniscale <http://omniscale.de>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from typing import Union
from pathlib import Path


def tile_location_tc(root: Path, x: int, y: int, z: Union[int,str], file_ext: str) -> Path:
    """ TileCache compatible layout

        scheme: zz/xxx/xxx/xxx/yyy/yyy/yyy.format
    """
    try:
      level = "%02d" % int(z)
    except ValueError:
      level = z

    parts = (
        level,
        "%03d" % (x // 1000000),
        "%03d" % ((x / 1000) % 1000),
        "%03d" % ((x) % 1000),
        "%03d" % (y // 1000000),
        "%03d" % ((y // 1000) % 1000),
        "%03d" % (y % 1000)
    )

    return (root / os.path.join(*parts)).with_suffix(file_ext)


def tile_location_mp(root: Path, x: int, y: int, z: Union[int,str], file_ext: str) -> Path:
    """ MapProxy layout

        scheme: zz/xxxx/xxxx/yyyy/yyyy.format
    """
    try:
      level = "%02d" % int(z)
    except ValueError:
      level = z

    parts = (
        level,
        "%04d" % (x // 10000),
        "%04d" % ((x) % 10000),
        "%04d" % (y // 10000),
        "%04d" % (y % 10000)
    )

    return (root / os.path.join(*parts)).with_suffix(file_ext)


def tile_location_tms(root: Path, x: int, y: int, z: Union[int,str], file_ext: str) -> Path:
    """ TMS compatible layout

        schema: z/x/y.format
    """
    return (root / os.path.join( str(z), str(x), str(y))).with_suffix(file_ext)


def tile_location_reverse_tms(root: Path, x: int, y: int, z: Union[int,str], file_ext: str) -> Path:
    """ Same as TMS but reversed

        schema: x/y/z.format
    """
    return (root / os.path.join( str(y), str(x), str(z))).with_suffix(file_ext)


layouts = {
    'tc': tile_location_tc,
    'mp': tile_location_mp,
    'tms': tile_location_tms,
    'reverse_tms': tile_location_tms
}
