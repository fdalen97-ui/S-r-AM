# ✈️ Daglig flyprissjekk – Oslo ↔ Australia (valgt plan, jan 2027)

Sporer flyene til den **valgte planen**: bobiltur Brisbane → Melbourne
2.–31. januar 2027 (`../00-planlegging/australia-bobil-jan2027.md`).
Open-jaw: **inn Brisbane (BNE), ut Melbourne (MEL)** — de to bena spores som
enveis-billetter, men bookes som multi-city.

**Mål: sum av de to bena ≤ 16 000 kr p.p.** (research-estimat 13 000–17 000
for januar-open-jaw). Verktøyet sjekker laveste pris i avreisevinduene, logger
historikk og **varsler deg på mobilen** når et ben faller under terskel eller
setter ny bunnrekord.

- Kun Python 3 standardbibliotek – **ingen `pip install`**
- Gratis prisdata via **Amadeus Self-Service API**
- Gratis push-varsel til mobil via **ntfy.sh** (valgfritt, ingen konto)

## Vinduene som spores

| Ben | Datoer | Varsel under |
|-----|--------|--------------|
| OSL → BNE | 28. des 2026 – 2. jan 2027 (ankomst 1.–2. jan pga. tidssone) | 8 500 kr |
| MEL → OSL | 30. jan – 3. feb 2027 (etter AO-finalene 30.–31. jan) | 8 000 kr |

Aktuelle selskaper: Qatar (Doha), Emirates (Dubai), Singapore Airlines,
China Southern (ofte billigst, via Guangzhou). Stopover i Singapore/Doha
koster ofte ingenting ekstra.

---

## 1. Engangsoppsett (ca. 10 min)

### a) Skaff gratis API-nøkler
1. Lag konto på <https://developers.amadeus.com>
2. **My Self-Service Workspace → Create New App**
3. Kopier `API Key` og `API Secret`
4. Kopier `.env.eksempel` til `.env` og lim inn nøklene:

```bash
cp .env.eksempel .env
# rediger .env og fyll inn nøklene
```

> Test-miljøet (`test.api.amadeus.com`) er gratis og holder til prissporing.
> Vil du ha mer nøyaktige/ferske priser, klikk **"Move to Production"** i Amadeus
> (fortsatt gratis kvote) og bytt `amadeus_base_url` i `config.json` til
> `https://api.amadeus.com`.

### b) (Valgfritt) Push-varsel til mobil
1. Installer **ntfy**-appen (iOS/Android) – gratis, ingen registrering
2. Abonner på et hemmelig emne-navn, f.eks. `flypris-australia-7x9k2`
3. Skriv samme navn inn i `config.json` → `varsling.ntfy_emne`

---

## 2. Kjøre manuelt

```bash
cd sor-amerika/10-prissporing
python3 sjekk_priser.py
```

Du ser laveste pris per dato, dagens beste per ben, og evt. varsel.
Alt logges til `prishistorikk.csv`.

---

## 3. Daglig rutine (cron)

```bash
crontab -e
```

```cron
0 8 * * *  cd ~/S-r-AM/sor-amerika/10-prissporing && /usr/bin/python3 sjekk_priser.py >> logg.txt 2>&1
```

Mac: bruk `launchd`. Windows: Oppgaveplanlegging med `python sjekk_priser.py`.

---

## 4. Booking-strategi for akkurat disse flyene

- **Book som multi-city/open-jaw** (inn BNE / ut MEL) — prises ca. som snittet
  av to t/r, og alltid billigere enn to enveis.
- **Jakt fra oktober**: forventet bunn for januar-avganger er sept–nov.
  Under 16 000 samlet = bra; under 14 000 = slå til umiddelbart.
- Romjuls-utreisen (28.–31. des) er peak — **1.–2. jan-avgang er ofte
  merkbart billigere** hvis bobil-hentingen kan skyves en dag.
- Retur etter AO-finalene: 31. jan–3. feb. Australsk skoleferie varer ut
  januar, så returen faller ikke like raskt som til Asia — ikke vent på et
  stup som ikke kommer.

## 5. Tilpasse (`config.json`)

| Felt | Betydning |
|------|-----------|
| `ruter[].fra` / `til` | Flyplasskoder (OSL, BNE, MEL, SYD …) |
| `avreise_fra` / `avreise_til` | Dato-vinduet per ben |
| `steg_dager` | 1 = sjekk hver dato i vinduet |
| `kun_ukedager` | tom liste = alle dager (vinduene er smale) |
| `varsle_under` | Send varsel når pris ≤ dette |
| `maks_mellomlandinger` | 2 (Australia krever oftest 1–2 stopp) |

## 6. Se prisutviklingen

`prishistorikk.csv` har én rad per ben per dag — åpne i Excel/Numbers eller:

```bash
column -s, -t prishistorikk.csv | less -S
```

Når kurven flater ut lavt, eller varselet plinger: **book multi-city med én
gang** — januar-seter til Australia blir ikke billigere av å vente forbi
november.

> `.env` og `prishistorikk.csv` er holdt utenfor git (se `.gitignore`).
> Historikk for de gamle Sør-Amerika-rutene kan stå — scriptet skiller på rutenavn.
