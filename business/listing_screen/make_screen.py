"""Build a 3-page pre-offer deal screen (HTML and PDF) from a JSON of public listing numbers.

Usage: python3 -I make_screen.py input.json outdir
Everything computed here is derived or assumed and is labelled that way on the page.
The call (proceed / pass) is my simple rule, shown on the page; it is not advice.
"""
import json, os, subprocess, sys
import numpy as np

inp = json.load(open(sys.argv[1]))
out = sys.argv[2]
os.makedirs(out, exist_ok=True)

pm = inp["monthly_profit"]; margin = inp["margin"]; views = inp["page_views"]
pmult = inp["profit_multiple"]; rmult = inp["revenue_multiple"]
rev_m = pm / margin; cost_m = rev_m - pm
ann_profit = pm * 12; ann_rev = rev_m * 12
price = round((ann_profit * pmult + ann_rev * rmult) / 2, -2)
rev_1000 = rev_m / views * 1000
bid_lo = round(ann_profit * 1.6, -2); bid_hi = round(ann_profit * 2.0, -2)

scen = []
for name, d in [("Flat", 0.0), ("Revenue -20%", -0.2), ("Revenue -40%", -0.4), ("Revenue -60%", -0.6)]:
    p = rev_m * (1 + d) - cost_m
    scen.append((name, p, price / (p * 12) if p > 0 else float("inf")))

# Monte Carlo (assumed ranges, shown on the page)
rng = np.random.default_rng(1)
N = 20000
d12 = rng.triangular(-0.60, -0.10, 0.30, N)
extra = rng.triangular(0, 150, 500, N)
lose = rng.random(N) < 0.15
lm = rng.integers(1, 25, N)
cum = np.zeros(N); cum24 = np.zeros(N)
for t in range(1, 37):
    mult = 1 + d12 * min(t / 12, 1)
    mult = np.where(lose & (t >= lm), mult * 0.5, mult)
    cum += rev_m * mult - cost_m - extra
    if t == 24: cum24 = cum.copy()
p36 = float((cum >= price).mean()); p24 = float((cum24 >= price).mean())

pay20 = scen[1][2]
call = "Proceed with conditions" if pay20 <= 3.5 else "Pass unless the price falls"
money = lambda x: "${:,.0f}".format(x)

flags = inp.get("flags") or [
    {"risk": "Search traffic falls", "chance": "check", "why": "Check Search Console for 24 months"},
    {"risk": "Main income source leaves", "chance": "check", "why": "Ask for revenue by partner or customer"},
    {"risk": "Owner or writer leaves", "chance": "check", "why": "Ask who runs it day to day"},
]
questions = inp.get("questions") or [
    "Revenue by source for the last 24 months, with contracts.",
    "Traffic or sales by month for 24 months, with the date of any big drop.",
    "Top 20 pages, products or customers by revenue.",
    "Payout statements or bank deposits that match the stated profit.",
    "What the monthly costs contain and who is paid out of them.",
    "Can the main customers or partners move to a new owner, and on what terms?",
    "Any inconsistency in the listing (age, traffic, profit) and the explanation.",
    "Any penalties, disputes, refunds or chargebacks in the last 24 months.",
    "Who does the work, how long, and will they stay at least six months.",
    "Any licences, consents or platform terms the business depends on.",
]
notes = inp.get("notes", [])
rows = "".join(
    f'<tr><td>{n}</td><td class="n">{money(p)}</td><td class="n">{("%.1f" % y) if y != float("inf") else "never"}</td></tr>'
    for n, p, y in scen)
flag_rows = "".join(f'<tr><td>{f["risk"]}</td><td class="n">{f["chance"]}</td><td>{f["why"]}</td></tr>' for f in flags)
q_items = "".join(f"<li>{q}</li>" for q in questions)
note_items = "".join(f"<li>{n}</li>" for n in notes)

html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Pre-offer deal screen</title>
<style>
@page {{ size: A4; margin: 16mm 15mm; }}
body {{ font: 10.5pt/1.45 "Helvetica Neue", Arial, sans-serif; color: #11161d; }}
h1 {{ font: 600 20pt Georgia, serif; margin: 0 0 2px; }}
h2 {{ font: 600 12.5pt Georgia, serif; margin: 16px 0 6px; border-bottom: 1px solid #c9d0d9; padding-bottom: 3px; }}
.kick {{ font: 9pt monospace; letter-spacing: .08em; text-transform: uppercase; color: #4a5360; }}
.meta {{ color: #4a5360; font-size: 9.5pt; margin-bottom: 8px; }}
.box {{ border: 1.5px solid #0f2a4a; padding: 9px 12px; margin: 10px 0; background: #f3f6fa; }}
table {{ border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: 6px 0; }}
th {{ text-align: left; font: 8.5pt monospace; text-transform: uppercase; color: #4a5360; border-bottom: 1px solid #c9d0d9; padding: 4px 6px; }}
td {{ border-bottom: 1px solid #e3e7ec; padding: 4px 6px; vertical-align: top; }}
td.n {{ text-align: right; white-space: nowrap; }}
.tag {{ font: 8pt monospace; text-transform: uppercase; padding: 1px 5px; border: 1px solid #9aa3af; }}
ol, ul {{ margin: 4px 0 4px 18px; padding: 0; }} li {{ margin-bottom: 3px; }}
.pb {{ page-break-after: always; }} .small {{ font-size: 8.8pt; color: #4a5360; }}
</style></head><body>
<div class="kick">Pre-offer deal screen</div>
<h1>{inp["title"]}</h1>
<div class="meta">Subject: {inp["subject"]} · Screen date: {inp["date"]} · Basis: the public listing only. {inp.get("price_note", "The sold or asking price may be hidden; the price below is an estimate.")}</div>
<div class="box"><b>Call: {call.lower()}.</b> Suggested bid <b>{money(bid_lo)} to {money(bid_hi)}</b> (1.6x to 2.0x annual profit). Walk away above about <b>{money(price)}</b>. My rule: proceed if payback with revenue down 20% is 3.5 years or less.</div>
<h2>1. The numbers at a glance</h2>
<table><tr><th>Item</th><th class="n">Value</th><th>Status</th></tr>
<tr><td>Monthly profit</td><td class="n">{money(pm)}</td><td><span class="tag">copied</span> listing</td></tr>
<tr><td>Profit margin</td><td class="n">{margin*100:.0f}%</td><td><span class="tag">copied</span></td></tr>
<tr><td>Monthly page views or orders</td><td class="n">{views:,}</td><td><span class="tag">copied</span></td></tr>
<tr><td>Profit / revenue multiple</td><td class="n">{pmult}x / {rmult}x</td><td><span class="tag">copied</span></td></tr>
<tr><td>Monthly revenue, monthly costs</td><td class="n">{money(rev_m)} / {money(cost_m)}</td><td><span class="tag">derived</span> profit / margin</td></tr>
<tr><td>Annual profit</td><td class="n">{money(ann_profit)}</td><td><span class="tag">derived</span></td></tr>
<tr><td>Revenue per 1,000 views</td><td class="n">{money(rev_1000)}</td><td><span class="tag">derived</span></td></tr>
<tr><td>Estimated price</td><td class="n">about {money(price)}</td><td><span class="tag">assumed</span> average of profit and revenue multiples</td></tr>
</table>
<h2>2. What drives the call</h2><ul>{note_items}</ul>
<div class="pb"></div>
<h2>2b. Payback under falling revenue (costs held at {money(cost_m)} a month)</h2>
<table><tr><th>Scenario</th><th class="n">Profit / month</th><th class="n">Payback (years)</th></tr>{rows}</table>
<p class="small">Simulation (20,000 runs, assumed ranges: revenue change -60% to +30%, a 15% chance the main income source leaves, $0 to $500 a month of added cost): price recovered within 36 months in about {p36*100:.0f}% of runs and within 24 months in about {p24*100:.0f}%. Ranges are assumptions, not data.</p>
<h2>Red flags</h2><table><tr><th>Risk</th><th class="n">Chance (my judgment)</th><th>Why</th></tr>{flag_rows}</table>
<div class="pb"></div>
<h2>3. Questions for the seller</h2><ol>{q_items}</ol>
<h2>4. What this screen is not</h2>
<p class="small">This is a short screen for discussion. It is not a quality-of-earnings report, no CPA signs it, and it is not legal, tax or investment advice. It uses only the public listing, did not contact the seller, and could not verify any figure against bank statements. The price and all chances are estimates. Prepared by Syed Shafai, syed.shafai@gmail.com.</p>
</body></html>"""
hp = os.path.join(out, "screen.html"); open(hp, "w").write(html)
pdf = os.path.join(out, "screen.pdf")
js = f"const {{chromium}}=require('playwright');(async()=>{{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://{os.path.abspath(hp)}');await p.pdf({{path:'{os.path.abspath(pdf)}',format:'A4',printBackground:true}});await b.close();}})();"
root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
subprocess.run(["node", "-e", js], env={**os.environ, "NODE_PATH": root}, check=True)
print(json.dumps({"price": price, "bid": [bid_lo, bid_hi], "call": call, "payback_flat": round(scen[0][2], 1), "payback_-20": round(pay20, 1), "p36": round(p36, 3), "pdf": pdf}))
