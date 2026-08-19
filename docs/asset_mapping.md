# CMMS–DC asset mapping

A rendszer saját eszközazonosítója az `assets.asset_id`. A CMMS és a
SilverFrog DC külső azonosítói ugyanazon a rekordon, külön mezőben szerepelnek:

```text
assets.cmms_asset_id  <- CMMS asset_id
assets.dc_asset_id    <- DC technicalObjectUniqueIdentifier
```

A `dc_asset_id` és a `sensors.metric_function_id` szöveges értékek. A
datacollector csak olyan DC technical object metaadatait és méréseit menti,
amelyhez már létezik mapping. Ismeretlen DC-azonosítóból nem hoz létre assetet.

## Mapping API

A mappingek a futó API-n keresztül, újraindítás nélkül tölthetők be:

```text
POST /sf_asset_mapping
X-API-Key: <MAPPING_ADMIN_API_KEY>
```

Példakérés:

```json
{
  "mappings": [
    {
      "cmms_asset_id": 1875,
      "dc_asset_id": "TECH-00981"
    },
    {
      "cmms_asset_id": 1876
    },
    {
      "dc_asset_id": "TECH-00982"
    }
  ]
}
```

Egy elemben elegendő csak a `cmms_asset_id` vagy csak a `dc_asset_id` mezőt
megadni. Mindkettő megadása összekapcsolja a két külső azonosítót. Ha az egyik
azonosító már létezik, és a másik mezője még üres, a végpont a meglévő assetet
frissíti. Legalább az egyik azonosító kötelező.

Az eredmény minden párhoz `created`, `updated`, `unchanged` vagy `conflict`
állapotot ad. Meglévő azonosítót a végpont nem rendel át automatikusan másik
assethez. Új mapping után a datacollector a következő ciklusban frissíti a DC
metrikák metaadatait.

## Importálás JSON-fájlból

A `scripts/import_asset_mappings.py` közvetlen listát és `mappings` mezőbe
csomagolt listát is elfogad. A projekt gyökerében létrehozott
`asset_mappings.json` a csomagolt formátumot használja. Kitöltési példa:

```json
{
  "mappings": [
    {
      "cmms_asset_id": 1875,
      "dc_asset_id": "TECH-00981"
    },
    {
      "cmms_asset_id": 1876
    },
    {
      "dc_asset_id": "TECH-00982"
    }
  ]
}
```

Linuxon:

```bash
export MAPPING_ADMIN_API_KEY='replace-me'
python scripts/import_asset_mappings.py asset_mappings.json
```

Eltérő API-cím esetén:

```bash
python scripts/import_asset_mappings.py asset_mappings.json \
  --url http://digital-twin-host:8000/sf_asset_mapping
```

## Meglévő adatbázis

Induláskor a `db-init` átnevezi a korábbi `assets.sf_asset_id` oszlopot
`cmms_asset_id` névre, létrehozza a `dc_asset_id` oszlopot, valamint szövegesre
alakítja a `sensors.metric_function_id` mezőt.

Telepítés előtt ellenőrizni kell, hogy a korábbi `sf_asset_id` értékek valóban
CMMS-azonosítók. Ha a régi datacollector már hozott létre asseteket DC-azonosító
alapján, azokhoz tartozó szenzorokat és méréseket kézzel kell a helyes belső
`asset_id` rekordhoz migrálni; ezt nem lehet a két külső azonosító ismerete
nélkül biztonságosan automatizálni.
