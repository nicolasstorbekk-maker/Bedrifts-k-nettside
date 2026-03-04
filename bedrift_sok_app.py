import streamlit as st
import io
import os

from api import hent_kommunenummer, sok_alle_sider
from data_processing import bygg_dataframe
from constants import NAERINGSKODER


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
    st.markdown("### Næringskode katalog")
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
    st.markdown("Dette er bare et lite utvalg av koder. Søk etter andre koder " \
    "på [brreg.no](https://www.ssb.no/klass/klassifikasjoner/6).")
    st.markdown("Appen er utviklet av **Uldre**")



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