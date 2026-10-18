# Upstox data setup (start here)

You only need: a free Upstox account, a developer app, and the free **Analytics Token** (read-only, valid 1 year).
Nothing here can place an order.

1. **Install** Python 3.10+ (python.org) and Git.
2. **Get the code**
   ```bash
   git clone -b claude/zerodha-api-live-data-6tf1kn https://github.com/TechSavvysyedshafai/callable-demo-mcp
   cd callable-demo-mcp
   pip install numpy pandas
   ```
3. **Put your token in the environment** (never paste it into chat or into a file in this folder).
   Mac / Linux:  `export UPSTOX_ANALYTICS_TOKEN='paste-token-here'`
   Windows PowerShell:  `$env:UPSTOX_ANALYTICS_TOKEN="paste-token-here"`
   (This lasts only for that terminal window. Set it again in each new window.)
4. **Check it works**  `python research/upstox/check_setup.py`
   You should see `[ OK ]` lines. You may paste that output to Claude: it contains no secrets.
5. **Download NIFTY history** (free)  `python research/upstox/fetch_upstox.py`
6. **Expired option history** needs the **Upstox Plus** plan. If check_setup shows a `[PLUS]` line, that part is locked; the rest still works.
   Upgrade in the Upstox app ("Get Plus", top-right). Then: `python research/upstox/download_expired_options.py`
   (Upstox only keeps about 6 months of expired expiries, so run it regularly.)
7. **Run the tests on real data**
   `python research/scalp/options/evaluate_opt.py --underlying NIFTY --runs 200`
   `python research/scalp/evaluate.py --runs 200`
   Read the `verdict`. FAIL is the normal result; PASS still needs weeks of paper trading before any real money.

Offline self-test (no token needed): `python research/upstox/tests/test_upstox_parse.py`
Status: these scripts follow Upstox's published API formats but have not been run against the live service.

## Easiest: Google Colab (no install)
Open `colab_upstox.ipynb` in Google Colab (File > Open notebook > GitHub tab, repo `TechSavvysyedshafai/callable-demo-mcp`, branch
`claude/zerodha-api-live-data-6tf1kn`), add the secret `UPSTOX_ANALYTICS_TOKEN` (key icon), then Runtime > Run all.
