# Cache WMTS

Plugin de cache disque de tuiles pour le service WMTS

## Paramètres d'une tuile WMTS

* LAYER (couche, groupe ou projet complet en fonction de la configuration)
* TILEMATRIXSET (le CRS)
* TILEMATRIX (le z en tms)
* TILEROW (le x en tms)
* TILE COL (le y en tms)
* FORMAT (sous la forme `image/*`)

see https://georezo.net/wiki/main/standards/wmts

## Configuration du plugin

Le plugin se configure via les variable d'environment:

### `QGIS_WMTS_CACHE_ROOTDIR`

Chemin de repertoire de base pour le cache disque.

Par défaut: *`tempfile.getmpdir()`/org.qgis.wmts/*

### `QGIS_WMTS_CACHE_LAYOUT`

Schema de stockage des tuiles en cache

Valeurs possibles: `tc`,`mp`,`tms`,`reverse_tms`

Valeur par défaut: `tc`

#### Layouts:

- `tc`: TileCache compatible layout, (`zz/xxx/xxx/xxx/yyy/yyy/yyy.format`)
- `mp`: MapProxy layout (`zz/xxxx/xxxx/yyyy/yyyy.format`), moins de niveaux de repertoire
- `tms`: TMS compatible layout (`zz/xxxx/yyyy.format`)

Le layout doit être choisi en fonction de la taille attendue du cache: plus le cache
doit être gros, plus le layout doit avoir de niveaux de repertoire.

