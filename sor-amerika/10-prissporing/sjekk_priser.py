#!/usr/bin/env python3
"""Daglig flyprissjekk for Sør-Amerika-turen (Oslo → ...).

Sjekker laveste pris for rutene i config.json over hele dato-vinduet ditt
(f.eks. slutten av oktober → november), logger historikk til prishistorikk.csv
og varsler deg når prisen faller under en terskel eller setter ny bunnrekord.

Bruker Amadeus Self-Service API (gratis). Kun standardbibliotek – ingen pip.

Oppsett: se README.md
Kjør:    python3 sjekk_priser.py
"""

import os
import sys
import json
import csv
import time
import datetime as dt
import urllib.request
import urllib.parse
import urllib.error

HER = os.path.dirname(os.path.abspath(__file__))
CONFIG_FIL = os.path.join(HER, "config.json")
HISTORIKK_FIL = os.path.join(HER, "prishistorikk.csv")
ENV_FIL = os.path.join(HER, ".env")


# ---------------------------------------------------------------------------
# Oppsett og hjelpefunksjoner
# ---------------------------------------------------------------------------
def les_env():
    """Leser AMADEUS_API_KEY / AMADEUS_API_SECRET fra miljø eller .env-fil."""
    if os.path.exists(ENV_FIL):
        with open(ENV_FIL, encoding="utf-8") as f:
            for linje in f:
                linje = linje.strip()
                if not linje or linje.startswith("#") or "=" not in linje:
                    continue
                navn, _, verdi = linje.partition("=")
                os.environ.setdefault(navn.strip(), verdi.strip().strip('"').strip("'"))
    nokkel = os.environ.get("AMADEUS_API_KEY")
    hemmelig = os.environ.get("AMADEUS_API_SECRET")
    if not nokkel or not hemmelig:
        sys.exit(
            "FEIL: Mangler API-nøkler.\n"
            "Lag en gratis app på https://developers.amadeus.com og legg inn:\n"
            "  AMADEUS_API_KEY=...\n"
            "  AMADEUS_API_SECRET=...\n"
            "i en .env-fil her, eller som miljøvariabler. Se README.md."
        )
    return nokkel, hemmelig


def les_config():
    with open(CONFIG_FIL, encoding="utf-8") as f:
        return json.load(f)


def hent_token(base, nokkel, hemmelig):
    data = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": nokkel,
            "client_secret": hemmelig,
        }
    ).encode()
    req = urllib.request.Request(
        base + "/v1/security/oauth2/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


def kandidat_datoer(fra_str, til_str, steg, ukedager):
    """Genererer avreisedatoer fra..til med gitt steg, evt. filtrert på ukedag.

    ukedager: liste med 0=mandag ... 6=søndag, eller tom = alle.
    """
    fra = dt.date.fromisoformat(fra_str)
    til = dt.date.fromisoformat(til_str)
    i_dag = dt.date.today()
    datoer = []
    d = fra
    while d <= til:
        if d > i_dag and (not ukedager or d.weekday() in ukedager):
            datoer.append(d.isoformat())
        d += dt.timedelta(days=steg)
    return datoer


def sok_pris(base, token, fra, til, avreise, retur, voksne, valuta, maks_stop):
    """Returnerer billigste tilbud for én dato, eller None."""
    params = {
        "originLocationCode": fra,
        "destinationLocationCode": til,
        "departureDate": avreise,
        "adults": voksne,
        "currencyCode": valuta,
        "max": 20,
    }
    if retur:
        params["returnDate"] = retur
    url = base + "/v2/shopping/flight-offers?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"   ! API-feil ({e.code}) for {avreise}: {e.read().decode()[:120]}")
        return None
    except Exception as e:  # noqa: BLE001
        print(f"   ! Nettverksfeil for {avreise}: {e}")
        return None

    beste = None
    for o in payload.get("data", []):
        stop = max(len(it["segments"]) - 1 for it in o["itineraries"])
        if stop > maks_stop:
            continue
        pris = float(o["price"]["grandTotal"])
        if beste is None or pris < beste["pris"]:
            selskap = (o.get("validatingAirlineCodes") or ["?"])[0]
            beste = {"pris": pris, "stop": stop, "selskap": selskap}
    return beste


def tidligere_bunn(rute_navn):
    """Laveste pris logget tidligere for ruten, eller None."""
    if not os.path.exists(HISTORIKK_FIL):
        return None
    bunn = None
    with open(HISTORIKK_FIL, encoding="utf-8", newline="") as f:
        for rad in csv.DictReader(f):
            if rad["rute"] != rute_navn:
                continue
            try:
                p = float(rad["pris"])
            except ValueError:
                continue
            if bunn is None or p < bunn:
                bunn = p
    return bunn


def skriv_historikk(rad):
    ny_fil = not os.path.exists(HISTORIKK_FIL)
    with open(HISTORIKK_FIL, "a", encoding="utf-8", newline="") as f:
        skriver = csv.writer(f)
        if ny_fil:
            skriver.writerow(
                ["dato_sjekket", "rute", "avreise", "retur", "pris", "valuta", "selskap", "stop"]
            )
        skriver.writerow(rad)


def varsle_ntfy(emne, tittel, melding, prioritet="default"):
    if not emne:
        return
    url = "https://ntfy.sh/" + emne
    req = urllib.request.Request(
        url,
        data=melding.encode("utf-8"),
        headers={"Title": tittel, "Priority": prioritet, "Tags": "airplane,money_with_wings"},
    )
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:  # noqa: BLE001
        print(f"   ! Klarte ikke sende ntfy-varsel: {e}")


# ---------------------------------------------------------------------------
# Hovedløp
# ---------------------------------------------------------------------------
def main():
    cfg = les_config()
    nokkel, hemmelig = les_env()
    base = cfg.get("amadeus_base_url", "https://test.api.amadeus.com")
    valuta = cfg.get("valuta", "NOK")
    voksne = cfg.get("antall_voksne", 1)
    maks_stop = cfg.get("maks_mellomlandinger", 2)
    sov = cfg.get("sov_mellom_kall_sekunder", 1.0)
    emne = cfg.get("varsling", {}).get("ntfy_emne", "")
    i_dag = dt.date.today().isoformat()

    print(f"== Flyprissjekk {i_dag} ==  (valuta: {valuta}, base: {base})")
    token = hent_token(base, nokkel, hemmelig)

    for rute in cfg["ruter"]:
        navn = rute["navn"]
        print(f"\n>>> {navn}")
        datoer = kandidat_datoer(
            rute["avreise_fra"], rute["avreise_til"],
            rute.get("steg_dager", 3), rute.get("kun_ukedager", []),
        )
        if not datoer:
            print("   (ingen gyldige datoer i vinduet)")
            continue

        rute_beste = None
        for avreise in datoer:
            retur = None
            if rute.get("retur_etter_dager"):
                retur = (
                    dt.date.fromisoformat(avreise)
                    + dt.timedelta(days=rute["retur_etter_dager"])
                ).isoformat()
            res = sok_pris(base, token, rute["fra"], rute["til"], avreise, retur,
                           voksne, valuta, maks_stop)
            if res:
                merk = ""
                if rute_beste is None or res["pris"] < rute_beste["pris"]:
                    rute_beste = {**res, "avreise": avreise, "retur": retur}
                    merk = "  <- billigst så langt"
                print(f"   {avreise} -> {retur or 'en vei'}: "
                      f"{res['pris']:.0f} {valuta} ({res['selskap']}, {res['stop']} stop){merk}")
            time.sleep(sov)

        if not rute_beste:
            print("   Fant ingen tilbud.")
            continue

        # Logg + sammenlign
        bunn_for = tidligere_bunn(navn)
        skriv_historikk([
            i_dag, navn, rute_beste["avreise"], rute_beste["retur"] or "",
            f"{rute_beste['pris']:.0f}", valuta, rute_beste["selskap"], rute_beste["stop"],
        ])

        pris = rute_beste["pris"]
        print(f"   == Dagens beste: {pris:.0f} {valuta} "
              f"({rute_beste['avreise']}, {rute_beste['selskap']})")

        ny_rekord = bunn_for is not None and pris < bunn_for
        under_terskel = pris <= rute.get("varsle_under", 0)

        if under_terskel or ny_rekord:
            grunn = []
            if under_terskel:
                grunn.append(f"under terskel {rute['varsle_under']} {valuta}")
            if ny_rekord:
                grunn.append(f"ny bunnrekord (forrige {bunn_for:.0f})")
            tittel = f"✈️ {navn}: {pris:.0f} {valuta}"
            melding = (
                f"{navn}\nPris: {pris:.0f} {valuta}\n"
                f"Avreise: {rute_beste['avreise']}"
                + (f", retur {rute_beste['retur']}" if rute_beste['retur'] else "")
                + f"\nSelskap: {rute_beste['selskap']} ({rute_beste['stop']} stop)\n"
                f"Grunn: {', '.join(grunn)}"
            )
            print(f"   *** VARSEL: {', '.join(grunn)} ***")
            varsle_ntfy(emne, tittel, melding, prioritet="high" if under_terskel else "default")
        elif bunn_for is not None:
            diff = pris - bunn_for
            print(f"   (laveste noensinne: {bunn_for:.0f} {valuta}, "
                  f"dagens er {diff:+.0f})")

    print("\nFerdig. Historikk lagret i prishistorikk.csv")


if __name__ == "__main__":
    main()
