""" CLI for Managing  cache files
"""

import argparse
import json
import os
import sys

from pathlib import Path
from shutil import rmtree
from typing import List

from .helper import CacheHelper


def read_metadata(rootdir: Path) -> dict:
    """ Read metadata
    """
    print('Reading cache infos from %s' % rootdir, file=sys.stderr)

    metadata = rootdir / 'wmts.json'
    if not metadata.exists():
        print("Cannot read cache metadata %s" % metadata)
        sys.exit(1)

    metadata = json.loads(metadata.read_text())

    data = {}
    for c in rootdir.glob('*.inf'):
        d = c.with_suffix('')
        h = d.name

        tiledir = d / 'tiles'
        layers  = [layer.name for layer in tiledir.glob('*') if layer.is_dir()]

        data[h] = {
            'project': c.read_text(),
            'layers' : layers,
        }
    metadata.update(data=data)
    return metadata


def match_projects( glob: str, data: dict ) -> List[str]:
    """ Return a list of hash corressponding to project
    """
    if glob == '*':
        return data

    # E731 do not assign a lambda expression, use a def
    match = lambda p: p.match(glob) or p.match(glob + '.qgs') or p.name == glob or p.name == glob + '.qgs'

    return { h:v for h,v in data.items() if match(Path(v['project'])) }


def list_command( args, rootdir: Path, metadata: dict ) -> None:
    """ List cached content
    """
    data = match_projects(args.name, metadata['data'])
    if not data:
        print("No projects found for %s" % args.name, file=sys.stderr)
        return

    if args.json:
        json.dump(metadata,fp=sys.stdout,indent=2)
    else:
        print('Cache root:   ', rootdir.as_posix())
        print('Cache layout: ', metadata['layout'])
        print('Cache content:')
        data = metadata['data']
        for h,v in data.items():
            print('##')
            print('hash:  ', h)
            print('path:  ', v['project'])
            print('layers:',','.join(v['layers']))
        print('###')


def delete_command( args, rootdir: Path, metadata: dict ) -> None:
    """ Delete cached content
    """
    data = match_projects(args.name, metadata['data'])
    if not data:
        print("No projects found for %s" % args.name, file=sys.stderr)
        return

    cache = CacheHelper(rootdir, metadata['layout'])

    for h,v in data.items():
        project  = v['project']
        digest = cache.get_project_hash(project).hexdigest()

        if h != digest:
            print("Warning: Hash digest does not match: ignoring '%s'" % h, file=sys.stderr)
            continue

        cachedir = rootdir / h
        if args.layer is not None:
            tileroot = cache.get_tiles_root(project)
            cachedir = tileroot / args.layer
            if cachedir.exists():
                print("Removing layer %s" % cachedir, file=sys.stderr)
                rmtree(cachedir.as_posix())
            else:
                print("Warning: tile cache directory  %s not found" % cachedir, file=sys.stderr)
        else:
            cachedir = rootdir / h
            if cachedir.exists():
                print("Removing %s" % cachedir, file=sys.stderr)
                rmtree(cachedir.as_posix())
            else:
                print("Warning: cache directory %s not found" % cachedir, file=sys.stderr)
            # Remove medatata infos
            inf = cachedir.with_suffix('.inf')
            if inf.exists():
                inf.unlink()


def main() -> None:

    name = os.path.basename(sys.argv[0])

    rootdir = os.getenv('QGIS_WMTS_CACHE_ROOTDIR')

    parser = argparse.ArgumentParser(description='WMTS cache manager')
    parser.add_argument('--rootdir', metavar='PATH', default=rootdir, help="Cache rootdir")

    sub = parser.add_subparsers(title='commands', help="type  '%s <command> --help'" % name)
    sub.required = True
    sub.dest = 'command'

    cmd = sub.add_parser('delete'   , description="Delete cached content")
    cmd.add_argument('--layer   ', '-l', metavar='NAME', default=None, help="Tile layer name", dest='layer')
    cmd.add_argument('name'      , metavar='PATH', help="Project path - globbing allowed")
    cmd.set_defaults(func=delete_command)

    cmd = sub.add_parser('list'   , description="List cached content")
    cmd.add_argument('--json'  , action="store_true", help="Output in json format")
    cmd.add_argument('--name'  , metavar='PATH',  default='*', help="Project path - globbing allowed")
    cmd.set_defaults(func=list_command)

    args = parser.parse_args()

    rootdir = args.rootdir
    if not rootdir or not os.path.exists(rootdir):
        print('Error: no cache rootdir defined',file=sys.stderr)
        sys.exit(1)

    rootdir = Path(rootdir)

    data = read_metadata(rootdir)

    # Execute command
    args.func(args, rootdir, data)


if __name__ == "__main__":
    main()
