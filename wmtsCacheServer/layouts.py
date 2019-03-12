""" Tiles layouts models

    From https://github.com/mapproxy/mapproxy/blob/master/mapproxy/cache/path.py
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

from typing import Union, Tuple
from pathlib import Path

layouts = {
    'tc': tile_location_tc,
    'mp': tile_location_mp,
    'tms': tile_location_tms,
    'reverse_tms': tile_location_tms
}


def tile_location_tc(root: Path, x: int, y: int, z: Union[int,str], file_ext: str) -> Path:
     try: 
       level = "%02d" % z
     except TypeError:
       pass

     parts = (
         level,
         "%03d" % int(x / 1000000),
         "%03d" % (int(x / 1000) % 1000),
         "%03d" % (int(x) % 1000),
         "%03d" % int(y / 1000000),
         "%03d" % (int(y / 1000) % 1000),
         "%03d.%s" % (int(y) % 1000, file_ext))
     )

     return root / os.path.join(*parts)


def tile_location_mp(root: Path, x: int, y: int, z: Union[int,str], file_ext: str) -> Path:
     try: 
       level = "%02d" % z
     except TypeError:
       pass

     parts = (
       level,
       "%04d" % int(x / 10000),
       "%04d" % (int(x) % 10000),
       "%04d" % int(y / 10000),
       "%04d.%s" % (int(y) % 10000, file_ext)
     )

     return root / os.path.join(*parts)

def tile_location_tms(root: Path, x: int, y: int, z: Union[int,str], file_ext: str) -> Path:
     return root / os.path.join( str(z), str(x), str(y), file_ext )


def tile_location_reverse_tms(root: Path, x: int, y: int, z: Union[int,str], file_ext: str) -> Path:
     return root / os.path.join( str(y), str(x), str(z), file_ext )

