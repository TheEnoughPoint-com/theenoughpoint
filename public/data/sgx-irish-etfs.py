"""
Reproduction script for "Can I Now Hold the S&P 500 on SGX Without the US Estate Tax?"
theenoughpoint.com/sgx-irish-etfs-us-estate-tax

Recomputes every derived figure in the article and the calculator's default output
from the stated inputs, then runs edge-case checks. Standard library only.

    python sgx-irish-etfs.py            pinned inputs (the article's fixed examples)
    python sgx-irish-etfs.py --live     re-fetches the SGD/USD rate from FRED; the
                                        calculator uses a rate refreshed at each site
                                        build, so its figures can differ slightly

These are estimates under stated assumptions, not measured performance. They leave out
tracking difference, securities-lending income, platform and custody fees, and the
exceptions to the 30% US rate (interest-related and short-term capital-gain dividends).
"""
import sys
import urllib.request

# ---------------------------------------------------------------------------
# Inputs, each with its source and as-at date
# ---------------------------------------------------------------------------

S27, CSPX, XT = "S27 (US fund, SGX)", "CSPX (Irish fund, London)", "Xtrackers S&P 500 4C (Irish fund, SGX)"

# Annual fund fee, % of assets
TER = {
    S27:  0.0945,  # SSGA Singapore fund page, gross expense ratio, 22 Sep 2026
    CSPX: 0.07,    # iShares factsheet, 31 Aug 2026
    XT:   0.03,    # DWS factsheet (IE000Z9SJA06, class 4C), all-in fee, 31 Aug 2026
}

# US dividend tax rate and the base it applies to.
#   S27: 30% general rate on ordinary dividends to a no-treaty holder (IRS Pub. 515),
#        applied to distributions, which S27 pays "net of fees and expenses"
#        (SPDR S&P 500 ETF Trust prospectus) -> base = yield - fee, floored at zero.
#   Irish funds: 15% on US dividends at fund level (IRS Treaty Table 1) -> base = yield.
WHT = {S27: 0.30, CSPX: 0.15, XT: 0.15}
NET_OF_FEE = {S27: True, CSPX: False, XT: False}

# S&P 500 trailing dividend yield, % — multpl.com, close 22 Sep 2026 (secondary source).
DIV_YIELD = 1.04

# SGD per USD — FRED DEXSIUS (Federal Reserve H.10), 18 Sep 2026.
SGD_PER_USD = 1.2775

# IRC Chapter 11 Table A, per IRS Instructions for Form 706 (rev. 09/2025):
# (over, not over, tax on column A, rate on excess)
BRACKETS = [
    (0, 10_000, 0, .18), (10_000, 20_000, 1_800, .20), (20_000, 40_000, 3_800, .22),
    (40_000, 60_000, 8_200, .24), (60_000, 80_000, 13_000, .26), (80_000, 100_000, 18_200, .28),
    (100_000, 150_000, 23_800, .30), (150_000, 250_000, 38_800, .32),
    (250_000, 500_000, 70_800, .34), (500_000, 750_000, 155_800, .37),
    (750_000, 1_000_000, 248_300, .39), (1_000_000, None, 345_800, .40),
]
CREDIT = 13_000  # Form 706-NA, maximum unified credit for a non-resident non-citizen

# Calculator defaults (SP500RoutesTool.astro): illustrative dealing costs, % of holding
TOOL_AMOUNT, TOOL_YEARS = 100_000, 10
TOOL_BUY = {S27: 0.30, CSPX: 0.30, XT: 0.25}
TOOL_SELL = {S27: 0.30, CSPX: 0.30, XT: 0.20}

# ---------------------------------------------------------------------------


def annual_pct(fund, dy):
    """Estimated annual fund fee + US dividend tax, % of the holding."""
    base = max(0.0, dy - TER[fund]) if NET_OF_FEE[fund] else max(0.0, dy)
    return TER[fund] + WHT[fund] * base


def us_estate_tax_usd(usd):
    for lo, hi, base, rate in BRACKETS:
        if hi is None or usd <= hi:
            return max(0.0, base + rate * (usd - lo) - CREDIT)
    return 0.0


def estate_tax_sgd(sgd, fx):
    """S$ holding -> US$ (divide by S$ per US$) -> tax in US$ -> back to S$."""
    return us_estate_tax_usd(sgd / fx) * fx


def tool_totals(amount, years, dy, buy=TOOL_BUY, sell=TOOL_SELL):
    out = {}
    for f in TER:
        run = amount * annual_pct(f, dy) / 100 * years
        out[f] = dict(buy=amount * buy[f] / 100, run=run, sell=amount * sell[f] / 100,
                      total=amount * (buy[f] + sell[f]) / 100 + run)
    return out


def live_fx():
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXSIUS"
    rows = urllib.request.urlopen(url, timeout=20).read().decode().strip().splitlines()[1:]
    rows = [r.split(",") for r in rows if r.split(",")[1] not in ("", ".")]
    return rows[-1][0], float(rows[-1][1])


def main():
    fx, fx_date = SGD_PER_USD, "18 Sep 2026 (pinned; the article's examples)"
    if "--live" in sys.argv:
        fx_date, fx = live_fx()
        fx_date += " (live; the calculator's figures use the rate at site build)"

    print(f"S&P 500 dividend yield {DIV_YIELD:.2f}%  |  S$ {fx:.4f} per US$, {fx_date}\n")

    print("1. Estimated fund fee + dividend tax a year (article table)")
    for f in TER:
        a = annual_pct(f, DIV_YIELD)
        print(f"   {f:40s} {TER[f]:.4f}% + {a - TER[f]:.4f}% = {a:.5f}%  -> S${a * 1000:,.0f} on S$100,000")
    gap = annual_pct(S27, DIV_YIELD) - annual_pct(XT, DIV_YIELD)
    gap_c = annual_pct(CSPX, DIV_YIELD) - annual_pct(XT, DIV_YIELD)
    print(f"\n   S27 - Xtrackers: {gap:.5f} pp  = S${gap * 1000:,.0f} a year on S$100,000")
    print(f"   CSPX - Xtrackers: {gap_c:.5f} pp = S${gap_c * 1000:,.0f} a year on S$100,000")

    print("\n2. US estate tax (holder neither US citizen nor US-domiciled; only US-situated asset)")
    print(f"   US$60,000 threshold = S${60_000 * fx:,.0f}")
    for amt in (100_000, 300_000):
        print(f"   S${amt:,} -> S${estate_tax_sgd(amt, fx):,.0f}")

    print("\n3. Recovery of a one-off cost by the annual gap")
    half = 0.40 / 2
    print(f"   0.40% spread -> {half:.2f}% above midpoint to buy")
    print(f"   0.20% extra, against S27: {half / gap:.2f} years; against CSPX: {half / gap_c:.1f} years")
    for sw in (0.20, 0.40):
        print(f"   a switch from CSPX costing {sw:.2f}% in total: {sw / gap_c:.1f} years")

    print(f"\n4. Calculator defaults: S${TOOL_AMOUNT:,}, {TOOL_YEARS} years, cash")
    t = tool_totals(TOOL_AMOUNT, TOOL_YEARS, DIV_YIELD)
    for f, v in t.items():
        print(f"   {f:40s} buy S${v['buy']:,.0f} + fee/tax S${v['run']:,.0f} + sell S${v['sell']:,.0f}"
              f" = S${v['total']:,.0f}")
    print(f"   fee/tax difference S27 - Xtrackers: S${t[S27]['run'] - t[XT]['run']:,.0f};"
          f" total difference: S${t[S27]['total'] - t[XT]['total']:,.0f}")

    checks(fx)


def checks(fx):
    print("\n5. Checks")
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f"   {'PASS' if cond else 'FAIL'}  {name}")

    check("S27 = 0.0945 + 0.30 x (1.04 - 0.0945) = 0.37815%", abs(annual_pct(S27, 1.04) - 0.37815) < 1e-9)
    check("gap S27 - Xtrackers = 0.19215 pp", abs(annual_pct(S27, 1.04) - annual_pct(XT, 1.04) - 0.19215) < 1e-9)
    check("zero yield: every fund's cost equals its fee", all(abs(annual_pct(f, 0) - TER[f]) < 1e-12 for f in TER))
    check("yield below S27's fee: no negative dividend tax", annual_pct(S27, 0.05) == TER[S27])
    check("estate: exactly US$60,000 -> zero tax", us_estate_tax_usd(60_000) == 0)
    check("estate: US$60,001 -> 26% on the excess", abs(us_estate_tax_usd(60_001) - 0.26) < 1e-9)
    check("estate: bracket boundary US$100,000 continuous",
          abs((18_200 + 0.28 * 20_000) - (23_800 + 0.30 * 0)) < 1e-9)
    check("estate: FX direction (S$ / rate, then x rate)",
          abs(estate_tax_sgd(60_000 * fx, fx)) < 1e-6 and estate_tax_sgd(100_000, 1.2775) > 6_000)
    t5 = tool_totals(100_000, 5, 1.04)
    check("5-year run cost is half the 10-year one",
          abs(t5[XT]['run'] * 2 - tool_totals(100_000, 10, 1.04)[XT]['run']) < 1e-6)
    t_deal = tool_totals(100_000, 10, 1.04, buy={S27: 0, CSPX: 0, XT: 0}, sell={S27: 0, CSPX: 0, XT: 0})
    check("zero dealing costs: total equals fee/tax cost", all(abs(v['total'] - v['run']) < 1e-9 for v in t_deal.values()))
    print(f"\n   {'ALL CHECKS PASS' if ok else 'CHECKS FAILED'}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
