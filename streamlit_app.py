import requests
import pandas as pd
import streamlit as st
import io
import os

BASE_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"


# ── Hjelpefunksjoner ──────────────────────────────────────

@st.cache_data
def hent_kommunenummer(kommunenavn: str) -> str | None:
    """Slår opp kommunenummer fra Brreg. Resultatet caches så det ikke hentes på nytt."""
    side = 0
    while True:
        url = f"https://data.brreg.no/enhetsregisteret/api/kommuner?page={side}&size=100"
        r = requests.get(url, headers={"Accept": "application/json"})

        if r.status_code != 200:
            return None

        data = r.json()
        kommuner = data.get("_embedded", {}).get("kommuner", [])

        for k in kommuner:
            if k.get("navn", "").upper() == kommunenavn.upper():
                return k.get("nummer")

        total_sider = data.get("page", {}).get("totalPages", 1)
        side += 1
        if side >= total_sider:
            break

    return None


def sok_alle_sider(naeringskode: str, kommunenr: str):
    """Henter alle sider med resultater fra Brreg."""
    alle_enheter = []
    totalt = 0
    side = 0

    while True:
        params = {
            "naeringskode":  naeringskode,
            "kommunenummer": kommunenr,
            "size":          100,
            "page":          side
        }
        r = requests.get(BASE_URL, params=params, headers={"Accept": "application/json"})

        if r.status_code != 200:
            st.error(f"API-feil: {r.status_code} – {r.text}")
            break

        data = r.json()
        enheter = data.get("_embedded", {}).get("enheter", [])
        alle_enheter.extend(enheter)

        # Hent totalt én gang fra første side
        if side == 0:
            totalt = data.get("page", {}).get("totalElements", 0)

        total_sider = data.get("page", {}).get("totalPages", 1)
        side += 1

        if side >= total_sider:
            break

    return alle_enheter, totalt


def bygg_dataframe(enheter: list) -> pd.DataFrame:
    """Pakker ut relevante felter fra API-svaret og returnerer en DataFrame."""
    resultater = []
    for enhet in enheter:
        adresse_obj  = enhet.get("forretningsadresse") or enhet.get("postadresse") or {}
        adresse_str  = ", ".join([a for a in adresse_obj.get("adresse", []) if a])
        poststed     = adresse_obj.get("poststed", "")
        postnr       = adresse_obj.get("postnummer", "")
        full_adresse = f"{adresse_str}, {postnr} {poststed}".strip(", ")

        resultater.append({
            "Navn":        enhet.get("navn", "–"),
            "Org.nr":      enhet.get("organisasjonsnummer", "–"),
            "Næringskode": enhet.get("naeringskode1", {}).get("kode", "–"),
            "Beskrivelse": enhet.get("naeringskode1", {}).get("beskrivelse", "–"),
            "Adresse":     full_adresse or "–",
            "Telefon":     enhet.get("telefon") or enhet.get("mobil") or "–",
            "E-post":      enhet.get("epostadresse") or "–",
            "Hjemmeside":  enhet.get("hjemmeside") or "–",
        })

    return pd.DataFrame(resultater)


# ── Næringskode-katalog ───────────────────────────────────

NAERINGSKODER = {
    "Mat & Drikke": {
        "56.101": "Restauranter",
        "56.102": "Kafeer",
        "56.301": "Barer og puber",
        "47.241": "Bakeri",
    },
    "Handel": {
        "47.111": "Dagligvarebutikker",
        "47.191": "Ikke-spesialisert butikkhandel",
        "46.900": "Ikke-spesialisert engroshandel",
        "47.710": "Klesbutikker",
        "47.520": "Jernvare og byggevarer",
    },
    "IT & Teknologi": {
        "62.010": "Programvareutvikling",
        "62.020": "IT-konsulenter",
        "62.090": "Andre IT-tjenester",
        "63.110": "Databehandling og drift",
    },
    "Bygg & Anlegg": {
        "41.200": "Bygging av boliger",
        "43.210": "Elektriske installasjoner",
        "43.220": "VVS-arbeid",
        "43.310": "Maling og tapetsering",
    },
    "Helse": {
        "86.211": "Allmennlegetjenester",
        "86.220": "Spesialistlegetjenester",
        "86.901": "Fysioterapitjenester",
        "88.101": "Hjemmetjenester",
    },
    "Kontor & Administrasjon": {
        "69.201": "Regnskap og bokføring",
        "70.220": "Bedriftsrådgivning",
        "73.110": "Reklamebyråer",
        "78.100": "Arbeidsformidling",
    },
    "Personlige tjenester": {
        "96.020": "Frisører",
        "96.021": "Skjønnhetssalonger",
        "93.110": "Treningssentre",
        "96.090": "Andre personlige tjenester",
    },
    "Transport": {
        "49.410": "Godstransport på vei",
        "49.320": "Drosjebiltransport",
        "45.200": "Bilverksteder",
        "45.111": "Bilforhandlere",
    },
}


# ── Streamlit UI ──────────────────────────────────────────

st.set_page_config(page_title="Bedriftssøk", layout="wide")

# Initialiser session state
for key, default in {
    "valgt_kode": "56.101",
    "enheter": None,
    "totalt": 0,
    "sok_naeringskode": "",   # ← lagrer hvilken kode/kommune som ble søkt på
    "sok_kommune": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Sidebar ───────────────────────────────────────────────

with st.sidebar:
    st.logo("static/uldre.png", link="https://uldre.no")
    st.markdown("### Næringskode-hjelp")
    st.markdown("Trykk **Bruk** for å fylle inn koden automatisk.")
    st.markdown("---")

    for bransje, koder in NAERINGSKODER.items():
        with st.expander(bransje):
            for kode, beskrivelse in koder.items():
                col_kode, col_bruk = st.columns([2, 1])
                with col_kode:
                    st.markdown(f"`{kode}` {beskrivelse}")
                with col_bruk:
                    if st.button("Bruk", key=f"btn_{kode}"):
                        st.session_state["valgt_kode"] = kode
                        st.rerun()

    st.markdown("---")
    st.markdown("Utviklet av **Uldre**")


# ── Hovedinnhold ──────────────────────────────────────────

col_left, col_right = st.columns([3, 1])

with col_left:
    st.title("Bedriftssøk")
    st.markdown("Søk etter bedrifter i Enhetsregisteret basert på næringskode og kommune.")

with col_right:
    if os.path.exists("static/uldre.png"):
        st.image("static/uldre.png", use_container_width=True)

# Inputfelter
col1, col2 = st.columns(2)
with col1:
    naeringskode = st.text_input(
        "Næringskode",
        value=st.session_state["valgt_kode"],
        help="Velg fra sidebaren eller skriv inn manuelt. F.eks. 56.101 = Restaurant"
    )
with col2:
    kommune = st.text_input("Kommune", value="Trondheim")

sok_knapp = st.button("Søk", type="primary")


# ── Søkeprosess ───────────────────────────────────────────

if sok_knapp:
    if not naeringskode or not kommune:
        st.warning("Fyll inn både næringskode og kommune.")
    else:
        with st.spinner(f"Slår opp kommunenummer for {kommune}..."):
            kommunenr = hent_kommunenummer(kommune)

        if not kommunenr:
            st.error(f"Fant ikke kommunenummer for «{kommune}». Sjekk stavemåten.")
        else:
            with st.spinner("Henter bedrifter..."):
                enheter, totalt = sok_alle_sider(naeringskode, kommunenr)

            # ✅ Lagre både resultater OG søkeparametrene som ble brukt
            st.session_state["enheter"]         = enheter
            st.session_state["totalt"]           = totalt
            st.session_state["sok_naeringskode"] = naeringskode
            st.session_state["sok_kommune"]      = kommune


# ── Vis resultater ────────────────────────────────────────

if st.session_state["enheter"]:

    # Bruk parametrene fra da søket ble gjort – ikke nåværende inputfelt
    sok_kode     = st.session_state["sok_naeringskode"]
    sok_kommunen = st.session_state["sok_kommune"]

    df = bygg_dataframe(st.session_state["enheter"])

    st.success(
        f"Fant **{st.session_state['totalt']} bedrifter** "
        f"med næringskode {sok_kode} i {sok_kommunen}."
    )

    kun_med_kontakt = st.checkbox("Kun vis bedrifter med telefon eller e-post")

    if kun_med_kontakt:
        df = df[(df["Telefon"] != "–") | (df["E-post"] != "–")]

    st.info(f"Viser {len(df)} bedrifter")
    st.dataframe(df, use_container_width=True)

    # Opprett Excel-fil i minnet
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_buffer.seek(0)

    
    st.download_button(
        label="Last ned som Excel",
        data=excel_buffer,
        file_name=f"bedrifter_{sok_kode.replace('.','_')}_{sok_kommunen}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False  
    )