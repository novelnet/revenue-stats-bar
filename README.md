# revenue-stats-bar

Zeigt deine wichtigsten **ChartMogul-Kennzahlen** in der macOS-Menüleiste über
[SwiftBar](https://github.com/swiftbar/SwiftBar).

Die Menüleisten-Zahl **rotiert** bei jedem Refresh durch die Kennzahlen
(MRR → ARR → Subscribers → ARPA → LTV → Ø Kundenlebensdauer → Netto-Movement diesen
Monat), mit ▲/▼-Trend (30 Tage). Das Aufklapp-Menü zeigt immer **alles**:

- MRR, ARR (Run Rate), Paid Subscribers, ARPA, Customer LTV — jeweils mit 30-Tage-Änderung
- Ø Kundenlebensdauer (abgeleitet aus LTV ÷ ARPA)
- MRR-Movement des laufenden Monats (New Business, Expansion, Contraction, Churn,
  Reactivation, Net)

Die Werte stammen aus den ChartMogul-Metrics-Endpoints (`/v1/metrics/mrr`, `/arr`,
`/customer-count`, `/arpa`, `/ltv`). Daten werden 10 Min gecacht, damit schnelle Rotation
kaum API-Calls kostet.

## Voraussetzungen
- macOS mit `python3` (nur Standardbibliothek)
- ChartMogul-API-Key: **Admin → API Keys**

## Installation

1. **SwiftBar installieren**
   ```sh
   brew install --cask swiftbar
   ```
   Beim ersten Start einen **Plugin-Ordner** wählen, z. B. `~/SwiftBar-Plugins`.

2. **API-Key ablegen**
   ```sh
   mkdir -p ~/.config/revenue-stats-bar
   printf '%s' 'DEIN_CHARTMOGUL_API_KEY' > ~/.config/revenue-stats-bar/token
   chmod 600 ~/.config/revenue-stats-bar/token
   ```
   Alternativ: Umgebungsvariable `CHARTMOGUL_API_KEY` setzen.

3. **Plugin verlinken** (Repo bleibt Quelle der Wahrheit):
   ```sh
   chmod +x revenue.1m.py
   ln -s "$(pwd)/revenue.1m.py" ~/SwiftBar-Plugins/revenue.1m.py
   ```

4. In SwiftBar **„Refresh all"** auslösen.

## Anpassen (oben in `revenue.1m.py`)
- **Rotations-Tempo:** Zahl im Dateinamen, z. B. `revenue.2m.py` = alle 2 Min weiterschalten.
- **Welche Kennzahlen rotieren:** Liste `ROTATION` (Eintrag entfernen = nicht mehr in der Bar).
- **Rotation aus:** `ROTATE = False` → zeigt fix die erste Kennzahl aus `ROTATION`.
- **Cache-Dauer:** `DATA_TTL_SECONDS` (Default 600 = 10 Min).
- **Währungssymbol:** `CURRENCY_SYMBOL` (Default `€`).

## Schnelltest ohne SwiftBar
```sh
CHARTMOGUL_API_KEY='DEIN_KEY' python3 revenue.1m.py
```
Mehrfach ausführen → die erste Zeile rotiert durch die Kennzahlen.
Ohne/mit falschem Key zeigt das Plugin `⚠︎ …` statt eines Tracebacks.

## Dateien
- `revenue.1m.py` — das SwiftBar-Plugin
- `config.example` — Vorlage für die Token-Datei
- `.gitignore`, `README.md`
- Laufzeit-State: `~/.config/revenue-stats-bar/state.json` (Cache + Rotationsindex)
