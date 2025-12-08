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


# --- Adatkezelés ---


def ensure_data_dir() -> None:
    DATA_FILE.parent.mkdir(exist_ok=True)


def load_data() -> list[dict]:
    """Betölti a tételeket (kiadás + bevétel)."""
    ensure_data_dir()
    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []

        # Régi rekordok kompatibilitása: ha nincs 'tipus', tekintsük kiadásnak
        for t in data:
            if "tipus" not in t:
                t["tipus"] = "kiadas"
        return data
    except json.JSONDecodeError:
        return []


def save_data(data: list[dict]) -> None:
    ensure_data_dir()
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_settings() -> dict:
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
    ensure_data_dir()
    with SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def get_dataframe(data: list[dict]) -> pd.DataFrame:
    """Lista → DataFrame, dátum + típus rendezése."""
    if not data:
        return pd.DataFrame(
            columns=["datum", "tipus", "kategoria", "osszeg", "megjegyzes"]
        )

    df = pd.DataFrame(data)
    df["datum"] = pd.to_datetime(df["datum"]).dt.date
    df["osszeg"] = df["osszeg"].astype(float)
    if "tipus" not in df.columns:
        df["tipus"] = "kiadas"
    return df


# --- UI oldalak ---


def oldal_dashboard(data: list[dict], settings: dict) -> None:
    st.header("Kezdőlap – áttekintés")

    if not data:
        st.info("Még nincs rögzített tétel. Kezdd az 'Új tétel' menüpontnál.")
        return

    df = get_dataframe(data).copy()
    df["honap"] = pd.to_datetime(df["datum"]).dt.to_period("M")

    today = date.today()
    aktualis_honap = pd.Period(today.strftime("%Y-%m"))
    df_akt = df[df["honap"] == aktualis_honap]

    havi_kiadas = df_akt.loc[df_akt["tipus"] == "kiadas", "osszeg"].sum()
    havi_bevetel = df_akt.loc[df_akt["tipus"] == "bevetel", "osszeg"].sum()
    havi_egyenleg = havi_bevetel - havi_kiadas

    havi_keret = float(settings.get("havi_keret", 0.0))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Aktuális havi kiadás", f"{havi_kiadas:,.0f} Ft".replace(",", " "))
    with col2:
        st.metric("Aktuális havi bevétel", f"{havi_bevetel:,.0f} Ft".replace(",", " "))
    with col3:
        st.metric("Havi egyenleg", f"{havi_egyenleg:,.0f} Ft".replace(",", " "))

    st.divider()

    st.subheader("Keret állapota (kiadásokra)")
    if havi_keret > 0:
        felhasznalt_szazalek = havi_kiadas / havi_keret

        col4, col5 = st.columns(2)
        with col4:
            st.metric("Havi keret", f"{havi_keret:,.0f} Ft".replace(",", " "))
        with col5:
            maradek = max(havi_keret - havi_kiadas, 0)
            st.metric("Maradék keret", f"{maradek:,.0f} Ft".replace(",", " "))

        st.progress(
            min(felhasznalt_szazalek, 1.0),
            text=f"{felhasznalt_szazalek*100:.1f}% felhasználva",
        )

        if havi_kiadas > havi_keret:
            st.error("Túllépted a havi keretet!")
        elif havi_kiadas > havi_keret * 0.8:
            st.warning("Már több mint 80%-át elköltötted a havi keretnek.")
    else:
        st.info("Nincs beállítva havi keret. Állítsd be a Beállításokban.")

    st.divider()

    st.subheader("Top 3 kiadási kategória (aktuális hónap)")
    top = (
        df_akt[df_akt["tipus"] == "kiadas"]
        .groupby("kategoria")["osszeg"]
        .sum()
        .sort_values(ascending=False)
        .head(3)
    )

    if top.empty:
        st.info("Ebben a hónapban még nincs kiadás.")
    else:
        st.bar_chart(top)

    st.subheader("Legutóbbi 5 tétel")
    df_recent = df.sort_values("datum", ascending=False).head(5).copy()
    df_recent["tipus"] = df_recent["tipus"].map(
        {"kiadas": "Kiadás", "bevetel": "Bevétel"}
    )
    st.dataframe(
        df_recent[["datum", "tipus", "kategoria", "osszeg", "megjegyzes"]],
        use_container_width=True,
    )


def oldal_uj_tetel(data: list[dict]) -> None:
    st.header("Új tétel rögzítése")

    # Kiadás / Bevétel választás
    tipus = st.radio("Típus", ["Kiadás", "Bevétel"], horizontal=True)
    tipus_kod = "kiadas" if tipus == "Kiadás" else "bevetel"

    alap_kategoriak_kiadas = [
        "Étkezés",
        "Lakhatás",
        "Közlekedés",
        "Szórakozás",
        "Egészség",
        "Bevásárlás",
        "Egyéb",
    ]
    alap_kategoriak_bevetel = [
        "Fizetés",
        "Ösztöndíj",
        "Ajándék",
        "Egyéb bevétel",
    ]
    alap_kategoriak = (
        alap_kategoriak_kiadas if tipus_kod == "kiadas" else alap_kategoriak_bevetel
    )

    with st.form("uj_tetel_form"):
        col1, col2 = st.columns(2)
        with col1:
            datum = st.date_input("Dátum", value=date.today())
        with col2:
            osszeg = st.number_input("Összeg (Ft)", min_value=0.0, step=1000.0)

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
            "tipus": tipus_kod,
        }

        data.append(uj_tetel)
        save_data(data)

        st.success("Tétel elmentve!")
        st.balloons()


def oldal_tetelek_listaja(data: list[dict]) -> None:
    st.header("Tételek listája")

    if not data:
        st.info("Még nincs rögzített tétel.")
        return

    # DataFrame + egy "id" oszlop, ami a lista indexe
    df = get_dataframe(data).copy()
    df["id"] = df.index

    # --- Szűrők ---
    st.subheader("Szűrés")

    col0, col1, col2, col3 = st.columns(4)
    with col0:
        tipus_szuro = st.multiselect(
            "Típus",
            options=["kiadas", "bevetel"],
            default=["kiadas", "bevetel"],
            format_func=lambda x: "Kiadás" if x == "kiadas" else "Bevétel",
        )
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
    if tipus_szuro:
        maszk &= df["tipus"].isin(tipus_szuro)
    if kategoria_szuro:
        maszk &= df["kategoria"].isin(kategoria_szuro)

    szurt = df[maszk].sort_values("datum", ascending=False)

    # --- Összegzés a szűrt adatokra ---
    st.markdown("### Összegzés (szűrt adatokra)")
    kiadasok = szurt.loc[szurt["tipus"] == "kiadas", "osszeg"].sum()
    bevetel = szurt.loc[szurt["tipus"] == "bevetel", "osszeg"].sum()
    egyenleg = bevetel - kiadasok

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Kiadások", f"{kiadasok:,.0f} Ft".replace(",", " "))
    with col_b:
        st.metric("Bevételek", f"{bevetel:,.0f} Ft".replace(",", " "))
    with col_c:
        st.metric("Egyenleg", f"{egyenleg:,.0f} Ft".replace(",", " "))

    # --- Lista táblázatban ---
    st.markdown("### Részletes lista")
    df_megj = szurt.copy()
    df_megj["tipus"] = df_megj["tipus"].map(
        {"kiadas": "Kiadás", "bevetel": "Bevétel"}
    )
    st.dataframe(df_megj.drop(columns=["id"]), use_container_width=True)

    # --- Szerkesztés / törlés szekció ---
    st.markdown("### Tétel módosítása vagy törlése")

    if szurt.empty:
        st.info("A szűrők alapján nincs megjeleníthető tétel.")
        return

    # Legördülő lista a tételekhez (id + rövid leírás)
    id_to_label = {}
    for _, row in szurt.iterrows():
        label_tipus = "Kiadás" if row["tipus"] == "kiadas" else "Bevétel"
        label = (
            f'#{int(row["id"])} | {label_tipus} | '
            f'{row["datum"]} | {row["kategoria"]} | {row["osszeg"]:.0f} Ft'
        )
        id_to_label[int(row["id"])] = label

    selected_id = st.selectbox(
        "Tétel kiválasztása",
        options=list(id_to_label.keys()),
        format_func=lambda x: id_to_label[x],
    )

    selected_row = szurt[szurt["id"] == selected_id].iloc[0]

    col_left, col_right = st.columns(2)

    # --- Módosítás bal oldalon ---
    with col_left:
        st.subheader("Módosítás")

        alap_kategoriak_kiadas = [
            "Étkezés",
            "Lakhatás",
            "Közlekedés",
            "Szórakozás",
            "Egészség",
            "Bevásárlás",
            "Egyéb",
        ]
        alap_kategoriak_bevetel = [
            "Fizetés",
            "Ösztöndíj",
            "Ajándék",
            "Egyéb bevétel",
        ]

        tipus_index = 0 if selected_row["tipus"] == "kiadas" else 1

        with st.form("edit_form"):
            tipus_valaszto = st.radio(
                "Típus",
                ["Kiadás", "Bevétel"],
                index=tipus_index,
                horizontal=True,
            )
            tipus_kod = "kiadas" if tipus_valaszto == "Kiadás" else "bevetel"

            if tipus_kod == "kiadas":
                kategoriak_val = alap_kategoriak_kiadas.copy()
            else:
                kategoriak_val = alap_kategoriak_bevetel.copy()

            if selected_row["kategoria"] not in kategoriak_val:
                kategoriak_val.append(selected_row["kategoria"])

            datum_uj = st.date_input("Dátum", value=selected_row["datum"])
            osszeg_uj = st.number_input(
                "Összeg (Ft)",
                min_value=0.0,
                step=1000.0,
                value=float(selected_row["osszeg"]),
            )
            kategoria_uj = st.selectbox(
                "Kategória",
                options=kategoriak_val,
                index=kategoriak_val.index(selected_row["kategoria"]),
            )
            megjegyzes_uj = st.text_input(
                "Megjegyzés",
                value=selected_row.get("megjegyzes", ""),
            )

            ment = st.form_submit_button("Változtatások mentése")

        if ment:
            if osszeg_uj <= 0:
                st.error("Az összegnek nagyobbnak kell lennie 0-nál.")
            else:
                data[selected_id]["datum"] = datum_uj.isoformat()
                data[selected_id]["osszeg"] = float(osszeg_uj)
                data[selected_id]["kategoria"] = kategoria_uj
                data[selected_id]["megjegyzes"] = megjegyzes_uj.strip()
                data[selected_id]["tipus"] = tipus_kod
                save_data(data)
                st.success("Tétel módosítva.")
                st.rerun()

    # --- Törlés jobb oldalon ---
    with col_right:
        st.subheader("Törlés")
        if st.button("Kiválasztott tétel törlése"):
            data.pop(selected_id)
            save_data(data)
            st.success("Tétel törölve.")
            st.rerun()


def oldal_statisztika(data: list[dict], settings: dict) -> None:
    st.header("Statisztika")

    if not data:
        st.info("Még nincs rögzített tétel, így statisztika sem.")
        return

    df = get_dataframe(data)

    # Összesített számok
    st.subheader("Összesítés")

    kiadasok = df.loc[df["tipus"] == "kiadas", "osszeg"].sum()
    bevetel = df.loc[df["tipus"] == "bevetel", "osszeg"].sum()
    egyenleg = bevetel - kiadasok

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Összes kiadás", f"{kiadasok:,.0f} Ft".replace(",", " "))
    with col2:
        st.metric("Összes bevétel", f"{bevetel:,.0f} Ft".replace(",", " "))
    with col3:
        st.metric("Egyenleg", f"{egyenleg:,.0f} Ft".replace(",", " "))

    # Havi keret – csak kiadásokra
    st.subheader("Aktuális hónap kerete (kiadásokra)")

    today = date.today()
    df["honap"] = pd.to_datetime(df["datum"]).dt.to_period("M")
    aktualis_honap = pd.Period(today.strftime("%Y-%m"))
    df_havi_kiadas = df[(df["honap"] == aktualis_honap) & (df["tipus"] == "kiadas")]
    havi_kiadas = df_havi_kiadas["osszeg"].sum()

    havi_keret = float(settings.get("havi_keret", 0.0))

    if havi_keret > 0:
        felhasznalt_szazalek = havi_kiadas / havi_keret if havi_keret > 0 else 0
        col3a, col3b = st.columns(2)
        with col3a:
            st.metric("Havi keret", f"{havi_keret:,.0f} Ft".replace(",", " "))
        with col3b:
            st.metric(
                "Eddig elköltve ebben a hónapban",
                f"{havi_kiadas:,.0f} Ft".replace(",", " "),
            )

        st.progress(
            min(felhasznalt_szazalek, 1.0),
            text=f"{felhasznalt_szazalek*100:.1f}% felhasználva",
        )

        if havi_kiadas > havi_keret:
            st.error("Túllépted a havi keretet! 😬")
        elif havi_kiadas > havi_keret * 0.8:
            st.warning("Már több mint 80%-át elköltötted a havi keretnek.")
    else:
        st.info("Még nincs beállítva havi keret. Menj a Beállítások menüpontra.")

    # Kategóriánkénti kiadások
    st.subheader("Kategóriánkénti kiadások")
    by_cat_kiadas = (
        df[df["tipus"] == "kiadas"]
        .groupby("kategoria")["osszeg"]
        .sum()
        .sort_values(ascending=False)
    )
    if not by_cat_kiadas.empty:
        st.bar_chart(by_cat_kiadas)
    else:
        st.info("Még nincs kiadás, amit meg tudnánk jeleníteni kategóriánként.")

    # Havi egyenleg grafikon
    st.subheader("Havi egyenleg (bevétel - kiadás)")

    by_month = (
        df.groupby(["honap", "tipus"])["osszeg"]
        .sum()
        .unstack(fill_value=0)
        .rename(columns={"kiadas": "Kiadás", "bevetel": "Bevétel"})
    )
    by_month["Egyenleg"] = by_month.get("Bevétel", 0) - by_month.get("Kiadás", 0)
    by_month.index = by_month.index.astype(str)

    st.line_chart(by_month[["Kiadás", "Bevétel", "Egyenleg"]])


def oldal_beallitasok(settings: dict) -> dict:
    st.header("Beállítások – havi költségkeret")

    jelenlegi_keret = float(settings.get("havi_keret", 0.0))

    uj_keret = st.number_input(
        "Havi költségkeret (Ft) – csak kiadásokra",
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


def oldal_export(data: list[dict]) -> None:
    st.header("Adatok exportálása (CSV)")

    if not data:
        st.info("Még nincs exportálható adat.")
        return

    df = get_dataframe(data)

    st.markdown("### Összes tétel exportálása")

    # String → UTF-8 BOM-os byte-tömb, hogy az Excel helyesen kezelje az ékezeteket
    csv_all = df.to_csv(index=False, sep=";")
    csv_bytes = csv_all.encode("utf-8-sig")

    st.download_button(
        label="Összes tétel exportálása (CSV)",
        data=csv_bytes,
        file_name="koltsegkoveto_osszes.csv",
        mime="text/csv; charset=utf-8",
    )

    st.markdown("### Előnézet (utolsó 20 tétel)")
    st.dataframe(df.tail(20), use_container_width=True)


# --- Főprogram ---


def main():
    st.title("💰 Költségkövető és statisztika – bevételekkel")

    data = load_data()
    settings = load_settings()

    oldal = st.sidebar.radio(
        "Menü",
        ("Kezdőlap", "Új tétel", "Tételek listája", "Statisztika", "Beállítások", "Exportálás"),
    )

    if oldal == "Kezdőlap":
        oldal_dashboard(data, settings)
    elif oldal == "Új tétel":
        oldal_uj_tetel(data)
    elif oldal == "Tételek listája":
        oldal_tetelek_listaja(data)
    elif oldal == "Statisztika":
        oldal_statisztika(data, settings)
    elif oldal == "Beállítások":
        oldal_beallitasok(settings)
    elif oldal == "Exportálás":
        oldal_export(data)


if __name__ == "__main__":
    main()
