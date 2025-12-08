# Költségkövető és statisztika (Streamlit)

Ez a projekt egy egyszerű költségkövető és statisztika alkalmazás Python nyelven, Streamlit felhasználásával.  
A cél a kiadások és bevételek rögzítése, áttekintése, elemzése, valamint egy havi költségkeret követése.

## Fő funkciók

- **Kiadások és bevételek rögzítése** űrlapon keresztül.
- Minden tételhez megadható:
  - dátum
  - összeg
  - kategória
  - megjegyzés
  - típus (kiadás / bevétel)
- **Adatok listázása** táblázatos nézetben.
- **Szűrés**:
  - típus szerint
  - dátumtartomány szerint
  - kategória szerint
- **Tétel módosítása és törlése** kiválasztás után.
- **Statisztikák**:
  - összes kiadás
  - összes bevétel
  - egyenleg
  - kategóriánkénti kiadások
  - havi trendek
- **Havi költségkeret** beállítása és követése:
  - figyelmeztetés 80% felett
  - jelzés túllépés esetén
- **Kezdőlap / Dashboard**:
  - aktuális havi összefoglaló
  - top 3 kiadási kategória
  - legutóbbi tételek
- **CSV export** Excel-kompatibilis formában.

## Használt technológiák és csomagok

### Külső Python csomagok
- **streamlit** – a felhasználói felület és az alkalmazás futtatása.
- **pandas** – adatok táblázatos kezelése, csoportosítás és statisztikák.

### Standard könyvtár (beépített)
- **json** – adatok mentése/olvasása fájlból.
- **pathlib** – fájlútvonalak kezelése.
- **datetime** – dátumok kezelése.

## Fontosabb megoldások

- **Fájl alapú tárolás (JSON)**  
  Az adatok a `data/koltsegek.json` fájlba mentődnek, így az alkalmazás újraindítás után is megőrzi őket.

- **Beállítások tárolása**  
  A havi keret külön fájlban van elmentve: `data/beallitasok.json`.

- **Visszamenőleges kompatibilitás**  
  Ha régebbi tételekben nincs `tipus` mező, a program automatikusan `kiadas`-ként kezeli őket.

- **Excel-barát CSV export**  
  Az export **UTF-8 BOM-mal** készül (`utf-8-sig`), hogy az ékezetek helyesen jelenjenek meg Excelben.

- **Automatikus frissítés szerkesztés/törlés után**  
  Mentés és törlés után `st.rerun()` fut, így nem szükséges kézzel újratölteni az oldalt.


## Telepítés

### Ajánlott Python verzió
- **Python 3.11.x**

### Virtuális környezet létrehozása

''' bash 
python -m venv venv

Aktiválás: 
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate

Csomagok telepítése
pip install streamlit pandas

Futtatás
python -m streamlit run app.py

