#!/usr/bin/env python3
# <xbar.title>ChartMogul Revenue</xbar.title>
# <xbar.version>v2.2</xbar.version>
# <xbar.author>Tobias Brauchle</xbar.author>
# <xbar.desc>Rotates MRR / ARR / Subscribers / ARPA / LTV / Lifetime / net movement in the menu bar; full breakdown in the dropdown.</xbar.desc>
# <xbar.dependencies>python3</xbar.dependencies>
# <xbar.abouturl>https://dev.chartmogul.com/reference/metrics</xbar.abouturl>
#
# Setup:
#   1) Store the API key in ~/.config/revenue-stats-bar/token (chmod 600)
#      OR set the CHARTMOGUL_API_KEY environment variable.
#   2) chmod +x and symlink it into the SwiftBar plugins folder.
#
# Rotation: the menu-bar value advances to the next metric on every refresh.
# The refresh/rotation interval is the number in the filename: revenue.1m.py = every minute.
# Rename to change it (revenue.2m.py, revenue.5m.py, ...). API data is cached for
# DATA_TTL_SECONDS so fast rotation barely costs any API calls.

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

# --- Configuration -----------------------------------------------------------
CURRENCY_SYMBOL = "€"
API_ROOT = "https://api.chartmogul.com/v1/metrics"
CONFIG_DIR = os.path.expanduser("~/.config/revenue-stats-bar")
TOKEN_FILE = os.path.join(CONFIG_DIR, "token")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")
TIMEOUT = 10
DATA_TTL_SECONDS = 600  # cache data this long (10 min); only the display rotates faster

# Order of the menu-bar rotation. Remove an entry to drop it from the bar.
ROTATION = ["mrr", "arr", "subscribers", "arpa", "ltv", "lifetime", "net"]
# ROTATE = False -> always show the first metric in ROTATION (no rotation).
ROTATE = True

MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]


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
    """Fetch every metric and flatten it into one structure."""
    today = date.today().isoformat()
    month_start = date.today().replace(day=1).isoformat()
    day = {"start-date": today, "end-date": today, "interval": "day"}

    data = {}
    # Stock metrics with their 30-day change (summary.percentage-change matches the dashboard)
    for key, path in (("mrr", "/mrr"), ("arr", "/arr"),
                      ("subscribers", "/customer-count"), ("arpa", "/arpa"),
                      ("ltv", "/ltv")):
        summary = api_get(api_key, path, day).get("summary", {})
        data[key] = {
            "current": summary.get("current", 0),
            "pct": summary.get("percentage-change", 0.0),
        }

    # This month's MRR movement (month to date)
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
    # Avg. customer lifetime (months) = LTV / ARPA — the relation ChartMogul derives LTV from
    arpa_c = data["arpa"]["current"] or 0
    data["lifetime"] = {"months": (data["ltv"]["current"] / arpa_c) if arpa_c else 0}
    data["fetched_at"] = time.time()
    return data


# --- State / cache -----------------------------------------------------------
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


# --- Formatting (English / ChartMogul-style: € prefix, comma thousands) -------
def fmt_eur(cents, sign=False):
    value = cents / 100.0
    s = ""
    if sign:
        s = "+" if value > 0 else ("-" if value < 0 else "")
        value = abs(value)
    return f"{s}{CURRENCY_SYMBOL}{value:,.2f}"


def fmt_eur_short(cents):
    """Compact for the menu bar, no decimals."""
    return f"{CURRENCY_SYMBOL}{round(cents / 100.0):,.0f}"


def fmt_pct(pct):
    return f"{pct:+.2f}%"


def fmt_lifetime(months, long=False):
    if not long:
        return f"{round(months)} mo"
    return f"{round(months)} months (≈ {months / 12:.1f} years)"


# Definition of each metric: (label, sfimage, bar text, pct or None)
def bar_metric(key, data):
    if key == "mrr":
        return "MRR", "chart.line.uptrend.xyaxis", fmt_eur_short(data["mrr"]["current"]), data["mrr"]["pct"]
    if key == "arr":
        return "ARR", "calendar", fmt_eur_short(data["arr"]["current"]), data["arr"]["pct"]
    if key == "subscribers":
        return "Subs", "person.2.fill", str(data["subscribers"]["current"]), data["subscribers"]["pct"]
    if key == "arpa":
        return "ARPA", "eurosign.circle", fmt_eur(data["arpa"]["current"]), data["arpa"]["pct"]
    if key == "ltv":
        return "LTV", "heart.circle", fmt_eur(data["ltv"]["current"]), data["ltv"]["pct"]
    if key == "lifetime":
        return "Lifetime", "clock", fmt_lifetime(data["lifetime"]["months"]), None
    if key == "net":
        return "Net/mo", "arrow.up.arrow.down", fmt_eur(data["month"]["net"], sign=True), None
    return key, "questionmark", "?", None


def emit_error(headline, *detail_lines):
    print(f"⚠︎ {headline} | sfimage=exclamationmark.triangle")
    print("---")
    for line in detail_lines:
        print(line)
    print(f"Updated {datetime.now():%H:%M}")
    print("Refresh now | refresh=true")


# --- Main --------------------------------------------------------------------
def main():
    api_key = load_api_key()
    if not api_key:
        emit_error("No API key",
                   "Add your key to:",
                   f"{TOKEN_FILE} | font=Menlo size=11",
                   "or set CHARTMOGUL_API_KEY. | size=11")
        return

    state = load_state()
    data = state.get("data")
    fresh = bool(data) and (time.time() - data.get("fetched_at", 0) < DATA_TTL_SECONDS)

    if not fresh:
        try:
            data = fetch_all(api_key)
            state["data"] = data
        except urllib.error.HTTPError as exc:
            if data is None:  # no cache to fall back on
                msg = "Invalid API key" if exc.code in (401, 403) else f"HTTP {exc.code}"
                emit_error("ChartMogul", f"{msg} | color=red")
                return
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            if data is None:
                emit_error("ChartMogul", "Connection error | color=red", f"{exc} | size=11")
                return

    # Pick the rotation index and advance it
    idx = state.get("idx", 0) if ROTATE else 0
    key = ROTATION[idx % len(ROTATION)]
    if ROTATE:
        state["idx"] = (idx + 1) % len(ROTATION)
    save_state(state)

    # --- Menu-bar line (rotating) ---
    # No text color in the menu bar: the system color stays readable in light & dark.
    # Trend is shown with an arrow instead (no arrow for derived values without a % trend).
    label, sfimage, value, pct = bar_metric(key, data)
    trend = ""
    if pct is not None and pct != 0:
        trend = " ▲" if pct > 0 else " ▼"
    print(f"{label} {value}{trend} | sfimage={sfimage}")

    # --- Dropdown: always the full picture ---
    print("---")
    print("Metrics (Δ = last 30 days) | size=11 color=gray")
    print(f"MRR: {fmt_eur(data['mrr']['current'])}  ({fmt_pct(data['mrr']['pct'])}) | sfimage=chart.line.uptrend.xyaxis")
    print(f"ARR (Run Rate): {fmt_eur(data['arr']['current'])}  ({fmt_pct(data['arr']['pct'])}) | sfimage=calendar")
    print(f"Paid Subscribers: {data['subscribers']['current']}  ({fmt_pct(data['subscribers']['pct'])}) | sfimage=person.2.fill")
    print(f"ARPA: {fmt_eur(data['arpa']['current'])}  ({fmt_pct(data['arpa']['pct'])}) | sfimage=eurosign.circle")
    print(f"Customer LTV: {fmt_eur(data['ltv']['current'])}  ({fmt_pct(data['ltv']['pct'])}) | sfimage=heart.circle")
    print(f"Avg. Customer Lifetime: {fmt_lifetime(data['lifetime']['months'], long=True)} | sfimage=clock")

    m = data["month"]
    print("---")
    print(f"This Month ({MONTHS_EN[date.today().month - 1]}) | size=11 color=gray")
    print(f"New Business: {fmt_eur(m['new'], sign=True)}")
    print(f"Expansion: {fmt_eur(m['expansion'], sign=True)}")
    print(f"Contraction: {fmt_eur(m['contraction'], sign=True)}")
    print(f"Churn: {fmt_eur(m['churn'], sign=True)}")
    print(f"Reactivation: {fmt_eur(m['reactivation'], sign=True)}")
    print(f"Net MRR Movement: {fmt_eur(m['net'], sign=True)} | font=Menlo-Bold")

    print("---")
    age = int(time.time() - data.get("fetched_at", time.time()))
    print(f"Updated {datetime.now():%H:%M} · data {age // 60}m old | size=11 color=gray")
    print("Refresh now | refresh=true")
    print("Open ChartMogul ↗ | href=https://app.chartmogul.com")


if __name__ == "__main__":
    main()
