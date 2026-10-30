"""Simple UK small-development deal model + stress test. No real deal; all inputs are assumptions.
Run: python3 model.py   (prints tables; writes results.json)

Two cases:
  page      = the numbers on the family page (8% on the whole loan for 12 months, no selling costs, no lender fees)
  realistic = same project with typical lender limits and costs (65% of sale value cap, monthly rate, fees, selling costs)
Rates and limits follow lender pages dated April-Oct 2026 (ABC Finance, Montpelier). Everything else is my assumption.
"""
import json, random, statistics

BASE = dict(
    gdv=720_000,            # expected sale value (family page)
    cost=550_000,           # land + build + fees + contingency, before finance (family page)
    sell_pct=0.025,         # agent 1.5% + legal 0.5% + marketing 0.5% (assumption)
    ltc=0.90,               # max loan as share of cost (lender pages: up to 85-90%)
    ltgdv=0.65,             # max loan as share of sale value (lender pages: 65%, 70% for experienced)
    rate_month=0.0095,      # 0.95%/month = first-time developer band (lender page: 0.95-1.10%)
    drawn=0.70,             # average share of the loan drawn over the term (assumption)
    months=15,              # 12 build + 3 sale (assumption)
    arr_fee=0.015, exit_fee=0.01, broker=0.01,   # lender pages: 1-2%, 1-2%, ~1%
    fixed_fees=15_000,      # legal, valuation, monitoring surveyor (lender page: GBP 5-12k legal + visits)
)

def deal(gdv_chg=0.0, cost_chg=0.0, delay=0, rate_add=0.0, p=BASE, mode="realistic"):
    gdv = p["gdv"] * (1 + gdv_chg)
    cost = p["cost"] * (1 + cost_chg)
    months = p["months"] + delay
    if mode == "page":   # the family page's own arithmetic
        loan = 495_000
        interest = loan * (0.08 + rate_add) * (12 + delay) / 12
        sell = 0.0
        fees = 0.0
        loan_cap_note = "page: 90% of cost, 8% a year on whole loan, 12 months"
    else:
        # lender sizes the loan on the ORIGINAL plan (cost and value as underwritten), not on the stressed outcome
        loan = min(p["ltc"] * p["cost"], p["ltgdv"] * p["gdv"])
        rate = p["rate_month"] + rate_add / 12
        interest = loan * p["drawn"] * rate * months
        sell = gdv * p["sell_pct"]
        fees = loan * (p["arr_fee"] + p["exit_fee"] + p["broker"]) + p["fixed_fees"]
    finance = interest + fees
    total_need = cost + finance                 # all cash needed before sale
    equity_in = total_need - loan               # what the partners must put in
    # extra cash if costs overrun beyond what was planned is also equity (lender does not lend more)
    planned_need = p["cost"] + (loan * p["drawn"] * (p["rate_month"] if mode != "page" else 0.08/12) * (p["months"] if mode != "page" else 12)) + (fees if mode != "page" else 0)
    profit = gdv - sell - cost - finance
    # lender is repaid first: loan + rolled interest + fees come out of sale proceeds
    owed_to_lender = loan + interest + (loan * (p["arr_fee"] + p["exit_fee"] + p["broker"]) if mode != "page" else 0)
    proceeds = gdv - sell
    shortfall = max(0.0, owed_to_lender - proceeds)   # amount the lender cannot recover from the sale: guarantee is called
    return dict(profit=profit, equity_in=equity_in, loan=loan, finance=finance, shortfall=shortfall,
                margin_on_gdv=profit / gdv, roe=profit / equity_in if equity_in > 0 else None)

def money(x): return f"{x:,.0f}"

def scenarios(mode):
    rows = [("Base", {}),
            ("Sale price -5%", dict(gdv_chg=-0.05)), ("Sale price -10%", dict(gdv_chg=-0.10)),
            ("Sale price -15%", dict(gdv_chg=-0.15)), ("Sale price -20%", dict(gdv_chg=-0.20)),
            ("Sale price -25%", dict(gdv_chg=-0.25)), ("Sale price -30%", dict(gdv_chg=-0.30)), ("Sale price -35%", dict(gdv_chg=-0.35)),
            ("Build cost +10%", dict(cost_chg=0.10)), ("Build cost +20%", dict(cost_chg=0.20)),
            ("Delay +3 months", dict(delay=3)), ("Delay +6 months", dict(delay=6)), ("Delay +12 months", dict(delay=12)),
            ("Interest +2 points a year", dict(rate_add=0.02)),
            ("BAD: price -10%, cost +10%, delay +6m", dict(gdv_chg=-0.10, cost_chg=0.10, delay=6)),
            ("SEVERE: price -15%, cost +15%, delay +9m, rate +2", dict(gdv_chg=-0.15, cost_chg=0.15, delay=9, rate_add=0.02))]
    out = []
    for name, kw in rows:
        r = deal(mode=mode, **kw); r["name"] = name; out.append(r)
    return out

def breakeven_price_drop(mode):
    lo, hi = 0.0, 0.6
    for _ in range(60):
        mid = (lo + hi) / 2
        if deal(gdv_chg=-mid, mode=mode)["profit"] > 0: lo = mid
        else: hi = mid
    return lo

def guarantee_trigger_price_drop(mode):
    """Sale-price fall at which the sale no longer repays the lender (this is when a personal guarantee is called)."""
    lo, hi = 0.0, 0.8
    for _ in range(60):
        mid = (lo + hi) / 2
        if deal(gdv_chg=-mid, mode=mode)["shortfall"] > 0: hi = mid
        else: lo = mid
    return lo

def deal_quality_sweep(mode="realistic"):
    """How good must the deal be before the odds are acceptable? Raises sale value, keeps cost fixed."""
    rows = []
    for gdv in range(720_000, 960_001, 20_000):
        q = dict(BASE, gdv=gdv)
        r = deal(mode=mode, p=q)
        rng = random.Random(7); n = 6000; losses = 0
        for _ in range(n):
            x = deal(gdv_chg=tri(-0.15, 0.0, 0.05, rng), cost_chg=tri(-0.02, 0.08, 0.25, rng), delay=tri(0, 3, 12, rng), rate_add=tri(-0.01, 0.0, 0.03, rng), p=q, mode=mode)
            if x["profit"] < 0: losses += 1
        rows.append(dict(gdv=gdv, base_profit=r["profit"], margin_on_gdv=r["margin_on_gdv"], profit_on_cost=r["profit"] / (q["cost"] + r["finance"]), p_loss=losses / n))
    return rows

def tri(a, m, b, rng): return rng.triangular(a, b, m)

def monte_carlo(n=20_000, seed=7, mode="realistic"):
    rng = random.Random(seed)
    res = []
    for _ in range(n):
        r = deal(gdv_chg=tri(-0.15, 0.0, 0.05, rng), cost_chg=tri(-0.02, 0.08, 0.25, rng),
                 delay=tri(0, 3, 12, rng), rate_add=tri(-0.01, 0.0, 0.03, rng), mode=mode)
        res.append(r)
    profits = sorted(r["profit"] for r in res)
    eq = BASE_EQUITY[mode]
    return dict(
        n=n,
        p_loss=sum(1 for r in res if r["profit"] < 0) / n,
        p_lose_over_half_equity=sum(1 for r in res if r["profit"] < -0.5 * eq) / n,
        p_lose_all_equity=sum(1 for r in res if r["profit"] <= -eq) / n,
        p_lender_shortfall=sum(1 for r in res if r["shortfall"] > 0) / n,
        median_profit=profits[n // 2], p5=profits[int(n * 0.05)], p95=profits[int(n * 0.95)],
        mean_profit=statistics.mean(profits), worst=profits[0])

BASE_EQUITY = {}
for m in ("page", "realistic"):
    BASE_EQUITY[m] = deal(mode=m)["equity_in"]

if __name__ == "__main__":
    out = {}
    for mode in ("page", "realistic"):
        print(f"\n=== {mode.upper()} CASE ===")
        rows = scenarios(mode); out[mode] = dict(scenarios=rows, breakeven_price_drop=breakeven_price_drop(mode), guarantee_trigger_price_drop=guarantee_trigger_price_drop(mode), monte_carlo=monte_carlo(mode=mode))
        print(f"{'Scenario':52s} {'Profit':>10s} {'Margin':>7s} {'Equity in':>10s} {'Lender shortfall':>17s}")
        for r in rows:
            print(f"{r['name']:52s} {money(r['profit']):>10s} {r['margin_on_gdv']*100:6.1f}% {money(r['equity_in']):>10s} {money(r['shortfall']):>17s}")
        print("Sale price fall that wipes out profit:", f"{out[mode]['breakeven_price_drop']*100:.1f}%")
        print("Sale price fall at which the lender is not fully repaid (guarantee called):", f"{out[mode]['guarantee_trigger_price_drop']*100:.1f}%")
        mc = out[mode]["monte_carlo"]
        print("Monte Carlo (20,000 runs, my assumed ranges):")
        for k, v in mc.items():
            print(f"  {k}: {v:.3f}" if isinstance(v, float) and abs(v) < 5 else f"  {k}: {money(v) if isinstance(v,(int,float)) else v}")
    sw = deal_quality_sweep("realistic"); out["deal_quality_sweep"] = sw
    print("\n=== DEAL QUALITY SWEEP (realistic case, cost fixed at 550k) ===")
    print(f"{'Sale value':>10s} {'Base profit':>12s} {'Margin':>7s} {'Profit/cost':>11s} {'P(loss)':>8s}")
    for r in sw: print(f"{r['gdv']:>10,} {money(r['base_profit']):>12s} {r['margin_on_gdv']*100:6.1f}% {r['profit_on_cost']*100:10.1f}% {r['p_loss']*100:7.1f}%")
    json.dump(out, open("results.json", "w"), indent=1)
