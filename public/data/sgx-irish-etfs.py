"""
Reproduction script for "Can I Now Hold the S&P 500 on SGX Without the US Estate Tax?"
theenoughpoint.com/sgx-irish-etfs-us-estate-tax

Recomputes every derived figure in the piece from the stated inputs. Standard library
only. Run:  python sgx-irish-etfs.py            (uses the pinned inputs below)
            python sgx-irish-etfs.py --live     (re-fetches the SGD/USD rate from FRED)

Nothing here is a forecast. The costs are fund-level running costs on a constant notional;
the estate figures apply the published US schedule to a stated holding.
"""
import sys
import urllib.request

# ---------------------------------------------------------------------------
# Inputs, each with its source and as-at date
# ---------------------------------------------------------------------------

# Annual fund charges (% of assets a year)
TER = {
    "S27 (SGX, US trust)":           0.0945,  # SSGA Singapore fund page, gross expense ratio, 22 Sep 2026
    "CSPX (London, Irish)":          0.07,    # iShares factsheet, 31 Aug 2026
    "Xtrackers S&P 500 (SGX, Irish)": 0.03,   # DWS factsheet (IE000Z9SJA06, class 4C), all-in fee, 31 Aug 2026
}

# Share of US dividends lost to US withholding tax, by domicile.
#   US fund -> non-resident holder with no treaty (Singapore): 30% of the distribution,
#     IRS Publication 515. No look-through for a US fund's distribution.
#   Irish fund -> 15% at fund level on US dividends, US-Ireland treaty Art. 10 portfolio rate.
#     Ireland does not withhold on the fund's accumulation; Singapore does not tax it.
WHT = {
    "S27 (SGX, US trust)":           0.30,
    "CSPX (London, Irish)":          0.15,
    "Xtrackers S&P 500 (SGX, Irish)": 0.15,
}

# S&P 500 trailing dividend yield, % — multpl.com, close 22 Sep 2026.
DIV_YIELD = 1.04  # cross-check: SPY 12m distributions to 18 Sep 2026 = 0.99% net of fee, ~1.08% gross

# SGD per USD — FRED DEXSIUS (Federal Reserve H.10), 18 Sep 2026.
SGD_PER_USD = 1.2775

# IRC Chapter 11 Table A, per IRS Instructions for Form 706 (rev. 09/2025):
# [over, not over, tax on column A, rate on excess]
BRACKETS = [
    (0, 10_000, 0, .18), (10_000, 20_000, 1_800, .20), (20_000, 40_000, 3_800, .22),
    (40_000, 60_000, 8_200, .24), (60_000, 80_000, 13_000, .26), (80_000, 100_000, 18_200, .28),
    (100_000, 150_000, 23_800, .30), (150_000, 250_000, 38_800, .32),
    (250_000, 500_000, 70_800, .34), (500_000, 750_000, 155_800, .37),
    (750_000, 1_000_000, 248_300, .39), (1_000_000, None, 345_800, .40),
]
CREDIT = 13_000  # Form 706-NA, maximum unified credit for a non-resident non-citizen


def live_fx():
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXSIUS"
    rows = urllib.request.urlopen(url, timeout=20).read().decode().strip().splitlines()[1:]
    rows = [r.split(",") for r in rows if r.split(",")[1] not in ("", ".")]
    return rows[-1][0], float(rows[-1][1])


def us_estate_tax(usd):
    for lo, hi, base, rate in BRACKETS:
        if hi is None or usd <= hi:
            return max(0.0, base + rate * (usd - lo) - CREDIT)
    return 0.0


def main():
    fx, fx_date = SGD_PER_USD, "18 Sep 2026 (pinned)"
    if "--live" in sys.argv:
        fx_date, fx = live_fx()

    print(f"S&P 500 dividend yield {DIV_YIELD:.2f}%  |  S$ per US$ {fx:.4f} as at {fx_date}\n")

    print("1. Fund-level running cost a year: charge + dividend tax lost")
    drag = {}
    for k in TER:
        leak = WHT[k] * DIV_YIELD
        drag[k] = TER[k] + leak
        print(f"   {k:32s} {TER[k]:.4f}% + {leak:.3f}% = {drag[k]:.3f}%")

    us, irish = "S27 (SGX, US trust)", "Xtrackers S&P 500 (SGX, Irish)"
    gap = drag[us] - drag[irish]
    print(f"\n   Gap, US trust vs Irish fund on SGX: {gap:.3f} percentage points a year")
    for amt in (100_000, 300_000):
        print(f"   On S${amt:,}: S${amt * drag[us] / 100:,.0f} vs S${amt * drag[irish] / 100:,.0f}"
              f"  (difference S${amt * gap / 100:,.0f} a year)")

    print("\n2. US estate tax on the same holding, if it is the only US-situated asset")
    for amt in (77_000, 100_000, 300_000, 500_000):
        usd = amt / fx
        tax = us_estate_tax(usd)
        print(f"   S${amt:>7,} = US${usd:>9,.0f} -> tax US${tax:>9,.0f} = S${tax * fx:>9,.0f}"
              f"  ({(tax * fx / amt * 100) if amt else 0:.1f}% of the holding)")

    thresh_sgd = 60_000 * fx
    print(f"\n   US$60,000 threshold = S${thresh_sgd:,.0f} at this rate")

    print("\n3. How long the fee gap takes to repay a one-off cost")
    # Buying at the offer costs half the quoted spread against the fund's value.
    for spread in (0.15, 0.40):
        half = spread / 2
        print(f"   quoted spread {spread:.2f}% -> cost to buy {half:.3f}% of the amount;"
              f" repaid by the {gap:.3f}pp gap vs S27 in {half / gap:.1f} years")

    # An existing London holder who switches pays twice: out of the old line, into the new.
    ldn = "CSPX (London, Irish)"
    gap_ldn = drag[ldn] - drag[irish]
    print(f"\n   Gap, London Irish fund vs SGX Irish fund: {gap_ldn:.3f}pp a year")
    for round_trip in (0.20, 0.40):
        print(f"   a switch costing {round_trip:.2f}% in total is repaid in {round_trip / gap_ldn:.0f} years")


if __name__ == "__main__":
    main()
