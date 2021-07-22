# Cache WMTS

Cache disk QGIS server plugin for WMTS tiles  

## WMTS tile parameters

* LAYER (layer, group or complete project according to project configuration)
* TILEMATRIXSET (CRS)
* TILEMATRIX (z as tms)
* TILEROW (x as tms)
* TILE COL (y as tms)
* FORMAT (Image mime type: `image/*`)

See https://georezo.net/wiki/main/standards/wmts

## Plugin configuration

The plugin is configured with environment variables:

### `QGIS_WMTS_CACHE_ROOTDIR`

Root directory for cached data

Default to: *`tempfile.getmpdir()`/org.qgis.wmts/*

### `QGIS_WMTS_CACHE_LAYOUT`

Storage layout for tiles

Possible values: `tc`,`mp`,`tms`,`reverse_tms`

Default value: `tc`

### Layouts

- `tc`: TileCache compatible layout, (`zz/xxx/xxx/xxx/yyy/yyy/yyy.format`)
- `mp`: MapProxy layout (`zz/xxxx/xxxx/yyyy/yyyy.format`), moins de niveaux de repertoire
- `tms`: TMS compatible layout (`zz/xxxx/yyyy.format`)

The layout must be chosen according to the expected size of the cache: more the cache contains
elements, more the number of directory levels must be important. 

## CLI manager Installation

A cli manager command may be installed in the python environment using standard setuptools/pip installation.

Once installed, the `wmtscache` cache command can be used to manage the cache content:

- list cache content infos
- delete project cache content
- delete specific layer cached tiles  

## WMTS Cache manager API

The WMTS Cache manager API provides these URLs:
* `/wmtscache/?`
  * to get information on the WMTS disk cache
* `/wmtscache/collections/?`
  * to get the list of collections, QGIS projects, that have WMTS disk cache
* `/wmtscache/collection/(?<collectionId>[^/]+)/?`
  * to get information on a collection, QGIS project, WMTS disk cache
  * to delete the collection, QGIS Project, WMTS disk cache
* `/wmtscache/collection/(?<collectionId>[^/]+)/docs/?`
  * to get information on a collection, QGIS project, WMTS documents disk cache
  * to delete the collection, QGIS Project, WMTS documents disk cache
* `/wmtscache/collection/(?<collectionId>[^/]+)/layers/?`
  * to get information on a collection, QGIS project, WMTS layers tiles disk cache
  * to delete the collection, QGIS Project, WMTS layers tiles disk cache
* `/wmtscache/collection/(?<collectionId>[^/]+)/layers/(?<layerid>[^/]+)/?`
  * to get information on a collection, QGIS project, WMTS layer tiles disk cache
  * to delete the collection, QGIS Project, WMTS layer tiles disk cache

To delete some cache, you have to use Delete HTTP method over the dedicated URL.
