from pathlib import Path
from datetime import date

import json
import pandas as pd
import streamlit as st

# --- Beállítások ---
DATA_FILE = Path("data/koltsegek.json")
SETTINGS_FILE = Path("data/beallitasok.json")

st.set_page_config(
    page_title="Költségkövető",
    page_icon="💰",
    layout="centered",
)


# --- Segédfüggvények az adatokhoz ---


def ensure_data_dir() -> None:
    """Létrehozza a data mappát, ha még nincs."""
    DATA_FILE.parent.mkdir(exist_ok=True)


def load_data() -> list[dict]:
    """Betölti a kiadásokat a JSON fájlból."""
    ensure_data_dir()

    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except json.JSONDecodeError:
        # Ha sérült a fájl, inkább üres listával dolgozunk
        return []


def save_data(data: list[dict]) -> None:
    """Elmenti a kiadásokat a JSON fájlba."""
    ensure_data_dir()
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_settings() -> dict:
    """Betölti a beállításokat (pl. havi keret)."""
    ensure_data_dir()

    if not SETTINGS_FILE.exists():
        return {}

    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as f:
            settings = json.load(f)
        if not isinstance(settings, dict):
            return {}
        return settings
    except json.JSONDecodeError:
        return {}


def save_settings(settings: dict) -> None:
    """Elmenti a beállításokat."""
    ensure_data_dir()
    with SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def get_dataframe(data: list[dict]) -> pd.DataFrame:
    """Lista → pandas DataFrame, dátum konvertálása."""
    if not data:
        return pd.DataFrame(columns=["datum", "kategoria", "osszeg", "megjegyzes"])

    df = pd.DataFrame(data)
    df["datum"] = pd.to_datetime(df["datum"]).dt.date
    df["osszeg"] = df["osszeg"].astype(float)
    return df


# --- UI: oldalak ---


def oldal_uj_kiadas(data: list[dict]) -> None:
    st.header("Új kiadás rögzítése")

    alap_kategoriak = [
        "Étkezés",
        "Lakhatás",
        "Közlekedés",
        "Szórakozás",
        "Egészség",
        "Bevásárlás",
        "Egyéb",
    ]

    with st.form("uj_kiadas_form"):
        col1, col2 = st.columns(2)
        with col1:
            datum = st.date_input("Dátum", value=date.today())
        with col2:
            osszeg = st.number_input("Összeg (Ft)", min_value=0.0, step=100.0)

        kategoria = st.selectbox("Kategória", alap_kategoriak)
        megjegyzes = st.text_input("Megjegyzés (opcionális)")

        submitted = st.form_submit_button("Hozzáadás")

    if submitted:
        if osszeg <= 0:
            st.error("Az összegnek nagyobbnak kell lennie 0-nál.")
            return

        uj_tetel = {
            "datum": datum.isoformat(),
            "osszeg": float(osszeg),
            "kategoria": kategoria,
            "megjegyzes": megjegyzes.strip(),
        }

        data.append(uj_tetel)
        save_data(data)

        st.success("Kiadás elmentve!")
        st.balloons()


def oldal_kiadasok_listaja(data: list[dict]) -> None:
    st.header("Kiadások listája")

    if not data:
        st.info("Még nincs rögzített kiadás.")
        return

    df = get_dataframe(data)

    # Szűrők
    st.subheader("Szűrés")

    col1, col2, col3 = st.columns(3)

    with col1:
        min_datum = df["datum"].min()
        kezdo = st.date_input("Kezdő dátum", value=min_datum)
    with col2:
        max_datum = df["datum"].max()
        veg = st.date_input("Vég dátum", value=max_datum)
    with col3:
        kategoriak = df["kategoria"].unique().tolist()
        kategoria_szuro = st.multiselect("Kategória", options=kategoriak)

    maszk = (df["datum"] >= kezdo) & (df["datum"] <= veg)
    if kategoria_szuro:
        maszk &= df["kategoria"].isin(kategoria_szuro)

    szurt = df[maszk].sort_values("datum", ascending=False)

    st.markdown("### Összegzés (szűrt adatokra)")
    osszesen = szurt["osszeg"].sum()
    st.metric("Összes kiadás", f"{osszesen:,.0f} Ft".replace(",", " "))

    st.markdown("### Részletes lista")
    st.dataframe(szurt, use_container_width=True)


def oldal_statisztika(data: list[dict], settings: dict) -> None:
    st.header("Statisztika")

    if not data:
        st.info("Még nincs rögzített kiadás, így statisztika sem.")
        return

    df = get_dataframe(data)

    # Összesítés
    st.subheader("Összesítés")

    osszesen = df["osszeg"].sum()
    atlag = df["osszeg"].mean()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Összes kiadás", f"{osszesen:,.0f} Ft".replace(",", " "))
    with col2:
        st.metric("Átlagos kiadás", f"{atlag:,.0f} Ft".replace(",", " "))

    # --- Havi keret rész ---
    st.subheader("Aktuális hónap kerete")

    today = date.today()
    # csak az aktuális hónap tételei
    df["honap"] = pd.to_datetime(df["datum"]).dt.to_period("M")
    aktualis_honap = pd.Period(today.strftime("%Y-%m"))
    df_havi = df[df["honap"] == aktualis_honap]
    havi_osszeg = df_havi["osszeg"].sum()

    havi_keret = float(settings.get("havi_keret", 0.0))

    if havi_keret > 0:
        felhasznalt_szazalek = havi_osszeg / havi_keret
        col3, col4 = st.columns(2)
        with col3:
            st.metric("Havi keret", f"{havi_keret:,.0f} Ft".replace(",", " "))
        with col4:
            st.metric(
                "Eddig elköltve ebben a hónapban",
                f"{havi_osszeg:,.0f} Ft".replace(",", " "),
            )

        st.progress(
            min(felhasznalt_szazalek, 1.0),
            text=f"{felhasznalt_szazalek*100:.1f}% felhasználva",
        )

        if havi_osszeg > havi_keret:
            st.error("Túllépted a havi keretet! 😬")
        elif havi_osszeg > havi_keret * 0.8:
            st.warning("Már több mint 80%-át elköltötted a havi keretnek.")
    else:
        st.info("Még nincs beállítva havi keret. Menj a Beállítások menüpontra.")

    # Kategória szerinti összeg
    st.subheader("Kategóriánkénti kiadás")
    by_cat = (
        df.groupby("kategoria")["osszeg"]
        .sum()
        .sort_values(ascending=False)
    )

    st.bar_chart(by_cat)

    # Havi bontás (összes hónapra)
    st.subheader("Havi összes kiadás (minden hónap)")

    by_month = df.groupby("honap")["osszeg"].sum().sort_index()
    by_month.index = by_month.index.astype(str)

    st.line_chart(by_month)


def oldal_beallitasok(settings: dict) -> dict:
    st.header("Beállítások – havi költségkeret")

    jelenlegi_keret = float(settings.get("havi_keret", 0.0))

    uj_keret = st.number_input(
        "Havi költségkeret (Ft)",
        min_value=0.0,
        step=1000.0,
        value=jelenlegi_keret,
    )

    if st.button("Keret mentése"):
        settings["havi_keret"] = float(uj_keret)
        save_settings(settings)
        st.success("Keret elmentve!")

    st.caption("A keretet az aktuális hónap kiadásaihoz hasonlítjuk a Statisztika oldalon.")

    return settings


# --- Fő program ---


def main():
    st.title("💰 Költségkövető és statisztika")

    # Adatok betöltése
    data = load_data()
    settings = load_settings()

    # Oldal választása
    oldal = st.sidebar.radio(
        "Menü",
        ("Új kiadás", "Kiadások listája", "Statisztika", "Beállítások"),
    )

    if oldal == "Új kiadás":
        oldal_uj_kiadas(data)
    elif oldal == "Kiadások listája":
        oldal_kiadasok_listaja(data)
    elif oldal == "Statisztika":
        oldal_statisztika(data, settings)
    elif oldal == "Beállítások":
        settings = oldal_beallitasok(settings)


if __name__ == "__main__":
    main()
