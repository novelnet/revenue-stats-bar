# revenue-stats-bar

Shows your key **ChartMogul metrics** in the macOS menu bar via
[SwiftBar](https://github.com/swiftbar/SwiftBar).

The menu-bar value **rotates** on every refresh through the metrics
(MRR → ARR → Subscribers → ARPA → LTV → Lifetime → this month's net movement), with
a ▲/▼ trend (last 30 days). The dropdown always shows **everything**:

- MRR, ARR (Run Rate), Paid Subscribers, ARPA, Customer LTV — each with its 30-day change
- Average customer lifetime (derived from LTV ÷ ARPA)
- This month's MRR movement (New Business, Expansion, Contraction, Churn, Reactivation, Net)

Values come from the ChartMogul Metrics endpoints (`/v1/metrics/mrr`, `/arr`,
`/customer-count`, `/arpa`, `/ltv`). Data is cached for 10 minutes so fast rotation
barely costs any API calls.

## Requirements
- macOS with `python3` (standard library only)
- A ChartMogul API key: **Admin → API Keys**

## Installation

1. **Install SwiftBar**
   ```sh
   brew install --cask swiftbar
   ```
   On first launch, pick a **plugins folder**, e.g. `~/SwiftBar-Plugins`.

2. **Store the API key**
   ```sh
   mkdir -p ~/.config/revenue-stats-bar
   printf '%s' 'YOUR_CHARTMOGUL_API_KEY' > ~/.config/revenue-stats-bar/token
   chmod 600 ~/.config/revenue-stats-bar/token
   ```
   Alternatively, set the `CHARTMOGUL_API_KEY` environment variable.

3. **Symlink the plugin** (the repo stays the source of truth):
   ```sh
   chmod +x revenue.1m.py
   ln -s "$(pwd)/revenue.1m.py" ~/SwiftBar-Plugins/revenue.1m.py
   ```

4. Trigger **"Refresh all"** in SwiftBar.

## Configuration (top of `revenue.1m.py`)
- **Rotation speed:** the number in the filename, e.g. `revenue.2m.py` = advance every 2 minutes.
- **Which metrics rotate:** the `ROTATION` list (remove an entry to drop it from the bar).
- **Disable rotation:** `ROTATE = False` shows the first metric in `ROTATION`.
- **Cache duration:** `DATA_TTL_SECONDS` (default 600 = 10 minutes).
- **Currency symbol:** `CURRENCY_SYMBOL` (default `€`).

## Quick test without SwiftBar
```sh
CHARTMOGUL_API_KEY='YOUR_KEY' python3 revenue.1m.py
```
Run it a few times — the first line rotates through the metrics.
Without/with an invalid key it prints `⚠︎ …` instead of a traceback.

## Files
- `revenue.1m.py` — the SwiftBar plugin
- `config.example` — template for the token file
- `.gitignore`, `README.md`
- Runtime state: `~/.config/revenue-stats-bar/state.json` (cache + rotation index)
