# ✈️ Daglig flyprissjekk – Oslo → Sør-Amerika

Et lite verktøy som hver dag sjekker laveste pris for rutene dine over hele
dato-vinduet (slutten av oktober → november), logger historikk og **varsler deg
på mobilen** når prisen faller under en terskel eller setter ny bunnrekord.

- Kun Python 3 standardbibliotek – **ingen `pip install`**
- Gratis prisdata via **Amadeus Self-Service API**
- Gratis push-varsel til mobil via **ntfy.sh** (valgfritt, ingen konto)

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
2. Abonner på et hemmelig emne-navn, f.eks. `flypris-fredrik-7x9k2`
3. Skriv samme navn inn i `config.json` → `varsling.ntfy_emne`

Da får du pling på telefonen så snart en god pris dukker opp.

---

## 2. Kjøre manuelt

```bash
cd sor-amerika/10-prissporing
python3 sjekk_priser.py
```

Du ser laveste pris per dato, dagens beste per rute, og evt. varsel.
Alt logges til `prishistorikk.csv`.

---

## 3. Gjøre det til en DAGLIG rutine (cron)

Kjør automatisk hver morgen kl. 08:00:

```bash
crontab -e
```

Legg til (bytt ut stien om nødvendig):

```cron
0 8 * * *  cd ~/S-r-AM/sor-amerika/10-prissporing && /usr/bin/python3 sjekk_priser.py >> logg.txt 2>&1
```

På **Mac** kan du i stedet bruke `launchd`, og på **Windows** Oppgaveplanlegging
(Task Scheduler) som kjører `python sjekk_priser.py` daglig.

Da trenger du ikke gjøre noe selv – du får bare et varsel når prisen er god nok
til å booke.

---

## 4. Tilpasse (`config.json`)

| Felt | Betydning |
|------|-----------|
| `ruter[].fra` / `til` | Flyplasskoder (OSL, LIM, EZE, SCL, GIG, BOG …) |
| `avreise_fra` / `avreise_til` | Dato-vinduet ditt (slutten okt → nov) |
| `steg_dager` | Hvor tett datoer sjekkes (3 = hver 3. dag) |
| `kun_ukedager` | 0=man … 6=søn. `[1,2,5]` = tir/ons/lør (ofte billigst) |
| `retur_etter_dager` | Returdato = avreise + N dager. Fjern feltet for kun en vei |
| `varsle_under` | Send varsel når pris ≤ dette |
| `ma_pris` | Din egen "drømmepris" (kun til referanse i notatene) |
| `maks_mellomlandinger` | Filtrer bort ruter med for mange bytter |

### Tips for å treffe billigst
- La `kun_ukedager` stå som `[1,2,5]` – tirsdag/onsdag/lørdag er erfaringsmessig billigst.
- Vurder **open-jaw** manuelt (inn Lima, ut Buenos Aires) – se
  `../00-planlegging/flyvninger-konkret.md`. Da legger du til en egen rute som
  kun sjekker `OSL→LIM` en vei + en `EZE→OSL` en vei.
- Hold `steg_dager` på 2–3 for å spare API-kvote (test-miljøet har begrenset
  antall kall per måned).

---

## 5. Se prisutviklingen

`prishistorikk.csv` har én rad per rute per dag. Åpne i Excel/Numbers og lag en
graf, eller kjør:

```bash
column -s, -t prishistorikk.csv | less -S
```

Når kurven flater ut på et lavt nivå, eller du får et varsel – book! 🎉

> `.env` og `prishistorikk.csv` er holdt utenfor git (se `.gitignore`).
