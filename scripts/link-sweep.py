"""link-sweep.py — every link on the built site, checked.

Run from the repo root after a build:

    python scripts/link-sweep.py             # offline checks, fast
    python scripts/link-sweep.py --external  # also probe every external URL

Exit code 0 means clean; 1 means something below needs a human.

WHY THIS EXISTS
Each check earned its place on 22 Aug 2026, the day a reader's WhatsApp
compose box surfaced a share link whose prefilled text began with the literal
word "undefined" — live, on four articles, invisible to the build, the static
checker and the render audit of the day.

WHAT IT CHECKS
1. Defect patterns inside href/src values: serialised undefined/null/NaN,
   localhost, double-encoded %2520, [object. These are always bugs.
   (Case-sensitive on NaN deliberately: the first run of this sweep reported
   307 defects, every one a case-insensitive "NaN" matching inside the word
   "fiNANce". A checker that cries wolf gets ignored.)
2. Internal integrity: every root-relative link resolves to a built page or
   file in dist/.
3. Share-link sanity: every article's WhatsApp link carries a real title
   before its URL.
4. Host consistency: absolute self-references should all use one host form.
   (The site canonicalises on the apex; a stray www link is drift.)
5. --external only: HEAD/GET every unique external URL. Known bot-walls
   (Bloomberg, SSRN, and friends) are reported separately, not failed — a 403
   from them is not proof the link is broken for a reader; verify those by
   hand when they are load-bearing. Transient 5xx: re-run before believing it.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

DIST = Path(__file__).resolve().parent.parent / "dist"
CANONICAL_HOST = "theenoughpoint.com"          # apex, per every canonical tag
WRONG_SELF = re.compile(r"https?://www\.theenoughpoint\.com")

BOT_BLOCKERS = ("bloomberg.com", "papers.ssrn.com", "schwab", "cnbc.com",
                "x.com", "twitter.com", "linkedin.com", "facebook.com",
                "fortune.com", "seekingalpha", "wsj.com", "axios.com",
                "qz.com", "mas.gov.sg", "fred.stlouisfed.org")

# URLs a script cannot fetch that a person has confirmed work in a browser.
# Reported, never failed. Re-verify by hand if one of these becomes
# load-bearing again, and prune entries when the citing article retires.
HAND_VERIFIED = {
    "https://www.kedglobal.com/korean-stock-market/newsView/ked202605270003":
        "intermittent 502s from their edge; loads in a browser (verified 22 Aug 2026)",
    "https://www.lionglobalinvestors.com/en/fund-lionglobal-singapore-physical-gold-etf.html":
        "cookie-wall redirect loop for scripted clients; loads in a browser (verified 22 Aug 2026)",
    "https://www.bls.gov/news.release/cpi.nr0.htm":
        "403 to scripted clients; loads in a browser (verified 2 Oct 2026)",
    "https://www.sec.gov/Archives/edgar/data/884394/000119312526022775/d77353d497.htm":
        "EDGAR 403s clients without a declared user agent; loads in a browser (verified 2 Oct 2026)",
}

href_re = re.compile(r'(?:href|src)="([^"]+)"')
bad_re = re.compile(
    r"undefined|(?<![a-zA-Z])null(?![a-zA-Z])|(?<![a-zA-Z])NaN(?![a-zA-Z])"
    r"|\[object|localhost|%2520")


def sweep():
    if not DIST.exists():
        print("dist/ not found — run `npm run build` first.")
        return 2
    pages = sorted(DIST.glob("**/index.html")) + [
        p for p in DIST.glob("*.html") if p.name != "index.html"]

    defects, missing, share_bad, host_drift = [], [], [], []
    externals = set()

    for page in pages:
        rel = str(page.relative_to(DIST))
        html = page.read_text(encoding="utf-8", errors="replace")
        for m in href_re.finditer(html):
            url = m.group(1)
            if url.startswith("data:"):
                continue
            if bad_re.search(url):
                defects.append((rel, url[:110]))
            if url.startswith(("http://", "https://")):
                if CANONICAL_HOST in url:
                    if WRONG_SELF.search(url):
                        host_drift.append((rel, url[:110]))
                else:
                    externals.add(url.split("#")[0])
                continue
            if url.startswith(("mailto:", "#", "tel:")):
                continue
            if url.startswith("/"):
                path = unquote(url.split("#")[0].split("?")[0]).lstrip("/")
                if path:
                    cand = DIST / path
                    if not (cand.exists() or (cand / "index.html").exists()):
                        missing.append((rel, url[:110]))

        wa = re.search(r'https://api\.whatsapp\.com/send\?text=([^"]*)', html)
        if wa and not re.search(r"[A-Za-z]{3,}.*https?://", unquote(wa.group(1))):
            share_bad.append((rel, unquote(wa.group(1))[:110]))

    failed = False
    for name, items in [
        ("defect-pattern hrefs (undefined/null/NaN/localhost/%2520)", defects),
        ("internal links with no built target", sorted(set(missing))),
        ("share links missing a title", share_bad),
        ("self-references on the wrong host form", sorted(set(host_drift))),
    ]:
        print(f"== {name}: {len(items)}")
        for it in items[:15]:
            print("   ", it)
        failed = failed or bool(items)

    print(f"== unique external links: {len(externals)}")

    if "--external" in sys.argv:
        failed = check_externals(sorted(externals)) or failed

    print("\nCLEAN." if not failed else "\nISSUES FOUND — see above.")
    return 1 if failed else 0


def check_externals(urls):
    import concurrent.futures as cf
    import requests

    ua = {"User-Agent": "Mozilla/5.0 (link check; TheEnoughPoint editorial)"}

    def probe(url):
        try:
            r = requests.head(url, headers=ua, timeout=15, allow_redirects=True)
            if r.status_code in (403, 404, 405, 501):
                r = requests.get(url, headers=ua, timeout=20,
                                 allow_redirects=True, stream=True)
                r.close()
            return url, r.status_code
        except Exception as e:  # noqa: BLE001 — the name is the diagnosis
            return url, type(e).__name__

    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        results = sorted(ex.map(probe, urls), key=str)

    ok = [r for r in results if isinstance(r[1], int) and r[1] < 400]
    rest = [r for r in results if r not in ok]
    verified = [r for r in rest if r[0] in HAND_VERIFIED]
    blocked = [r for r in rest if r not in verified
               and any(b in r[0] for b in BOT_BLOCKERS)]
    broken = [r for r in rest if r not in verified and r not in blocked]

    print(f"\n== external: {len(ok)} OK")
    print(f"== external, hand-verified exceptions: {len(verified)}")
    for u, s in verified:
        print(f"   {s}  {u[:80]} — {HAND_VERIFIED[u]}")
    print(f"== external, likely bot-wall (verify by hand if load-bearing): {len(blocked)}")
    for u, s in blocked:
        print(f"   {s}  {u[:100]}")
    print(f"== external, broken or suspect (re-run once before believing a 5xx): {len(broken)}")
    for u, s in broken:
        print(f"   {s}  {u[:110]}")
    return bool(broken)


if __name__ == "__main__":
    sys.exit(sweep())
