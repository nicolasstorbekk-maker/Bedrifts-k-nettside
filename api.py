import requests
import streamlit as st

BASE_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"


@st.cache_data
def hent_kommunenummer(kommunenavn: str) -> str | None:
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
    alle_enheter = []
    totalt = 0
    side = 0

    while True:
        params = {
            "naeringskode": naeringskode,
            "forretningsadresse.kommunenummer": kommunenr,
            "size": 100,
            "page": side,
        }

        r = requests.get(BASE_URL, params=params, headers={"Accept": "application/json"})

        if r.status_code != 200:
            st.error(f"API-feil: {r.status_code}")
            break

        data = r.json()
        enheter = data.get("_embedded", {}).get("enheter", [])
        alle_enheter.extend(enheter)

        if side == 0:
            totalt = data.get("page", {}).get("totalElements", 0)

        total_sider = data.get("page", {}).get("totalPages", 1)
        side += 1

        if side >= total_sider:
            break

    return alle_enheter, totalt

