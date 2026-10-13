"""
Reproduction script for "8 New SGX ETFs: What Are You Really Buying?"
theenoughpoint.com/sgx-etf-menu-eight-new-etfs

Recomputes holdings, published-fee illustrations and observed quote gaps in the article.
No projection of all-in ownership costs or route break-even periods is made. Standard library only.

    python sgx-etf-menu.py

Fee figures are not measures of the full drag on returns; transaction costs, currency
friction, taxes and other factors can also affect performance.
"""

# ---------------------------------------------------------------------------
# 1. Holdings: DWS factsheets "as of September 30, 2026", top 10 constituents
# ---------------------------------------------------------------------------
# Alphabet A and C share classes are added together. Only names in a fund's
# published top ten are carried, so a cross-fund figure counts a company only in
# the funds where it is a top-ten holding; the true figure can be slightly higher.

HOLDINGS = {
    "XUS": {"name": "S&P 500", "fee": 0.03, "top10": [
        ("Nvidia", 8.35), ("Apple", 7.44), ("Microsoft", 5.70), ("Amazon", 3.64),
        ("Alphabet", 3.03 + 2.43), ("Broadcom", 2.51), ("Meta", 2.38), ("Micron", 1.79),
        ("Tesla", 1.52)]},
    "XND": {"name": "Nasdaq-100", "fee": 0.20, "top10": [
        ("Nvidia", 8.41), ("Apple", 7.53), ("Microsoft", 5.76), ("Micron", 5.01), ("AMD", 4.18),
        ("Amazon", 4.05), ("Meta", 3.24), ("Alphabet", 3.07 + 2.86), ("Tesla", 2.86)]},
    "XWR": {"name": "MSCI World", "fee": 0.12, "top10": [
        ("Nvidia", 5.77), ("Apple", 5.46), ("Microsoft", 3.94), ("Amazon", 2.62),
        ("Alphabet", 2.21 + 1.74), ("Broadcom", 1.73), ("Meta", 1.73), ("Micron", 1.31),
        ("Tesla", 1.12)]},
    "EUS": {"name": "S&P 500 Equal Weight", "fee": 0.15, "top10": [
        ("Moderna", 0.30), ("Everpure", 0.27), ("Illumina", 0.27), ("CrowdStrike", 0.25),
        ("Revvity", 0.25), ("Agilent", 0.25), ("Mettler-Toledo", 0.24), ("Datadog", 0.24),
        ("Intuitive Surgical", 0.24), ("Palo Alto Networks", 0.24)]},
    "XBG": {"name": "AI & Big Data (iFAST feeder)", "fee": None, "underlying_fee": 0.35, "top10": [
        ("Microsoft", 5.75), ("Meta", 5.35), ("Apple", 4.93), ("Nvidia", 4.82), ("AMD", 4.41),
        ("Amazon", 4.35), ("Walmart", 4.04), ("Alphabet", 4.04), ("Samsung Electronics", 3.86),
        ("Micron", 3.85)]},
    "JPY": {"name": "Nikkei 225 (iFAST feeder)", "fee": None, "underlying_fee": 0.09, "top10": [
        ("Advantest", 12.34), ("Tokyo Electron", 8.59), ("Fast Retailing", 8.28),
        ("SoftBank Group", 7.62), ("Recruit", 2.51), ("Ibiden", 2.27), ("TDK", 2.25),
        ("Kioxia", 1.90), ("KDDI", 1.82), ("Fujikura", 1.51)]},
    "KOR": {"name": "MSCI Korea 20/35 (iFAST feeder)", "fee": None, "underlying_fee": 0.45, "top10": [
        ("Samsung Electronics", 28.26), ("SK hynix", 17.90), ("SK Square", 4.30),
        ("Samsung Electronics (preference)", 3.72), ("Samsung Electro-Mechanics", 3.55),
        ("KB Financial", 2.48), ("Hyundai Motor", 2.00), ("Shinhan Financial", 1.96),
        ("Doosan Enerbility", 1.56), ("Hana Financial", 1.53)]},
    "TWD": {"name": "MSCI Taiwan 20/35 (iFAST feeder)", "fee": None, "underlying_fee": 0.65, "top10": [
        ("TSMC", 30.23), ("MediaTek", 10.04), ("Delta Electronics", 4.90), ("Hon Hai", 4.05),
        ("ASE", 3.08), ("UMC", 2.29), ("Unimicron", 2.11), ("Elite Material", 1.91),
        ("Fubon Financial", 1.66), ("Asia Vital Components", 1.52)]},
}

# Published pre-launch TER figures, treated as estimates, not caps or audited actuals.
# FSM Global (iFAST), Table 1 in each article; no component reconciliation supplied.
# Japan/AI, data at 30 Sep 2026: https://fsm.global/sg/article/rcms397041
# and https://fsm.global/sg/article/rcms397262 (AI table labels this TER, not estimated TER).
# Korea/Taiwan, data at 29 Sep 2026: https://fsm.global/sg/article/rcms397520
PUBLISHED_TER = {"JPY": 0.43, "XBG": 0.63, "KOR": 0.67, "TWD": 0.77}
for code, f in HOLDINGS.items():
    if f["fee"] is None:
        f["fee"] = PUBLISHED_TER[code]

FIVE = ["Nvidia", "Apple", "Microsoft", "Amazon", "Alphabet"]
EW_PER_NAME = 0.2   # about 500 names at ~0.2% each: approximate


def weight(code, company):
    if code == "EUS" and company in FIVE:
        return EW_PER_NAME
    return dict(HOLDINGS[code]["top10"]).get(company, 0.0)


def five_share(code):
    return sum(weight(code, c) for c in FIVE)


def largest(code):
    return max(HOLDINGS[code]["top10"], key=lambda kv: kv[1])


def top10_sum(code):
    return sum(w for _, w in HOLDINGS[code]["top10"])


# Published holdings and fees only; no projected route-cost model.
def pct(x):
    return f"{x:.1f}%"


def sgd(x):
    return f"S${x:,.0f}"


print("=" * 80)
print("A. Share of each fund in the same five US companies (DWS factsheets, 30 Sep 2026)")
for code in sorted(HOLDINGS, key=five_share, reverse=True):
    note = "  (approx., ~0.2% each)" if code == "EUS" else ""
    print(f"  {code}  {HOLDINGS[code]['name']:<32} {pct(five_share(code)):>6}   Nvidia {weight(code, 'Nvidia'):.2f}%{note}")

print("\nB. Biggest company in each fund, and the ten biggest together")
for code in sorted(HOLDINGS, key=lambda c: largest(c)[1], reverse=True):
    name, w = largest(code)
    extra = ""
    if code == "KOR":
        extra = f"  (+{weight(code, 'Samsung Electronics (preference)'):.2f}% preference shares = {w + weight(code, 'Samsung Electronics (preference)'):.1f}%)"
    print(f"  {code}  {name:<22} {pct(w):>6}   top ten {pct(top10_sum(code))}{extra}")

print("\nC. Annual fund-level charge on S$10,000")
for code in sorted(HOLDINGS, key=lambda c: HOLDINGS[c]["fee"]):
    f = HOLDINGS[code]
    est = "  publisher TER figure treated as estimate, not a cap" if code in PUBLISHED_TER else ""
    print(f"  {code}  {f['fee']:.2f}%  = {sgd(f['fee'] / 100 * 10_000)} a year{est}")

print("\nF. Measured quotes on day one, 13 Oct 2026 (Yahoo Finance delayed quotes, SGT)")
QUOTES = [("XUS", "09:57", 19.56, 19.57, 29_576), ("XND", "10:10", 91.79, 91.82, 2_040),
          ("XWR", "10:39", 205.50, 207.00, 1_919), ("EUS", "10:34", 151.50, 153.73, 612)]
for code, t, bid, ask, vol in QUOTES:
    gap = (ask - bid) / ((ask + bid) / 2) * 100
    print(f"  {code} at {t}: bid {bid} ask {ask} gap {gap:.2f}%  volume {vol:,}")

print("\nG. SGX menu count (SGX ETF Market Highlights 1H2026, June 2026)")
sg, cn, rg = 7 + 7, 13 + 2, 16 + 8
print(f"  Singapore {sg}, China {cn}, regional and global {rg}, total {sg + cn + rg}; plus eight = {sg + cn + rg + 8}")

print("\nH. Korea fee build-ups (full underlying investment; Singapore expenses remain unknown)")
for label, management in (("Current Singapore management", 0.25), ("Singapore management ceiling", 0.90)):
    subtotal = round(management + HOLDINGS["KOR"]["underlying_fee"], 2)
    print(f"  {label}: {management:.2f}% + 0.45% = {subtotal:.2f}% plus Singapore expenses; {sgd(subtotal / 100 * 10_000)} plus expenses on S$10,000")
print("  Published estimated total: 0.67%; component reconciliation not supplied; no overall cap established")

# ---------------------------------------------------------------------------
# 4. Self-checks (the figures quoted in the article)
# ---------------------------------------------------------------------------
assert abs(five_share("XND") - 31.68) < 0.01 and abs(five_share("XUS") - 30.59) < 0.01
assert abs(five_share("XBG") - 23.89) < 0.01 and abs(five_share("XWR") - 21.74) < 0.01
assert largest("TWD") == ("TSMC", 30.23) and largest("KOR")[1] == 28.26
assert HOLDINGS["TWD"]["fee"] == 0.77 and HOLDINGS["KOR"]["fee"] == 0.67
assert HOLDINGS["XBG"]["fee"] == 0.63 and HOLDINGS["JPY"]["fee"] == 0.43
print("\nAll self-checks pass.")
