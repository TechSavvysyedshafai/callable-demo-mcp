"""Build the sample buyer-side listing review (East Insurance Group, Flippa #11356430).

Everything on the page comes from the public listing page (read 30 Oct 2026) or is
derived from it here. Assumptions in the Monte Carlo are labelled as mine.
Run: python3 -I build.py   -> writes report.html and results.json
"""
import json
import numpy as np

# ---------------- listing facts (public page) ----------------
PROFIT_M = 1539          # USD per month, listing
MARGIN = 0.94            # listing
PV_M = 2573              # page views per month, listing
PROFIT_MULT = 2.3        # listing
REV_MULT = 2.2           # listing
AGE_YEARS = 11           # listing field (text says "over seven years")

# ---------------- derived ----------------
rev_m = PROFIT_M / MARGIN                   # revenue per month
cost_m = rev_m - PROFIT_M                   # costs per month
ann_profit = PROFIT_M * 12
ann_rev = rev_m * 12
price_from_profit = ann_profit * PROFIT_MULT
price_from_rev = ann_rev * REV_MULT
price = round((price_from_profit + price_from_rev) / 2, -2)   # about 42.9k
rev_per_view = rev_m / PV_M
rev_per_1000 = rev_per_view * 1000

# deterministic scenarios: revenue falls by d, costs stay fixed
scen = [("Flat", 0.0), ("Revenue -20%", -0.2), ("Revenue -40%", -0.4), ("Revenue -60%", -0.6)]
scen_rows = []
for name, d in scen:
    p = rev_m * (1 + d) - cost_m
    scen_rows.append(dict(name=name, d=d, profit_m=p, payback=price / (p * 12)))

# ---------------- Monte Carlo (assumptions are mine) ----------------
rng = np.random.default_rng(20261030)
N = 20000
H = 36
d12 = rng.triangular(-0.60, -0.10, 0.30, N)          # revenue change reached by month 12
extra = rng.triangular(0, 150, 500, N)               # buyer's extra monthly cost (writer, tools)
lose_partner = rng.random(N) < 0.15                  # main partner/lead buyer leaves
lose_month = rng.integers(1, 25, N)
cum = np.zeros(N)
cum24 = np.zeros(N)
for t in range(1, H + 1):
    ramp = np.minimum(t / 12.0, 1.0)
    mult = 1 + d12 * ramp
    mult = np.where(lose_partner & (t >= lose_month), mult * 0.5, mult)
    prof = rev_m * mult - cost_m - extra
    cum += prof
    if t == 24:
        cum24 = cum.copy()
net36 = cum - price
mc = dict(
    n=N,
    p_recoup_24=float((cum24 >= price).mean()),
    p_recoup_36=float((cum >= price).mean()),
    p_traffic_down_20=float((d12 < -0.2).mean()),
    median_net36=float(np.median(net36)),
    p5=float(np.percentile(net36, 5)),
    p95=float(np.percentile(net36, 95)),
    p_lose_half=float((cum < price * 0.5).mean()),
)
res = dict(price=price, rev_m=rev_m, cost_m=cost_m, ann_profit=ann_profit, rev_per_view=rev_per_view,
           rev_per_1000=rev_per_1000, scen=scen_rows, mc=mc,
           price_from_profit=price_from_profit, price_from_rev=price_from_rev)
json.dump(res, open("results.json", "w"), indent=1)

# fair-value cross-checks
bid_lo = round(ann_profit * 1.6, -2)
bid_hi = round(ann_profit * 2.0, -2)

# ---------------- svg helpers ----------------
def money(x):
    return "${:,.0f}".format(x)

def svg_multiples():
    rows = [("East Insurance Group", 2.3, "sold", "Sold"),
            ("mysupermarketcompare.com", 2.9, "ask", "Asking"),
            ("Pureinsure", 0.3, "ask", "Asking"),
            ("Flippa all-category average", 3.03, "bench", "H1 2023 report")]
    W, rowh, left, right = 640, 44, 200, 130
    H_ = 20 + rowh * len(rows) + 34
    xmax = 3.5
    sx = lambda v: left + (W - left - right) * v / xmax
    o = [f'<svg viewBox="0 0 {W} {H_}" role="img" aria-label="Profit multiples of the sold listing against three comparisons">']
    for g in range(0, 4):
        x = sx(g)
        o.append(f'<line x1="{x}" y1="10" x2="{x}" y2="{10 + rowh * len(rows)}" class="grid"/>')
        o.append(f'<text x="{x}" y="{10 + rowh * len(rows) + 18}" class="axis" text-anchor="middle">{g}x</text>')
    for i, (lab, v, kind, tag) in enumerate(rows):
        y = 10 + i * rowh
        o.append(f'<text x="{left - 10}" y="{y + 26}" class="lab" text-anchor="end">{lab}</text>')
        w = sx(v) - left
        cls = {"sold": "bar-a", "ask": "bar-b", "bench": "bar-n"}[kind]
        o.append(f'<g><title>{lab}: {v}x profit multiple ({tag})</title>'
                 f'<path d="M{left},{y + 8} h{w - 4} a4,4 0 0 1 4,4 v12 a4,4 0 0 1 -4,4 h{-(w - 4)} z" class="{cls}"/></g>')
        o.append(f'<text x="{sx(v) + 8}" y="{y + 26}" class="val">{v}x <tspan class="tag">{tag}</tspan></text>')
    o.append('</svg>')
    return "".join(o)

def svg_lines():
    W, Hh, L, R, T, B = 640, 300, 56, 120, 14, 36
    months = 36
    ymax = 70000
    sx = lambda m: L + (W - L - R) * m / months
    sy = lambda v: T + (Hh - T - B) * (1 - v / ymax)
    o = [f'<svg viewBox="0 0 {W} {Hh}" role="img" aria-label="Cumulative profit by scenario against the estimated price">']
    for v in range(0, ymax + 1, 10000):
        o.append(f'<line x1="{L}" y1="{sy(v)}" x2="{W - R}" y2="{sy(v)}" class="grid"/>')
        o.append(f'<text x="{L - 8}" y="{sy(v) + 4}" class="axis" text-anchor="end">${v // 1000}k</text>')
    for m in (0, 12, 24, 36):
        o.append(f'<text x="{sx(m)}" y="{Hh - 12}" class="axis" text-anchor="middle">{"Month " if m == 0 else ""}{m}</text>')
    o.append(f'<line x1="{L}" y1="{sy(price)}" x2="{W - R}" y2="{sy(price)}" class="price"/>')
    o.append(f'<text x="{L + 8}" y="{sy(price) - 8}" class="val">Estimated price {money(price)}</text>')
    cls = ["ln-1", "ln-2", "ln-3", "ln-4"]
    for k, r in enumerate(scen_rows):
        pts = f'{sx(0)},{sy(0)} {sx(months)},{sy(r["profit_m"] * months)}'
        o.append(f'<g><title>{r["name"]}: {money(r["profit_m"])} a month, payback {r["payback"]:.1f} years</title>'
                 f'<polyline points="{pts}" class="{cls[k]}" fill="none"/></g>')
        ye = sy(r["profit_m"] * months)
        o.append(f'<circle cx="{sx(months)}" cy="{ye}" r="4" class="dot {cls[k]}"/>')
        o.append(f'<text x="{W - R + 8}" y="{ye + 4 + (10 if k == 3 else 0)}" class="lab">{r["name"]}</text>')
    o.append('</svg>')
    return "".join(o)

def svg_hist():
    bins = np.arange(-40000, 30001, 10000)
    clipped = np.clip(net36, bins[0] + 1, bins[-1] - 1)
    counts, _ = np.histogram(clipped, bins=bins)
    share = counts / N
    W, Hh, L, R, T, B = 640, 290, 52, 20, 18, 56
    bw = (W - L - R) / len(share)
    ymax = float(np.ceil(share.max() * 10) / 10)
    sy = lambda v: T + (Hh - T - B) * (1 - v / ymax)
    o = [f'<svg viewBox="0 0 {W} {Hh}" role="img" aria-label="Distribution of net result after 36 months across 20,000 simulated runs">']
    for v in [k / 10 for k in range(0, int(round(ymax * 10)) + 1)]:
        o.append(f'<line x1="{L}" y1="{sy(v)}" x2="{W - R}" y2="{sy(v)}" class="grid"/>')
        o.append(f'<text x="{L - 8}" y="{sy(v) + 4}" class="axis" text-anchor="end">{int(v * 100)}%</text>')
    for i, s in enumerate(share):
        lo, hi = bins[i], bins[i + 1]
        x = L + i * bw + 1
        h = sy(0) - sy(s)
        cls = "bar-a" if lo >= 0 else "bar-b"
        o.append(f'<g><title>Net result {lo // 1000}k to {hi // 1000}k: {s * 100:.1f}% of runs</title>'
                 f'<rect x="{x}" y="{sy(s)}" width="{bw - 2}" height="{max(h, 0)}" rx="2" class="{cls}"/></g>')
    xz = L + (0 - bins[0]) / 10000 * bw
    o.append(f'<line x1="{xz}" y1="{T}" x2="{xz}" y2="{sy(0)}" class="zero"/>')
    for k in range(0, len(bins)):
        o.append(f'<text x="{L + k * bw}" y="{Hh - 32}" class="axis" text-anchor="middle">{bins[k] // 1000}k</text>')
    o.append(f'<text x="{(L + W - R) / 2}" y="{Hh - 10}" class="axis" text-anchor="middle">Net result after 36 months, profit earned minus price paid (USD)</text>')
    o.append(f'<text x="{xz - 8}" y="{T + 12}" class="lab" text-anchor="end">Loss</text>')
    o.append(f'<text x="{xz + 8}" y="{T + 12}" class="lab">Gain</text>')
    o.append('</svg>')
    return "".join(o)

def bar(v):
    return f'<div class="meter" role="img" aria-label="{v} out of 100"><span style="width:{v}%"></span></div>'

scores = [("Financial quality", 70, "94% margin, vetted revenue and expenses, Google Analytics connected"),
          ("Traffic durability", 35, "Small audience, organic search only, drop after a Google update"),
          ("Transferability", 70, "WordPress, writer stays, 90 days of migration help"),
          ("Valuation", 60, "2.3x profit is in range, but the sold price is hidden"),
          ("Documentation", 55, "Public page is thin; the detail sits behind a login")]
overall = round(sum(s for _, s, _ in scores) / len(scores))

html = f"""<title>Listing Review Sample</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: research-note format. Masthead and verdict first, then evidence in numbered-by-topic sections, each ending in a one-line takeaway. */
:root {{
  --bg: #f6f7f9; --surface: #ffffff; --ink: #11161d; --ink-2: #4a5360; --ink-3: #7a8491;
  --rule: #d9dee5; --navy: #0f2a4a; --navy-ink: #ffffff;
  --series-1: #2a78d6; --series-2: #eb6834; --series-n: #9aa3af;
  --good: #1f7a4d; --good-bg: #e3f3ea; --warn: #8a5a00; --warn-bg: #fbf0d9; --bad: #a3262a; --bad-bg: #fbe4e4;
  --grid: #e3e7ec; --price: #11161d;
  --serif: "Source Serif 4", Georgia, "Times New Roman", serif;
  --sans: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #0d1117; --surface: #151b23; --ink: #e8ecf1; --ink-2: #b0b8c4; --ink-3: #8a94a2;
    --rule: #2a323d; --navy: #0b1b30; --navy-ink: #e8ecf1;
    --series-1: #3987e5; --series-2: #d95926; --series-n: #6b7480;
    --good: #5fcf98; --good-bg: #12301f; --warn: #e6b34d; --warn-bg: #33270b; --bad: #f08a8c; --bad-bg: #3a1618;
    --grid: #232b35; --price: #e8ecf1; color-scheme: dark;
  }}
}}
:root[data-theme="dark"] {{
  --bg: #0d1117; --surface: #151b23; --ink: #e8ecf1; --ink-2: #b0b8c4; --ink-3: #8a94a2;
  --rule: #2a323d; --navy: #0b1b30; --navy-ink: #e8ecf1;
  --series-1: #3987e5; --series-2: #d95926; --series-n: #6b7480;
  --good: #5fcf98; --good-bg: #12301f; --warn: #e6b34d; --warn-bg: #33270b; --bad: #f08a8c; --bad-bg: #3a1618;
  --grid: #232b35; --price: #e8ecf1; color-scheme: dark;
}}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--ink); font-family: var(--sans); font-size: 15px; line-height: 1.55;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 0 48px; }}
.wrap {{ max-width: 980px; margin: 0 auto; }}
.masthead {{ background: var(--navy); color: var(--navy-ink); margin: 0 calc(-1 * max(16px, env(safe-area-inset-left, 0px))); padding: 28px max(16px, env(safe-area-inset-left, 0px)) 30px; }}
.masthead .in {{ max-width: 980px; margin: 0 auto; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 24px; align-items: end; }}
.kicker {{ font: 500 11px/1 var(--mono); letter-spacing: .14em; text-transform: uppercase; opacity: .8; margin: 0 0 14px; }}
h1 {{ font: 600 clamp(26px, 5vw, 40px)/1.12 var(--serif); margin: 0 0 10px; text-wrap: balance; }}
.sub {{ margin: 0; max-width: 60ch; opacity: .88; }}
.ratingbox {{ border: 1px solid rgba(255,255,255,.35); padding: 14px 18px; min-width: 190px; }}
.ratingbox .big {{ font: 600 40px/1 var(--serif); }}
.ratingbox .big small {{ font: 400 14px var(--sans); opacity: .75; }}
.ratingbox .what {{ font: 500 12px/1.3 var(--mono); letter-spacing: .06em; text-transform: uppercase; margin-top: 8px; }}
.meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px 24px; padding: 16px 0; border-bottom: 1px solid var(--rule); }}
.meta div {{ min-width: 0; }}
.meta dt {{ font: 500 10.5px/1 var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--ink-3); margin-bottom: 4px; }}
.meta dd {{ margin: 0; font-weight: 500; overflow-wrap: anywhere; }}
.banner {{ margin: 18px 0 0; padding: 10px 14px; border: 1px solid var(--rule); background: var(--surface); color: var(--ink-2); font-size: 13px; }}
h2 {{ font: 600 22px/1.2 var(--serif); margin: 40px 0 6px; text-wrap: balance; }}
h2 + .take {{ margin-top: 0; }}
.take {{ color: var(--ink-2); margin: 0 0 16px; max-width: 75ch; }}
h3 {{ font: 600 13px/1.3 var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--ink-2); margin: 24px 0 8px; }}
p {{ margin: 0 0 12px; max-width: 78ch; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 16px 0 4px; }}
.tile {{ background: var(--surface); border: 1px solid var(--rule); padding: 14px 14px 12px; min-width: 0; }}
.tile .k {{ font: 500 10.5px/1.2 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--ink-3); }}
.tile .v {{ font: 600 26px/1.15 var(--serif); margin-top: 6px; font-variant-numeric: tabular-nums; }}
.tile .n {{ font-size: 12px; color: var(--ink-2); margin-top: 2px; }}
.panel {{ background: var(--surface); border: 1px solid var(--rule); padding: 16px 16px 12px; }}
.panel .ttl {{ font: 600 14px/1.3 var(--sans); margin: 0 0 2px; }}
.panel .cap {{ font-size: 12.5px; color: var(--ink-2); margin: 0 0 8px; }}
.panel .src {{ font: 400 11.5px/1.4 var(--mono); color: var(--ink-3); margin: 8px 0 0; }}
.chart {{ overflow-x: auto; }}
.chart svg {{ display: block; width: 100%; min-width: 560px; height: auto; }}
svg text {{ font-family: var(--sans); fill: var(--ink); }}
svg .axis {{ font-size: 11.5px; fill: var(--ink-3); font-family: var(--mono); }}
svg .lab {{ font-size: 12.5px; fill: var(--ink); }}
svg .val {{ font-size: 12.5px; fill: var(--ink); font-weight: 600; font-variant-numeric: tabular-nums; }}
svg .tag {{ font-weight: 400; fill: var(--ink-2); font-size: 11.5px; }}
svg .grid {{ stroke: var(--grid); stroke-width: 1; }}
svg .bar-a {{ fill: var(--series-1); }} svg .bar-b {{ fill: var(--series-2); }} svg .bar-n {{ fill: var(--series-n); }}
svg .price {{ stroke: var(--price); stroke-width: 1.5; stroke-dasharray: 5 4; }}
svg .zero {{ stroke: var(--ink); stroke-width: 1.5; }}
svg polyline {{ stroke-width: 2; stroke-linecap: round; }}
svg .ln-1 {{ stroke: var(--series-1); }} svg .ln-2 {{ stroke: var(--series-n); }} svg .ln-3 {{ stroke: var(--series-2); }} svg .ln-4 {{ stroke: var(--bad); }}
svg circle.ln-1 {{ fill: var(--series-1); }} svg circle.ln-2 {{ fill: var(--series-n); }} svg circle.ln-3 {{ fill: var(--series-2); }} svg circle.ln-4 {{ fill: var(--bad); }}
svg circle.dot {{ stroke: var(--surface); stroke-width: 2; }}
.tablewrap {{ overflow-x: auto; background: var(--surface); border: 1px solid var(--rule); }}
table {{ border-collapse: collapse; width: 100%; font-size: 13.5px; min-width: 560px; }}
th {{ text-align: left; font: 500 10.5px/1.2 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--ink-3); padding: 10px 12px; border-bottom: 1px solid var(--rule); background: var(--surface); }}
td {{ padding: 10px 12px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
tr:last-child td {{ border-bottom: 0; }}
td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; font-family: var(--mono); white-space: nowrap; }}
.pill {{ display: inline-block; font: 500 11px/1 var(--mono); letter-spacing: .04em; padding: 4px 7px; text-transform: uppercase; white-space: nowrap; }}
.p-good {{ background: var(--good-bg); color: var(--good); }} .p-warn {{ background: var(--warn-bg); color: var(--warn); }} .p-bad {{ background: var(--bad-bg); color: var(--bad); }}
.meter {{ background: var(--grid); height: 8px; border-radius: 4px; min-width: 90px; }}
.meter span {{ display: block; height: 100%; background: var(--series-1); border-radius: 4px; }}
.two {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }}
.two > * {{ min-width: 0; }}
ul.clean {{ margin: 0; padding-left: 18px; }} ul.clean li {{ margin-bottom: 6px; max-width: 78ch; }}
.verdict {{ background: var(--surface); border: 1px solid var(--rule); border-left: 4px solid var(--series-1); padding: 16px 18px; }}
.verdict p:last-child {{ margin-bottom: 0; }}
.foot {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--rule); font-size: 12px; color: var(--ink-3); }}
.foot p {{ max-width: 90ch; }}
a {{ color: var(--series-1); }}
@media (max-width: 640px) {{ .masthead .in {{ grid-template-columns: 1fr; }} }}
</style>

<header class="masthead"><div class="in">
  <div>
    <p class="kicker">Buyer-side listing review &middot; sample report</p>
    <h1>East Insurance Group: a fair price for a fragile traffic base</h1>
    <p class="sub">Independent review of a sold US insurance-guides website, written from the buyer&rsquo;s side, using only the public listing page and public market data.</p>
  </div>
  <div class="ratingbox"><div class="big">{overall}<small> / 100</small></div><div class="what">Proceed with conditions</div></div>
</div></header>

<main class="wrap">
<dl class="meta">
  <div><dt>Subject</dt><dd>East Insurance Group</dd></div>
  <div><dt>Platform</dt><dd>Flippa listing 11356430 (sold)</dd></div>
  <div><dt>Model</dt><dd>Content / lead-gen site, WordPress</dd></div>
  <div><dt>Review date</dt><dd>30 Oct 2026</dd></div>
  <div><dt>Basis</dt><dd>Public page only, no seller access</dd></div>
</dl>
<p class="banner"><strong>Sample.</strong> This shows the format of a paid review. The sold price is hidden by Flippa, so the price below is my estimate. The seller and buyer were not contacted. Not investment advice. Not affiliated with Flippa.</p>

<h2>1. Summary</h2>
<p class="take">The numbers are good for a site this small. The risk sits in where the money comes from, not in the multiple.</p>
<div class="tiles">
  <div class="tile"><div class="k">Monthly profit</div><div class="v">{money(PROFIT_M)}</div><div class="n">94% margin, listing</div></div>
  <div class="tile"><div class="k">Profit multiple</div><div class="v">{PROFIT_MULT}x</div><div class="n">revenue multiple {REV_MULT}x</div></div>
  <div class="tile"><div class="k">Est. price</div><div class="v">{money(price)}</div><div class="n">my estimate, not disclosed</div></div>
  <div class="tile"><div class="k">Page views</div><div class="v">{PV_M:,}</div><div class="n">a month, mostly organic</div></div>
  <div class="tile"><div class="k">Revenue per 1,000 views</div><div class="v">{money(rev_per_1000)}</div><div class="n">far above display ads</div></div>
</div>
<ul class="clean" style="margin-top:16px">
  <li><strong>Price looks fair.</strong> At 2.3x annual profit ({money(ann_profit)}) the estimated price is {money(price)}. Flat profit pays it back in about {scen_rows[0]["payback"]:.1f} years.</li>
  <li><strong>Revenue per visitor is unusually high.</strong> About {money(rev_per_1000)} per 1,000 page views. Ad income pays a small fraction of that, so the income is almost certainly lead sales to a few insurance partners. That is a concentration risk.</li>
  <li><strong>Traffic is the weak point.</strong> The listing says a Google core update hurt the site. At {PV_M:,} views a month there is little buffer.</li>
  <li><strong>The simulation is mixed.</strong> In my 20,000-run model the buyer recovers the price within 36 months in {mc["p_recoup_36"]*100:.0f}% of runs and within 24 months in {mc["p_recoup_24"]*100:.0f}%.</li>
  <li><strong>Suggested bid:</strong> {money(bid_lo)} to {money(bid_hi)}, walk away above {money(price)}, and only after the checks in section 8.</li>
</ul>

<h2>2. What the listing says, and what it does not</h2>
<p class="take">Facts come from the public page. Anything marked derived is my arithmetic.</p>
<div class="tablewrap"><table>
<thead><tr><th>Item</th><th class="num">Value</th><th>Source</th><th>Status</th></tr></thead>
<tbody>
<tr><td>Monthly profit</td><td class="num">{money(PROFIT_M)}</td><td>Listing</td><td><span class="pill p-good">Vetted by Flippa</span></td></tr>
<tr><td>Profit margin</td><td class="num">94%</td><td>Listing</td><td><span class="pill p-good">Vetted by Flippa</span></td></tr>
<tr><td>Monthly revenue</td><td class="num">{money(rev_m)}</td><td>Derived: profit / margin</td><td><span class="pill p-warn">Derived</span></td></tr>
<tr><td>Monthly costs</td><td class="num">{money(cost_m)}</td><td>Derived: revenue - profit</td><td><span class="pill p-warn">Derived</span></td></tr>
<tr><td>Page views</td><td class="num">{PV_M:,} / mo</td><td>Listing</td><td><span class="pill p-good">Vetted by Flippa</span></td></tr>
<tr><td>Site age</td><td class="num">11 years</td><td>Listing field</td><td><span class="pill p-bad">Conflict</span> text says &ldquo;over seven years&rdquo;</td></tr>
<tr><td>Traffic source</td><td class="num">Organic search</td><td>Listing text</td><td><span class="pill p-warn">Unquantified</span></td></tr>
<tr><td>Google update impact</td><td class="num">&ldquo;Downturn&rdquo;</td><td>Listing text</td><td><span class="pill p-bad">Size unknown</span></td></tr>
<tr><td>Asking and sold price</td><td class="num">Hidden</td><td>Needs a free login</td><td><span class="pill p-bad">Not seen</span></td></tr>
<tr><td>Assets included</td><td class="num">Domain, content, social, writer</td><td>Listing text</td><td><span class="pill p-good">Stated</span></td></tr>
<tr><td>Seller support</td><td class="num">90 days</td><td>Listing text</td><td><span class="pill p-good">Stated</span></td></tr>
</tbody></table></div>
<p class="foot" style="border:0;margin-top:8px;padding:0">The listing carries Flippa&rsquo;s &ldquo;Vetted + Data Verified&rdquo; label covering revenue, primary expenses and traffic, with Google Analytics connected. That lowers the risk of invented figures. It does not say the income will continue.</p>

<h2>3. Valuation against comparisons</h2>
<p class="take">2.3x sits in the middle of what small sites fetch. The two live insurance listings show how wide the range is.</p>
<div class="panel">
  <p class="ttl">Profit multiple: sold listing against comparisons</p>
  <p class="cap">Sold, asking and benchmark figures are different things and are labelled as such.</p>
  <div class="chart">{svg_multiples()}</div>
  <p class="src">Source: Flippa listing pages and category page, read 30 Oct 2026; Flippa Insight Report Jan-Jun 2023 for the 3.03x average (old, all categories).</p>
</div>
<div class="tablewrap" style="margin-top:16px"><table>
<thead><tr><th>Comparison</th><th>What it is</th><th class="num">Profit / mo</th><th class="num">Price</th><th class="num">Multiple</th><th>Status</th></tr></thead>
<tbody>
<tr><td>East Insurance Group</td><td>US insurance guides, 11 yrs</td><td class="num">$1,539</td><td class="num">~{money(price)} est.</td><td class="num">2.3x</td><td><span class="pill p-good">Sold</span></td></tr>
<tr><td>mysupermarketcompare.com</td><td>UK insurance comparison, 1 yr</td><td class="num">$309</td><td class="num">$10,789</td><td class="num">2.9x</td><td><span class="pill p-warn">Asking</span></td></tr>
<tr><td>Pureinsure</td><td>Canada life-insurance leads, 6 yrs</td><td class="num">$987</td><td class="num">$3,500</td><td class="num">0.3x</td><td><span class="pill p-warn">Asking</span></td></tr>
<tr><td>investadvisors.org</td><td>Pakistan content site, 5 yrs</td><td class="num">$82</td><td class="num">$4,000</td><td class="num">n/a</td><td><span class="pill p-warn">Asking</span></td></tr>
</tbody></table></div>
<p style="margin-top:12px">Method check: profit x 12 x multiple reproduces the two asking prices within 1% ($10,753 against $10,789, $3,553 against $3,500). I apply the same method to the sold site, giving {money(price_from_profit)} on profit and {money(price_from_rev)} on revenue. I use the {money(price)} midpoint. Treat it as an estimate until the seller or Flippa confirms the figure.</p>
<p>Context from Flippa&rsquo;s H1 2026 report: top-quartile assets sold at 1.6x to 2.7x the category average, content sales fell 39%, and searches for &ldquo;recently sold&rdquo; rose 811%. Buyers now ask for proof before price. This site has partial proof and a visible weakness.</p>

<h2>4. Where the money comes from</h2>
<p class="take">{money(rev_per_1000)} per 1,000 views is not advertising income. That points to a handful of paying partners.</p>
<div class="two">
  <div class="panel"><p class="ttl">Unit economics (derived)</p>
    <div class="tablewrap" style="border:0"><table style="min-width:0">
    <tbody>
    <tr><td>Revenue per month</td><td class="num">{money(rev_m)}</td></tr>
    <tr><td>Revenue per page view</td><td class="num">${rev_per_view:.2f}</td></tr>
    <tr><td>Profit per page view</td><td class="num">${PROFIT_M/PV_M:.2f}</td></tr>
    <tr><td>Annual profit</td><td class="num">{money(ann_profit)}</td></tr>
    <tr><td>Annual revenue</td><td class="num">{money(ann_rev)}</td></tr>
    <tr><td>Monthly costs</td><td class="num">{money(cost_m)}</td></tr>
    </tbody></table></div>
  </div>
  <div class="panel"><p class="ttl">What it implies</p>
    <ul class="clean">
      <li>Display ads typically pay a few dollars to a few tens of dollars per 1,000 views (my general assumption, not verified for this site). Here it is about {money(rev_per_1000)}.</li>
      <li>So most income is probably lead-gen or referral fees from insurance partners.</li>
      <li>Costs of {money(cost_m)} a month leave no room for the freelance writer to be fully paid. The buyer should expect to add spend.</li>
      <li>A few large buyers of leads mean losing one could cut revenue by a large share.</li>
    </ul>
  </div>
</div>

<h2>5. Scenarios: how long to earn the price back</h2>
<p class="take">If revenue falls by 40%, payback stretches past four years.</p>
<div class="panel">
  <p class="ttl">Cumulative profit against the estimated price, by revenue scenario</p>
  <p class="cap">Costs held at {money(cost_m)} a month. The dashed line is the price. Where a line crosses it, the buyer is repaid.</p>
  <div class="chart">{svg_lines()}</div>
  <p class="src">Source: derived from the listing figures. Scenarios are my assumptions.</p>
</div>
<div class="tablewrap" style="margin-top:16px"><table>
<thead><tr><th>Scenario</th><th class="num">Profit / month</th><th class="num">Annual profit</th><th class="num">Payback (years)</th><th>Read</th></tr></thead>
<tbody>
""" + "".join(
    f'<tr><td>{r["name"]}</td><td class="num">{money(r["profit_m"])}</td><td class="num">{money(r["profit_m"]*12)}</td>'
    f'<td class="num">{r["payback"]:.1f}</td><td><span class="pill {"p-good" if r["payback"]<=3 else ("p-warn" if r["payback"]<=4.5 else "p-bad")}">{"Acceptable" if r["payback"]<=3 else ("Stretched" if r["payback"]<=4.5 else "Poor")}</span></td></tr>'
    for r in scen_rows) + f"""
</tbody></table></div>

<h2>6. Risk simulation</h2>
<p class="take">{mc["p_recoup_36"]*100:.0f}% of runs repay the price inside three years. About {mc["p_lose_half"]*100:.0f}% leave the buyer less than half repaid.</p>
<div class="panel">
  <p class="ttl">Net result after 36 months across {N:,} simulated runs</p>
  <p class="cap">Each bar is the share of runs ending in that range. Orange is a loss, blue is a gain.</p>
  <div class="chart">{svg_hist()}</div>
  <p class="src">Source: my Monte Carlo. All inputs below are my assumptions, not data.</p>
</div>
<div class="two" style="margin-top:16px">
  <div class="panel"><p class="ttl">Assumptions (mine)</p>
    <ul class="clean">
      <li>Revenue change reached by month 12: between -60% and +30%, most likely -10% (triangular).</li>
      <li>A 15% chance the main partner leaves in months 1 to 24, halving revenue from then on.</li>
      <li>Buyer adds $0 to $500 a month of cost, most likely $150 (writer, tools).</li>
      <li>Price {money(price)}; base revenue {money(rev_m)}; base costs {money(cost_m)} a month.</li>
    </ul>
  </div>
  <div class="panel"><p class="ttl">Results</p>
    <div class="tablewrap" style="border:0"><table style="min-width:0"><tbody>
    <tr><td>Price recovered within 24 months</td><td class="num">{mc["p_recoup_24"]*100:.0f}%</td></tr>
    <tr><td>Price recovered within 36 months</td><td class="num">{mc["p_recoup_36"]*100:.0f}%</td></tr>
    <tr><td>Revenue down more than 20% after a year</td><td class="num">{mc["p_traffic_down_20"]*100:.0f}%</td></tr>
    <tr><td>Median net result at 36 months</td><td class="num">{money(mc["median_net36"])}</td></tr>
    <tr><td>5th to 95th percentile</td><td class="num">{money(mc["p5"])} to {money(mc["p95"])}</td></tr>
    </tbody></table></div>
  </div>
</div>

<h2>7. Risk register</h2>
<p class="take">Probabilities are my judgment for the 12 months after purchase.</p>
<div class="tablewrap"><table>
<thead><tr><th>Risk</th><th>Evidence</th><th class="num">Chance</th><th>Impact</th><th>What to do</th></tr></thead>
<tbody>
<tr><td>Search traffic falls again</td><td>Listing admits a Google update hurt it; one traffic source</td><td class="num">{mc["p_traffic_down_20"]*100:.0f}%</td><td><span class="pill p-bad">High</span></td><td>Ask for 24 months of Search Console data; price in a fall</td></tr>
<tr><td>Main lead partner leaves</td><td>Revenue per view implies few payers</td><td class="num">15&ndash;25%</td><td><span class="pill p-bad">High</span></td><td>Ask for revenue by partner and contract terms</td></tr>
<tr><td>AI search takes clicks</td><td>Insurance guides are easy for AI answers to summarise</td><td class="num">40%</td><td><span class="pill p-warn">Medium</span></td><td>Add local and quote-focused pages that AI summaries can&rsquo;t replace</td></tr>
<tr><td>Writer leaves</td><td>One freelancer carries the content</td><td class="num">30%</td><td><span class="pill p-warn">Medium</span></td><td>Get a written handover and a second writer</td></tr>
<tr><td>Figures overstated</td><td>Flippa vetted revenue, expenses and traffic</td><td class="num">10%</td><td><span class="pill p-warn">Medium</span></td><td>Ask for payout statements and bank proof</td></tr>
<tr><td>Age and history unclear</td><td>11 years in the field, &ldquo;over seven&rdquo; in the text</td><td class="num">n/a</td><td><span class="pill p-warn">Medium</span></td><td>Check domain history and past penalties</td></tr>
<tr><td>Insurance lead rules</td><td>US lead sales to insurers can need licences and consent records</td><td class="num">15%</td><td><span class="pill p-warn">Medium</span></td><td>Ask a US lawyer which state rules apply (not checked here)</td></tr>
<tr><td>Transfer problems</td><td>WordPress, social accounts, partner logins</td><td class="num">10%</td><td><span class="pill p-good">Low</span></td><td>Use escrow; stage the transfer; keep 90 days of support</td></tr>
</tbody></table></div>

<h2>8. Questions to ask before bidding</h2>
<p class="take">Ten checks, in the order they would change the price.</p>
<div class="panel"><ol class="clean">
  <li>Revenue by partner for the last 24 months, and the contracts behind each.</li>
  <li>Google Search Console clicks and impressions for 24 months, with the date of the update.</li>
  <li>Top 20 pages by traffic and by revenue; how many carry the income.</li>
  <li>Payout statements and bank deposits that match the stated profit.</li>
  <li>What the {money(cost_m)} of monthly costs contain; is the writer fully paid out of it.</li>
  <li>Whether partners can be moved to the new owner and on what terms.</li>
  <li>Why the site age differs between the field and the text.</li>
  <li>Any manual penalties, link purchases or paid-link history.</li>
  <li>What the writer is paid, how long they have worked on it, and whether they agree to stay.</li>
  <li>Any consent, licence or disclosure language on the lead forms.</li>
</ol></div>

<h2>9. Score and verdict</h2>
<p class="take">Overall {overall} out of 100: worth bidding, at a lower price, with conditions.</p>
<div class="tablewrap"><table>
<thead><tr><th>Area</th><th class="num">Score</th><th style="min-width:110px"></th><th>Why</th></tr></thead>
<tbody>
""" + "".join(f'<tr><td>{a}</td><td class="num">{s}</td><td>{bar(s)}</td><td>{w}</td></tr>' for a, s, w in scores) + f"""
</tbody></table></div>
<div class="verdict" style="margin-top:16px">
  <p><strong>Verdict: proceed with conditions.</strong> I would bid {money(bid_lo)} to {money(bid_hi)}, which is 1.6x to 2.0x annual profit, and walk away above {money(price)}.</p>
  <p>Conditions: revenue by partner shows no single payer above about 40% (my threshold); Search Console shows traffic stable for six months; payouts match the stated profit; the writer agrees to stay for six months.</p>
  <p>If two of the four conditions fail, pass. At that point the multiple no longer compensates for the risk.</p>
</div>

<footer class="foot">
  <p><strong>Sources.</strong> Flippa listing 11356430 and the Flippa insurance category page, both read 30 Oct 2026; Flippa &ldquo;Digital M&amp;A Insights Report H1 2026&rdquo; (29 Jul 2026); Flippa Insight Report Jan-Jun 2023.</p>
  <p><strong>Verified vs assumed.</strong> Verified: figures copied from the public pages. Derived: revenue, costs, per-view figures, payback, estimated price. Assumed by me: scenarios, simulation inputs, risk percentages, scores, the bid range. Not seen: the sold price, traffic detail, financial statements, partner list.</p>
  <p><strong>Limits.</strong> One public page cannot show whether income will continue. This is an opinion for discussion with the buyer&rsquo;s own advisers. It is not legal, tax or investment advice. Prepared by Syed Shafai as a sample of a paid buyer-side review.</p>
</footer>
</main>
"""
open("report.html", "w").write(html)
print("price", price, "overall", overall)
print(json.dumps(mc, indent=1))
for r in scen_rows:
    print(r)
