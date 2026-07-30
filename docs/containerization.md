# A projekt konténerizálása Docker Compose használatával

A projekt GitHub-helye: `operator40/digital_twin_simple`. Klónozás után minden
parancsot a repository gyökérkönyvtárában kell futtatni:

```powershell
git clone https://github.com/operator40/digital_twin_simple.git
Set-Location digital_twin_simple
```

## 1. A legfontosabb fogalmak

### Image

Az image egy csak olvasható alkalmazáscsomag. Tartalmazza a Linux alaprendszert,
a Python futtatókörnyezetet, a telepített csomagokat és az alkalmazás kódját.
A projekt image-ét a `Dockerfile` alapján építjük fel.

### Container

A container egy image futó példánya. Ugyanabból az alkalmazás-image-ből két
containert indítunk:

- az `api` Uvicornt futtat;
- a `worker` a queue feldolgozóját futtatja.

### Volume

A container írható fájlrendszere nem alkalmas tartós adatok tárolására. Ha a
containert töröljük, ez az adat elveszhet. A named volume ettől függetlenül él.

- `postgres_data`: az adatbázis tényleges fájljai;
- `prediction_data`: a predikciós fájlkimenetek számára fenntartott könyvtár.

### Docker network és szolgáltatásnév

Compose automatikusan létrehoz egy belső hálózatot. Ezen belül a szolgáltatások
a Compose-ban megadott nevükkel találják meg egymást. Emiatt az alkalmazásból az
adatbázis hostneve `db`, nem `localhost`.

Egy containerben a `localhost` mindig ugyanazt a containert jelenti. Ez az egyik
leggyakoribb kezdő Docker-hiba.

## 2. A szolgáltatások

```text
Felhasználó -> localhost:8000 -> api
                                  |
                                  v
                               db:5432
                                  ^
                                  |
                               worker -> CMMS
```

Az `api` csak sorba állítja a kérést a `prediction_jobs` táblában. A `worker`
ugyanebből az adatbázisból veszi fel és dolgozza fel a feladatot.

A TimescaleDB container az üres volume első inicializálásakor lefuttatja a
`db/init/001_schema.sql` fájlt. Ez hozza létre a `public` séma tábláit, kulcsait,
indexét, enumját és hypertable-jait. A `db-init` ezután rövid életű ellenőrző
containerként igazolja, hogy a teljes séma elkészült. Az API és a worker csak
sikeres ellenőrzés után indul el.

## 3. Docker Desktop telepítése Windowsra

1. Ellenőrizd a WSL verzióját PowerShellben:

   ```powershell
   wsl --version
   ```

2. Ha a WSL hiányzik vagy régi, rendszergazdai PowerShellben:

   ```powershell
   wsl --install
   wsl --update
   ```

3. Telepítsd a Docker Desktopot a WSL 2 backenddel, majd indítsd el.
4. Nyiss új PowerShell-ablakot, és ellenőrizd:

   ```powershell
   docker version
   docker compose version
   ```

Nem elég, ha csak a kliens verziója jelenik meg: a `docker version` kimenetében
a Client és Server szakasznak is szerepelnie kell. A Server a Docker Engine.

## 4. A konfiguráció létrehozása

A `.env.example` dokumentálja a szükséges változókat, de nem tartalmaz valódi
titkokat. Másold `.env` néven:

```powershell
Copy-Item .env.example .env
```

Ezután szerkeszd a `.env` fájlt. Legalább ezeket cseréld le:

- `POSTGRES_PASSWORD`;
- `INBOUND_API_KEY`;
- `CMMS_BASE_URL`;
- `CMMS_TOKEN`.

Az alapértelmezett adatbázisnév `dt_db_cmms`, a felhasználó `dt_admin`. A
`POSTGRES_PORT` a Windows hoston megnyitott port; a containerek egymás között
mindig a `db:5432` címet használják. Ha a host 5432-es portja foglalt, például:

```dotenv
POSTGRES_PORT=5433
```

A `.env` szerepel a `.gitignore` és `.dockerignore` fájlokban, ezért nem kerül
Gitbe és az alkalmazás-image-be. Ettől még biztonsági mentésben vagy kézi
megosztáskor ugyanúgy titokként kell kezelni.

## 5. Az image felépítése

```powershell
docker compose build
```

A Docker rétegenként hajtja végre a `Dockerfile` utasításait. A requirements
hamarabb kerül bemásolásra, mint a forráskód, így egy Python-fájl módosítása után
nem kell minden csomagot újratelepíteni: Docker felhasználhatja a korábbi cache-t.

Az image nem root felhasználóként fut. Ez csökkenti egy alkalmazáshiba hatását,
és jó alapértelmezés éles telepítéshez is.

## 6. Az első indítás

```powershell
docker compose up --build
```

Az előtérben látod az összes szolgáltatás naplóját. Az első alkalommal a folyamat:

1. a PostgreSQL 16-ot tartalmazó TimescaleDB image letöltése;
2. az alkalmazás-image felépítése;
3. a `postgres_data` és `prediction_data` volume létrehozása;
4. az adatbázis inicializálása;
5. a PostgreSQL healthcheck sikeressé válása;
6. a TimescaleDB entrypoint lefuttatja a séma SQL-t;
7. a `db-init` ellenőrzi a táblákat, hypertable-öket és az extensiont;
8. elindul az API és a worker.

Háttérben való indításhoz:

```powershell
docker compose up --build -d
```

Ha a CMMS még nem érhető el, csak az adatbázist, a sémaellenőrzést és az API-t
indítsd el:

```powershell
docker compose up --build -d db db-init api
```

Az API ettől elérhető és képes jobokat sorba állítani. A queued jobokat azonban
csak működő CMMS-kapcsolattal érdemes feldolgoztatni. A worker később külön
indítható:

```powershell
docker compose up -d worker
```

## 7. Ellenőrzés

Szolgáltatások állapota:

```powershell
docker compose ps
```

Naplók:

```powershell
docker compose logs -f
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f db-init
```

FastAPI dokumentáció:

```text
http://localhost:8000/docs
```

Adatbázistáblák listázása:

```powershell
docker compose exec db psql -U dt_admin -d dt_db_cmms -c "\dt"
```

Az első valódi API-kérés előtt az adatbázisnak üzleti törzsadatokra, például
asset rekordokra is szüksége lehet. Az inicializáló SQL a szerkezetet hozza
létre, de üzleti adatokat nem talál ki és nem tölt be.

A `db-init` sikeres futás után `Exited (0)` állapotú. Ez nem hiba: rövid életű
ellenőrző szolgáltatás, nem folyamatosan futó container.

### Időbélyegek

Az üzleti időpontokat az adatbázis `TIMESTAMP WITHOUT TIME ZONE` mezőkben tárolja.
Ha a CMMS időzóna nélkül küldi az időt, az alkalmazás azt változtatás nélkül
írja be; nem tesz hozzá UTC-jelölést és nem végez időzóna-konverziót. A két
rendszernek ezért dokumentáltan meg kell állapodnia abban, hogy a kapott időpont
például Europe/Budapest helyi időt jelent-e.

## 8. Leállítás és adattörlés

Containerek leállítása és eltávolítása, az adatok megtartásával:

```powershell
docker compose down
```

Leállítás a volume-ok törlésével:

```powershell
docker compose down --volumes
```

A második parancs törli a lokális adatbázist és a predikciós fájlokat. Csak akkor
használd, ha valóban tiszta újrakezdést szeretnél és nincs szükség az adatokra.

## 9. Gyakori hibák

### `docker` parancs nem található

A Docker Desktop nincs telepítve, nem fut, vagy a telepítés óta nem nyitottál új
terminált.

### Az alkalmazás `localhost:5432` címen keresi az adatbázist

Containerből az adatbázis hostneve `db`. A Compose által átadott URL ezt már
helyesen tartalmazza.

### A port már foglalt

Módosítsd a `.env` fájlban az `API_PORT` vagy `POSTGRES_PORT` értékét. A jobb
oldali container-portot nem kell megváltoztatni.

### Megváltoztattam a PostgreSQL jelszót, de nem lépett életbe

A PostgreSQL-alapú TimescaleDB image a `POSTGRES_*` változókat csak az üres adatkönyvtár
első inicializálásakor használja. Meglévő volume esetén módosítsd a jelszót SQL-lel,
vagy fejlesztői adatoknál töröld a volume-ot és inicializáld újra.

### Módosítottam a séma SQL-t, de az adatbázis nem változott meg

A `/docker-entrypoint-initdb.d` fájljai csak teljesen üres PostgreSQL volume
első inicializálásakor futnak. Fejlesztői adatoknál újra létrehozhatod a volume-ot;
megőrzendő adatok esetén verziózott migrációt kell írni. Ahogy a projekt fejlődik,
érdemes Alembic migrációkra váltani, mert azok kontrolláltan módosítják a már
létező adatbázist.

## 10. Biztonsági mentés

A PostgreSQL custom formátuma tömörített, bináris mentést készít, amelyet a
`pg_restore` szelektíven és megbízhatóan tud visszaállítani. PowerShellben a
bináris kimenetet ne irányítsd egyszerű `>` operátorral fájlba, mert a különböző
PowerShell-verziók eltérően kezelhetik a bájtfolyamot. Készítsd el először a
containerben, majd másold ki:

```powershell
New-Item -ItemType Directory -Force backups
docker compose exec db pg_dump -U dt_admin -d dt_db_cmms -Fc -f /tmp/dt_db_cmms.dump
docker compose cp db:/tmp/dt_db_cmms.dump ./backups/dt_db_cmms.dump
```

A mentés tartalmának ellenőrzése visszaállítás nélkül:

```powershell
docker compose cp ./backups/dt_db_cmms.dump db:/tmp/verify.dump
docker compose exec db pg_restore --list /tmp/verify.dump
```

Visszaállítás előtt állítsd le az API-t és a workert, hogy ne írjanak közben.
Éles adatoknál a visszaállítást először külön tesztadatbázisban próbáld ki:

```powershell
docker compose stop api worker
docker compose exec db createdb -U dt_admin -T template0 dt_db_cmms_restore_test
docker compose cp ./backups/dt_db_cmms.dump db:/tmp/restore.dump
docker compose exec db psql -U dt_admin -d dt_db_cmms_restore_test -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
docker compose exec db psql -U dt_admin -d dt_db_cmms_restore_test -c "SELECT timescaledb_pre_restore();"
docker compose exec db pg_restore -U dt_admin -d dt_db_cmms_restore_test -Fc /tmp/restore.dump
docker compose exec db psql -U dt_admin -d dt_db_cmms_restore_test -c "SELECT timescaledb_post_restore();"
docker compose exec db psql -U dt_admin -d dt_db_cmms_restore_test -c "ANALYZE;"
docker compose start api
```

A teszt-visszaállítás ellenőrzése:

```powershell
docker compose exec db psql -U dt_admin -d dt_db_cmms_restore_test -c "SELECT count(*) AS public_tables FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
docker compose exec db psql -U dt_admin -d dt_db_cmms_restore_test -c "SELECT hypertable_name FROM timescaledb_information.hypertables WHERE hypertable_schema='public' ORDER BY hypertable_name;"
docker compose exec db psql -U dt_admin -d dt_db_cmms_restore_test -c "SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_type.oid=pg_enum.enumtypid WHERE pg_type.typname='jobstatus' ORDER BY enumsortorder;"
```

Az aktuális séma esetén 18 public tábla, 4 hypertable, valamint a `queued`,
`processing`, `done`, `not_found`, `error` enumértékek az elvárt eredmények.
A tesztadatbázis csak sikeres ellenőrzés után törölhető:

```powershell
docker compose exec db dropdb -U dt_admin dt_db_cmms_restore_test
```

Ne add a `-j` kapcsolót a `pg_restore` parancshoz: a párhuzamos visszaállítás
nem kezeli helyesen a TimescaleDB belső katalógusait. Ha a restore a
`timescaledb_pre_restore()` után megszakad, a céladatbázison akkor is futtasd le
a `timescaledb_post_restore()` függvényt, mielőtt használni kezded vagy újra
próbálkozol.

Éles rendszerben a mentést automatizálni, titkosítani és rendszeresen visszaállítási
próbával ellenőrizni kell. A nem tesztelt backup csak feltételezett backup.
