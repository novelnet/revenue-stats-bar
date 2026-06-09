#!/usr/bin/env python3
# <xbar.title>ChartMogul Revenue</xbar.title>
# <xbar.version>v2.1</xbar.version>
# <xbar.author>Tobias Brauchle</xbar.author>
# <xbar.desc>Rotiert MRR / ARR / Subscribers / ARPA / Netto-Movement in der Menüleiste; volles ChartMogul-Bild im Dropdown.</xbar.desc>
# <xbar.dependencies>python3</xbar.dependencies>
# <xbar.abouturl>https://dev.chartmogul.com/reference/metrics</xbar.abouturl>
#
# Setup:
#   1) API-Key ablegen unter ~/.config/revenue-stats-bar/token (chmod 600)
#      ODER Umgebungsvariable CHARTMOGUL_API_KEY setzen.
#   2) chmod +x und in den SwiftBar-Plugins-Ordner verlinken.
#
# Rotation: Die Menüleisten-Zahl wechselt bei jedem Refresh zur nächsten Kennzahl.
# Das Refresh-/Rotations-Intervall steckt im Dateinamen: revenue.1m.py = jede Minute.
# Umbenennen ändert es (revenue.2m.py, revenue.5m.py, ...). Die API-Daten werden
# DATA_TTL_SECONDS lang gecacht, damit schnelle Rotation kaum API-Calls kostet.

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

# --- Konfiguration -----------------------------------------------------------
CURRENCY_SYMBOL = "€"
API_ROOT = "https://api.chartmogul.com/v1/metrics"
CONFIG_DIR = os.path.expanduser("~/.config/revenue-stats-bar")
TOKEN_FILE = os.path.join(CONFIG_DIR, "token")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")
TIMEOUT = 10
DATA_TTL_SECONDS = 600  # Daten so lange cachen (10 Min), nur Anzeige rotiert schneller

# Reihenfolge der Rotation in der Menüleiste. Eintrag hier raus = nicht mehr in der Bar.
ROTATION = ["mrr", "arr", "subscribers", "arpa", "ltv", "net"]
# ROTATE = False -> immer die erste Kennzahl aus ROTATION anzeigen (keine Rotation).
ROTATE = True


# --- HTTP --------------------------------------------------------------------
def load_api_key():
    key = os.environ.get("CHARTMOGUL_API_KEY", "").strip()
    if key:
        return key
    try:
        with open(TOKEN_FILE) as fh:
            return fh.read().strip()
    except OSError:
        return ""


def api_get(api_key, path, params):
    url = f"{API_ROOT}{path}?{urllib.parse.urlencode(params)}"
    auth = base64.b64encode(f"{api_key}:".encode()).decode("ascii")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all(api_key):
    """Alle Kennzahlen holen und in eine flache Struktur bringen."""
    today = date.today().isoformat()
    month_start = date.today().replace(day=1).isoformat()
    day = {"start-date": today, "end-date": today, "interval": "day"}

    data = {}
    # Bestandsgrößen mit 30-Tage-Änderung (summary.percentage-change matcht das Dashboard)
    for key, path in (("mrr", "/mrr"), ("arr", "/arr"),
                      ("subscribers", "/customer-count"), ("arpa", "/arpa"),
                      ("ltv", "/ltv")):
        summary = api_get(api_key, path, day).get("summary", {})
        data[key] = {
            "current": summary.get("current", 0),
            "pct": summary.get("percentage-change", 0.0),
        }

    # Monats-MRR-Movement (Monat bis heute)
    month = api_get(api_key, "/mrr", {
        "start-date": month_start, "end-date": today, "interval": "month",
    })
    entries = month.get("entries") or [{}]
    e = entries[-1]
    nb = e.get("mrr-new-business", 0) or 0
    ex = e.get("mrr-expansion", 0) or 0
    co = e.get("mrr-contraction", 0) or 0
    ch = e.get("mrr-churn", 0) or 0
    re = e.get("mrr-reactivation", 0) or 0
    data["month"] = {
        "new": nb, "expansion": ex, "contraction": co,
        "churn": ch, "reactivation": re, "net": nb + ex + co + ch + re,
    }
    data["fetched_at"] = time.time()
    return data


# --- State / Cache -----------------------------------------------------------
def load_state():
    try:
        with open(STATE_FILE) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_state(state):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(STATE_FILE, "w") as fh:
            json.dump(state, fh)
    except OSError:
        pass


# --- Formatierung ------------------------------------------------------------
def fmt_eur(cents, sign=False):
    value = cents / 100.0
    s = ""
    if sign:
        s = "+" if value > 0 else ("−" if value < 0 else "")
        value = abs(value)
    body = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s}{body} {CURRENCY_SYMBOL}"


def fmt_eur_short(cents):
    """Kompakt für die Menüleiste, ohne Nachkommastellen."""
    value = round(cents / 100.0)
    body = f"{value:,.0f}".replace(",", ".")
    return f"{body} {CURRENCY_SYMBOL}"


def fmt_pct(pct):
    return f"{pct:+.2f}%".replace(".", ",")


# Definition jeder Kennzahl: (label, sfimage, bar-text-funktion)
def bar_metric(key, data):
    if key == "mrr":
        return "MRR", "chart.line.uptrend.xyaxis", fmt_eur_short(data["mrr"]["current"]), data["mrr"]["pct"]
    if key == "arr":
        return "ARR", "calendar", fmt_eur_short(data["arr"]["current"]), data["arr"]["pct"]
    if key == "subscribers":
        return "Abos", "person.2.fill", str(data["subscribers"]["current"]), data["subscribers"]["pct"]
    if key == "arpa":
        return "ARPA", "eurosign.circle", fmt_eur(data["arpa"]["current"]), data["arpa"]["pct"]
    if key == "ltv":
        return "LTV", "heart.circle", fmt_eur(data["ltv"]["current"]), data["ltv"]["pct"]
    if key == "net":
        net = data["month"]["net"]
        return "Netto/M", "arrow.up.arrow.down", fmt_eur(net, sign=True), None
    return key, "questionmark", "?", None


def emit_error(headline, *detail_lines):
    print(f"⚠︎ {headline} | sfimage=exclamationmark.triangle")
    print("---")
    for line in detail_lines:
        print(line)
    print(f"Stand: {datetime.now():%H:%M}")
    print("Refresh | refresh=true")


# --- Hauptlogik --------------------------------------------------------------
def main():
    api_key = load_api_key()
    if not api_key:
        emit_error("Kein API-Key",
                   "Key ablegen unter:",
                   f"{TOKEN_FILE} | font=Menlo size=11",
                   "oder CHARTMOGUL_API_KEY setzen. | size=11")
        return

    state = load_state()
    data = state.get("data")
    fresh = bool(data) and (time.time() - data.get("fetched_at", 0) < DATA_TTL_SECONDS)

    if not fresh:
        try:
            data = fetch_all(api_key)
            state["data"] = data
        except urllib.error.HTTPError as exc:
            if data is None:  # kein Cache als Fallback
                msg = "Ungültiger API-Key" if exc.code in (401, 403) else f"HTTP {exc.code}"
                emit_error("ChartMogul", f"{msg} | color=red")
                return
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            if data is None:
                emit_error("ChartMogul", f"Verbindungsfehler | color=red", f"{exc} | size=11")
                return

    # Rotationsindex bestimmen und weiterschalten
    idx = state.get("idx", 0) if ROTATE else 0
    key = ROTATION[idx % len(ROTATION)]
    if ROTATE:
        state["idx"] = (idx + 1) % len(ROTATION)
    save_state(state)

    # --- Menüleisten-Zeile (rotierend) ---
    label, sfimage, value, pct = bar_metric(key, data)
    color = ""
    if pct is not None:
        color = " color=#37b24d" if pct >= 0 else " color=#f03e3e"
    print(f"{label} {value} | sfimage={sfimage}{color}")

    # --- Dropdown: immer das volle Bild ---
    print("---")
    print("Kennzahlen (Δ = letzte 30 Tage) | size=11 color=gray")
    print(f"MRR: {fmt_eur(data['mrr']['current'])}  ({fmt_pct(data['mrr']['pct'])}) | sfimage=chart.line.uptrend.xyaxis")
    print(f"ARR (Run Rate): {fmt_eur(data['arr']['current'])}  ({fmt_pct(data['arr']['pct'])}) | sfimage=calendar")
    print(f"Paid Subscribers: {data['subscribers']['current']}  ({fmt_pct(data['subscribers']['pct'])}) | sfimage=person.2.fill")
    print(f"ARPA: {fmt_eur(data['arpa']['current'])}  ({fmt_pct(data['arpa']['pct'])}) | sfimage=eurosign.circle")
    print(f"Customer LTV: {fmt_eur(data['ltv']['current'])}  ({fmt_pct(data['ltv']['pct'])}) | sfimage=heart.circle")

    m = data["month"]
    months_de = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
                 "August", "September", "Oktober", "November", "Dezember"]
    print("---")
    print(f"Diesen Monat ({months_de[date.today().month - 1]}) | size=11 color=gray")
    print(f"New Business: {fmt_eur(m['new'], sign=True)}")
    print(f"Expansion: {fmt_eur(m['expansion'], sign=True)}")
    print(f"Contraction: {fmt_eur(m['contraction'], sign=True)}")
    print(f"Churn: {fmt_eur(m['churn'], sign=True)}")
    print(f"Reactivation: {fmt_eur(m['reactivation'], sign=True)}")
    print(f"Net MRR Movement: {fmt_eur(m['net'], sign=True)} | font=Menlo-Bold")

    print("---")
    age = int(time.time() - data.get("fetched_at", time.time()))
    print(f"Daten {age//60}m alt · {datetime.now():%H:%M} | size=11 color=gray")
    print("Jetzt aktualisieren | refresh=true")
    print("Zu ChartMogul ↗ | href=https://app.chartmogul.com")


if __name__ == "__main__":
    main()
