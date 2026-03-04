import pandas as pd


def bygg_dataframe(enheter: list) -> pd.DataFrame:
    resultater = []

    for enhet in enheter:
        adresse_obj = enhet.get("forretningsadresse") or enhet.get("postadresse") or {}
        adresse_str = ", ".join([a for a in adresse_obj.get("adresse", []) if a])
        poststed = adresse_obj.get("poststed", "")
        postnr = adresse_obj.get("postnummer", "")
        full_adresse = f"{adresse_str}, {postnr} {poststed}".strip(", ")

        resultater.append({
            "Navn": enhet.get("navn", "–"),
            "Org.nr": enhet.get("organisasjonsnummer", "–"),
            "Næringskode": enhet.get("naeringskode1", {}).get("kode", "–"),
            "Beskrivelse": enhet.get("naeringskode1", {}).get("beskrivelse", "–"),
            "Adresse": full_adresse or "–",
            "Telefon": enhet.get("telefon") or enhet.get("mobil") or "–",
            "E-post": enhet.get("epostadresse") or "–",
            "Hjemmeside": enhet.get("hjemmeside") or "–",
        })

    return pd.DataFrame(resultater)

