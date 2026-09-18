"""
Reproduce every computed figure in "Fed Rate Hike: What US Shares, Gold and the STI Did Next"
— theenoughpoint.com/fed-rate-hike-us-shares-gold-sti/

Run it and it will download the public datasets itself, recompute the numbers from scratch,
and check them against what the article published. If a line prints MISMATCH, we got
something wrong and we would like to know.

    pip install pandas numpy requests openpyxl
    python first-hike.py

What this is, precisely
  The same rule the article ran, in one file with no local dependencies, written to be read.
  Provided as is, with no warranty; the datasets belong to their publishers and carry their
  own terms.

Data, all free and public
  FRED DFEDTAR, DFEDTARU   fed funds target: the single target to 15 Dec 2008, the upper
                           bound of the range from 16 Dec 2008 (Federal Reserve Board)
  FRED DEXSIUS             Singapore dollars per US dollar, noon buying rates in New York
                           (Federal Reserve H.10)
  Yahoo Finance            ^GSPC  S&P 500 price index, daily closes
                           ^STI   Straits Times Index, daily closes (price index)
                           GC=F   COMEX gold futures, front month, daily closes from Aug 2000
  World Bank Pink Sheet    gold, monthly average of London afternoon prices, US$/troy oz
                           (Commodity Markets Outlook historical data, CC BY 4.0)

The rule, stated exactly
  1. A "first hike" is the first increase in the fed funds target after at least 365 days
     without one, taken from FRED's own target series, from 1994 — the year the Fed began
     announcing its decisions. Six qualify with an after-window: 4 Feb 1994, 25 Mar 1997,
     30 Jun 1999, 30 Jun 2004, 16 Dec 2015, 16 Mar 2022. FRED records the 2022 step on its
     effective date (17 March); the announcement was the 16th. The seventh, 16 Sep 2026, is
     live and has no after-window yet.
  2. The clock starts at the last close BEFORE the announcement, so the reaction on the day
     is inside the window: for US series the previous session's close; for the STI the close
     of the announcement date, which ends before 2pm New York time on the same calendar day.
  3. Horizons are 21, 63, 126 and 252 trading days on each series' own calendar (about one,
     three, six and twelve months). Gold's monthly series counts months from the hike month's
     average.
  4. "In Singapore dollars" multiplies the US-dollar level by SGD per USD on the same day
     (previous available fixing where the US holiday differs).
  5. "Usual" is the median of the same horizon started on every trading day from 3 Jan 1994
     to 16 Sep 2026 that has a full horizon, and the share of those starts that ended higher.
  6. "About one time in N" is a random-entry check: draw six start days at random from the
     same pool 2,000 times, take each draw's median, and count how often it is at least as
     far from the usual as the six hikes were (two-sided).

Python months are 1-indexed (datetime / pandas).
"""
import io
import json

import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (reproduction script; theenoughpoint.com)"}
WINDOW_START = pd.Timestamp("1994-01-01")
POOL_END = pd.Timestamp("2026-09-16")      # pin the base-rate window so reruns stay like-for-like
H = [(21, "1M"), (63, "3M"), (126, "6M"), (252, "12M")]
ITERS = 2000
rng = np.random.default_rng(20260917)


def fred(sid):
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", headers=UA, timeout=120)
    d = pd.read_csv(io.StringIO(r.text))
    d.columns = ["date", "v"]
    d["date"] = pd.to_datetime(d["date"])
    d["v"] = pd.to_numeric(d["v"], errors="coerce")
    return d.dropna().set_index("date")["v"].sort_index()


def yahoo(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=0&period2=9999999999&interval=1d"
    res = requests.get(url, headers=UA, timeout=120).json()["chart"]["result"][0]
    ts = pd.to_datetime(res["timestamp"], unit="s", utc=True)
    tz = res["meta"].get("exchangeTimezoneName", "UTC")
    dates = ts.tz_convert(tz).normalize().tz_localize(None)
    s = pd.Series(res["indicators"]["quote"][0]["close"], index=dates, dtype="float64").dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[s > 0]


def worldbank_gold():
    # The World Bank moves this file when it republishes; the landing page always links the
    # current copy: https://www.worldbank.org/en/research/commodity-markets
    url = "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx"
    b = requests.get(url, headers=UA, timeout=180).content
    x = pd.read_excel(io.BytesIO(b), sheet_name="Monthly Prices", header=None)
    hdr = next(i for i in range(10) if any("Gold" in str(v) for v in x.iloc[i].tolist()))
    gi = next(i for i, c in enumerate(x.iloc[hdr].tolist()) if str(c).strip().lower() == "gold")
    d = x.iloc[hdr + 2:, [0, gi]].dropna()
    d.columns = ["ym", "gold"]
    d["date"] = pd.to_datetime(d["ym"].astype(str), format="%YM%m") + pd.offsets.MonthEnd(0)
    d["gold"] = pd.to_numeric(d["gold"], errors="coerce")
    return d.dropna().set_index("date")["gold"].sort_index()


# ------------------------------------------------------------------ 1. the six first hikes
print("Downloading FRED, Yahoo Finance and World Bank data...\n")
tar = pd.concat([fred("DFEDTAR"), fred("DFEDTARU")]).sort_index()
tar = tar[~tar.index.duplicated(keep="last")]
ups = tar.diff()
ups = ups[ups > 0].index
firsts, last_up = [], None
for d in ups:
    if last_up is None or (d - last_up).days >= 365:
        firsts.append(d)
    last_up = d
firsts = [d for d in firsts if d >= WINDOW_START]
# FRED dates the 2022 step on its effective date, the day after the announcement.
ANNOUNCED = {"1994-02-04": "1994-02-04", "1997-03-25": "1997-03-25", "1999-06-30": "1999-06-30",
             "2004-06-30": "2004-06-30", "2015-12-16": "2015-12-16", "2022-03-17": "2022-03-16"}
found = [str(d.date()) for d in firsts if d <= POOL_END]
print("First hikes found in FRED's target series:", found)
assert found[:6] == list(ANNOUNCED.keys()), "the event list has changed — stop and inspect"
EVENTS = [pd.Timestamp(v) for v in ANNOUNCED.values()]
LIVE = pd.Timestamp("2026-09-16")   # 3.50-3.75 to 3.75-4.00, unanimous; FRED shows it from 17 Sep
print("Announcement dates:", ", ".join(f"{d.date()} ({d.strftime('%a')})" for d in EVENTS), "\n")

spx, sti, gcf = yahoo("^GSPC"), yahoo("^STI"), yahoo("GC=F")
fx = fred("DEXSIUS")
gold_m = worldbank_gold()
for n, s in [("S&P 500 ^GSPC", spx), ("STI ^STI", sti), ("gold futures GC=F", gcf),
             ("USD/SGD DEXSIUS", fx), ("gold monthly", gold_m)]:
    print(f"  {n:20s} {s.index[0].date()} to {s.index[-1].date()}")
print()


# ------------------------------------------------------------------ 2. the machinery
def base_index(s, ann, market):
    """Position of the last close before the announcement is public."""
    idx = s.index
    p = idx.searchsorted(ann)
    if market == "US":
        return p - 1                                   # previous US session
    return p if (p < len(idx) and idx[p] == ann) else p - 1   # Singapore: the announcement-date session


def fwd(v, i, h):
    j = i + h
    return None if (i < 0 or j >= len(v)) else v[j] / v[i] - 1


def in_sgd(s):
    return (s * fx.reindex(s.index, method="ffill")).dropna()


def cells(s, market, dates=EVENTS):
    idx, v = s.index, s.to_numpy()
    bases = [base_index(s, d, market) for d in dates]
    st, en = idx.searchsorted(WINDOW_START), idx.searchsorted(POOL_END, side="right")
    out = {}
    for h, lab in H:
        per = [fwd(v, i, h) for i in bases]
        sig = np.array([x for x in per if x is not None])
        pool = np.array([x for x in (fwd(v, i, h) for i in range(st, min(en, len(v) - h))) if x is not None])
        med, base = float(np.median(sig)), float(np.median(pool))
        draws = np.median(pool[rng.integers(0, len(pool), size=(ITERS, len(sig)))], axis=1)
        p = float(min(1.0, 2 * min((draws <= med).mean(), (draws >= med).mean())))
        out[lab] = dict(per=[None if x is None else x * 100 for x in per], med=med * 100, up=int((sig > 0).sum()),
                        n=len(sig), base=base * 100, bup=float((pool > 0).mean() * 100), p=p)
    return out


def cells_monthly(s, dates):
    idx, v = s.index, s.to_numpy()
    bases = [idx.searchsorted(d + pd.offsets.MonthEnd(0)) for d in dates]
    st, en = idx.searchsorted(WINDOW_START), idx.searchsorted(POOL_END, side="right")
    out = {}
    for hm, lab in [(1, "1M"), (3, "3M"), (6, "6M"), (12, "12M")]:
        per = [fwd(v, i, hm) for i in bases]
        sig = np.array([x for x in per if x is not None])
        pool = np.array([x for x in (fwd(v, i, hm) for i in range(st, min(en, len(v) - hm))) if x is not None])
        med, base = float(np.median(sig)), float(np.median(pool))
        draws = np.median(pool[rng.integers(0, len(pool), size=(ITERS, len(sig)))], axis=1)
        p = float(min(1.0, 2 * min((draws <= med).mean(), (draws >= med).mean())))
        out[lab] = dict(per=[None if x is None else x * 100 for x in per], med=med * 100, up=int((sig > 0).sum()),
                        n=len(sig), base=base * 100, bup=float((pool > 0).mean() * 100), p=p)
    return out


def run_up(s, market, dates, h=126):
    idx, v = s.index, s.to_numpy()
    out = {}
    for d in dates:
        i = base_index(s, d, market)
        out[d.year] = (v[i] / v[i - h] - 1) * 100
    return out


def show(title, c):
    print(f"\n{title}")
    for lab, r in c.items():
        per = "  ".join(f"{d.year}:{x:+.1f}" for d, x in zip(EVENTS, r["per"]) if x is not None)
        print(f"  {lab:>3}  median {r['med']:+6.2f}%  higher {r['up']} of {r['n']}   usual {r['base']:+6.2f}% / {r['bup']:.0f}%"
              f"   one time in {1/r['p'] if r['p'] > 0 else float('inf'):.0f}   [{per}]")


ok = True


def check(label, got, want, tol=0.15):
    global ok
    good = abs(got - want) <= tol
    ok &= good
    print(f"  {'OK      ' if good else 'MISMATCH'} {label:<58} got {got:8.2f}   published {want:8.2f}")


# ------------------------------------------------------------------ 3. the figures
spx_usd = cells(spx, "US")
spx_sgd = cells(in_sgd(spx), "US")
sti_c = cells(sti, "SG")
usdsgd = cells(fx, "US")
gold_usd = cells_monthly(gold_m, EVENTS)
gold_sgd = cells_monthly(in_sgd(gold_m).resample("ME").last(), EVENTS) if False else None  # see below
# gold in SGD: convert the monthly average with the month's average fixing
fx_m = fx.resample("ME").mean()
gold_sgd = cells_monthly((gold_m * fx_m.reindex(gold_m.index)).dropna(), EVENTS)
gold_five = cells_monthly(gold_m, [d for d in EVENTS if d.year != 1997])
gold_fut = cells(gcf, "US", dates=[d for d in EVENTS if d.year >= 2004])

show("US shares (S&P 500 price index), in US dollars", spx_usd)
show("US shares, in Singapore dollars", spx_sgd)
show("Straits Times Index (price index), Singapore dollars", sti_c)
show("Gold, monthly averages, US dollars (six hikes)", gold_usd)
show("Gold, monthly averages, Singapore dollars (six hikes)", gold_sgd)
show("Gold, monthly averages, US dollars, five hikes (March 1997 dropped)", gold_five)
show("USD/SGD, Singapore dollars per US dollar (+ = Singapore dollar weaker)", usdsgd)
print("\nGold futures, US dollars, the three hikes inside the futures history (2004, 2015, 2022):")
print("  6M per hike: " + "  ".join(f"{d.year}:{x:+.1f}" for d, x in zip([e for e in EVENTS if e.year >= 2004], gold_fut["6M"]["per"])))

pre = {
    "spx": run_up(spx, "US", EVENTS + [LIVE]),
    "sti": run_up(sti, "SG", EVENTS + [LIVE]),
    "fx": run_up(fx, "US", EVENTS + [LIVE]),
    "gcf": run_up(gcf, "US", [d for d in EVENTS if d.year >= 2004] + [LIVE]),
}
gm = gold_m.to_numpy(); gidx = gold_m.index
pre["gold_m"] = {d.year: (gm[gidx.searchsorted(d + pd.offsets.MonthEnd(0))] / gm[gidx.searchsorted(d + pd.offsets.MonthEnd(0)) - 6] - 1) * 100 for d in EVENTS}
print("\nThe six months INTO each hike (to the last close before the announcement; 2026 included):")
for k, lab in [("spx", "US shares, USD"), ("sti", "STI"), ("fx", "USD/SGD"), ("gcf", "gold futures, USD"), ("gold_m", "gold monthly avg, USD")]:
    print(f"  {lab:24s} " + "  ".join(f"{y}:{x:+.1f}" for y, x in pre[k].items()))

day = {d.year: (spx.iloc[spx.index.searchsorted(d)] / spx.iloc[spx.index.searchsorted(d) - 1] - 1) * 100 for d in EVENTS + [LIVE]}
print("\nS&P 500 on the announcement day itself: " + "  ".join(f"{y}:{x:+.2f}%" for y, x in day.items()))

# ------------------------------------------------------------------ 3b. 2026, the live hike
# The article adds this hike's readings as dated points at the same four horizons, on a
# pre-announced schedule (one month in mid-October 2026, three in mid-December, six in
# mid-March 2027, twelve in mid-September 2027), whatever they show, and never between.
# This block prints whatever has completed so far; a horizon prints "pending" until its
# full count of sessions exists after the base close.
print("\n2026, THE LIVE HIKE — readings available so far")
def live_line(name, s, market, fx_series=None):
    if fx_series is not None:
        s = (s * fx_series.reindex(s.index, method="ffill")).dropna()
    i = base_index(s, LIVE, market)
    avail = len(s) - 1 - i
    parts = []
    for hh, lab in H:
        if i + hh < len(s):
            parts.append(f"{lab} {(s.iloc[i + hh] / s.iloc[i] - 1) * 100:+.1f}% (as at {s.index[i + hh].date()})")
        else:
            parts.append(f"{lab} pending ({avail}/{hh} sessions)")
    print(f"  {name:22s} " + "  ".join(parts))
live_line("US shares, USD", spx, "US")
live_line("US shares, SGD", spx, "US", fx)
live_line("STI", sti, "SG")
live_line("USD/SGD", fx, "US")
live_line("gold futures, USD", gcf, "US")
gi = gold_m.index.searchsorted(LIVE + pd.offsets.MonthEnd(0))
if gi < len(gold_m) and gold_m.index[gi] == LIVE + pd.offsets.MonthEnd(0):
    parts = []
    for hm, lab in [(1, "1M"), (3, "3M"), (6, "6M"), (12, "12M")]:
        parts.append(f"{lab} {(gold_m.iloc[gi + hm] / gold_m.iloc[gi] - 1) * 100:+.1f}% (to {gold_m.index[gi + hm].strftime('%b %Y')})"
                     if gi + hm < len(gold_m) else f"{lab} pending")
    print("  gold monthly, USD      " + "  ".join(parts))
else:
    print(f"  gold monthly, USD      pending: the World Bank file does not yet carry the {LIVE.strftime('%B %Y')} average "
          f"(series ends {gold_m.index[-1].strftime('%b %Y')})")
sg_live = (spx * fx.reindex(spx.index, method="ffill")).dropna()
li = base_index(sg_live, LIVE, "US")
fan_path = [round(float(sg_live.iloc[li + k] / sg_live.iloc[li] - 1) * 100, 1) for k in range(0, len(sg_live) - li, 6)]
print(f"  fan path so far (US shares in SGD, every 6 sessions, {len(fan_path)} points, "
      f"as at {sg_live.index[li + 6 * (len(fan_path) - 1)].date()}): {fan_path}")

# ------------------------------------------------------------------ 4. checks against the article
print("\nCHECKS AGAINST THE PUBLISHED FIGURES")
print("US shares, US dollars")
for lab, med, up, base, bup in [("1M", -2.53, 1, 1.33, 64), ("3M", -3.71, 1, 3.41, 70), ("6M", 4.25, 4, 6.16, 74), ("12M", 6.54, 4, 12.78, 79)]:
    check(f"{lab} median %", spx_usd[lab]["med"], med); check(f"{lab} higher, of 6", spx_usd[lab]["up"], up, 0)
    check(f"{lab} usual median %", spx_usd[lab]["base"], base); check(f"{lab} usual share higher %", spx_usd[lab]["bup"], bup, 1)
print("US shares, Singapore dollars")
for lab, med, up, base, bup in [("1M", -2.19, 1, 1.14, 62), ("3M", -4.34, 1, 3.07, 66), ("6M", -0.27, 3, 5.38, 71), ("12M", 6.50, 4, 10.31, 78)]:
    check(f"{lab} median %", spx_sgd[lab]["med"], med); check(f"{lab} higher, of 6", spx_sgd[lab]["up"], up, 0)
    check(f"{lab} usual median %", spx_sgd[lab]["base"], base); check(f"{lab} usual share higher %", spx_sgd[lab]["bup"], bup, 1)
print("STI")
for lab, med, up, base, bup in [("1M", -2.40, 2, 0.56, 56), ("3M", -4.74, 2, 1.32, 58), ("6M", -1.71, 2, 2.29, 59), ("12M", -4.75, 2, 3.15, 57)]:
    check(f"{lab} median %", sti_c[lab]["med"], med); check(f"{lab} higher, of 6", sti_c[lab]["up"], up, 0)
    check(f"{lab} usual median %", sti_c[lab]["base"], base); check(f"{lab} usual share higher %", sti_c[lab]["bup"], bup, 1)
print("Gold, Singapore dollars, monthly averages")
for lab, med, up, base, bup in [("1M", 0.09, 4, 0.17, 52), ("3M", -1.07, 3, 0.98, 57), ("6M", 1.46, 3, 2.89, 63), ("12M", 2.10, 3, 5.70, 68)]:
    check(f"{lab} median %", gold_sgd[lab]["med"], med); check(f"{lab} higher, of 6", gold_sgd[lab]["up"], up, 0)
    check(f"{lab} usual median %", gold_sgd[lab]["base"], base); check(f"{lab} usual share higher %", gold_sgd[lab]["bup"], bup, 1)
print("Gold, US dollars, monthly averages (the chart in the piece)")
for lab, med, up, base in [("1M", -0.02, 3, 0.11), ("3M", 0.64, 3, 1.28), ("6M", 3.95, 3, 3.45), ("12M", 3.11, 3, 6.21)]:
    check(f"{lab} median %", gold_usd[lab]["med"], med); check(f"{lab} higher, of 6", gold_usd[lab]["up"], up, 0)
    check(f"{lab} usual median %", gold_usd[lab]["base"], base)
print("Gold, US dollars: the one date that changes the answer (six months)")
check("five hikes (1997 dropped), median %", gold_five["6M"]["med"], 8.43)
print("The dollar leg (USD/SGD)")
check("6M after, median %", usdsgd["6M"]["med"], -3.03); check("6M after, Singapore dollar weaker, of 6", usdsgd["6M"]["up"], 2, 0)
check("6M usual median %", usdsgd["6M"]["base"], -0.44)
for y, want in [(1994, -5.0), (1997, 5.5), (1999, -2.2), (2004, -4.3), (2015, -3.8), (2022, 2.9)]:
    check(f"6M after {y} %", usdsgd["6M"]["per"][[e.year for e in EVENTS].index(y)], want)
for y, want in [(1994, -1.7), (1997, 2.2), (1999, 2.8), (2004, 0.7), (2015, 4.7), (2022, 1.8), (2026, -1.2)]:
    check(f"6M before {y} %", pre["fx"][y], want)
print("Six-month outcomes per hike, Singapore dollars")
for y, want in [(1994, -9.8), (1997, 28.3), (1999, 5.5), (2004, 1.8), (2015, -2.3), (2022, -4.8)]:
    check(f"US shares in SGD, 6M after {y} %", spx_sgd["6M"]["per"][[e.year for e in EVENTS].index(y)], want)
for y, want in [(1994, -5.7), (1997, -3.2), (1999, 6.1), (2004, 7.9), (2015, 14.0), (2022, -10.2)]:
    check(f"gold in SGD, 6M after {y} %", gold_sgd["6M"]["per"][[e.year for e in EVENTS].index(y)], want)
for y, want in [(1994, -3.6), (1997, -8.8), (1999, 13.5), (2004, 11.6), (2015, -2.7), (2022, -0.7)]:
    check(f"STI, 6M after {y} %", sti_c["6M"]["per"][[e.year for e in EVENTS].index(y)], want)
print("Run-ups into the hike and the day itself")
check("S&P 500, six months into 16 Sep 2026, %", pre["spx"][2026], 13.2)
check("STI, six months into 16 Sep 2026, %", pre["sti"][2026], 14.2)
check("gold futures, six months into 16 Sep 2026, %", pre["gcf"][2026], -13.4)
check("gold fell into the hike (monthly), count of 6", sum(1 for y, x in pre["gold_m"].items() if x < 0), 4, 0)
check("dollar rose into the hike, count of 6", sum(1 for y, x in pre["fx"].items() if y != 2026 and x > 0), 5, 0)
check("S&P 500 on 16 Sep 2026, %", day[2026], -0.45, 0.05)
check("gold futures 6M after 2015, %", gold_fut["6M"]["per"][1], 21.9)
check("gold futures 6M after 2022, %", gold_fut["6M"]["per"][2], -11.4)
check("gold futures 6M after 2004, %", gold_fut["6M"]["per"][0], 11.1)

print("\n" + ("ALL FIGURES REPRODUCED." if ok else "SOMETHING DID NOT MATCH — please tell us."))
