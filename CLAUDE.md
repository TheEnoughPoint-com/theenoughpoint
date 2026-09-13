# TheEnoughPoint.com — Claude Instructions

This is TheEnoughPoint.com, a Singapore-born personal finance media site.

## Brand positioning

TheEnoughPoint helps financially aware Singaporeans and Asia-based readers invest better, build optional income, spend with value, and reach their own “enough point” by 40ish.

## Brand tone

- Trustworthy
- Calm
- Practical
- Relatable
- Singapore-aware
- Financially literate but not intimidating
- No hype
- No get-rich-quick language

## Long-form clarity and density

For a decision article, state the actual choice in the opening 120 words. Do
not spend several sections rephrasing the same framing before reaching the
trade-off.

- Give each section one distinct job: explain the mechanism, name a trade-off,
  show a calculation, or give the reader a decision check. If a paragraph does
  none of these, cut it.
- Put non-load-bearing method detail, repeated caveats and source defence in a
  fold or sources block. Keep only the assumption that materially changes the
  conclusion in the body.
- Use one plain-English translation after a technical passage. Do not restate
  the same conclusion again in the summary, conclusion and tool introduction.
- For a normal explanatory article, aim for 1,200–1,600 words of body copy,
  excluding sources, tables and interactive-tool labels. Go longer only when
  original reporting or a calculation needs the space.
- Before requesting review, run a density pass: state the article's decision in
  one sentence, identify the three most useful reader takeaways, then delete
  duplicate framing and any paragraph that does not change understanding,
  options or action.

The intended reader is smart but busy. Rigour is shown through a checkable
calculation and a clear boundary, not by making the reader carry the full audit
trail through the article.

## Visual direction

Adapt the Astromag theme toward the reference mockup:
- Deep navy header
- Jade / teal primary accent
- Warm gold for highlights
- Ivory or soft off-white background
- Rounded content cards
- Clean magazine-style article pages
- Right sidebar on desktop
- Mobile-first responsive layout

## Core content pillars

1. Build Enough
   - FIRE roadmap
   - CPF, SRS, HDB, retirement planning
   - How much is enough

2. Invest Better
   - Brokerages
   - ETFs, REITs, T-bills, SSBs
   - Financial product reviews
   - Platform comparisons

3. Optional Income
   - Side hustles
   - Small business experiments
   - Acquisitions
   - Income streams

4. Spend With Value
   - Cheap hunts
   - Lifestyle optimisation
   - Family spending
   - Smart purchases

## Authors

Use anonymous author identities:
- FI: investing, risk, CPF/SRS, portfolio frameworks, product analysis
- RE: semi-retirement, business experiments, lifestyle design, value living

## Compliance rules

- Do not present personalised financial advice.
- Do not say “you should buy/sell/hold”.
- Do not create target prices.
- Do not create model portfolios unless clearly labelled hypothetical.
- Sponsored content must be clearly labelled.
- Affiliate links must include disclosure.
- Add the disclosure component to all review/comparison articles.
- Avoid implying that FI’s employer endorses any view.
- Views are personal and educational only.

## Technical rules

- Keep components reusable.
- Prefer MDX content files.
- Use Astro content collections where available.
- Do not hardcode repeated article lists if they can be driven from frontmatter or data files.
- Keep styling centralised in Tailwind/CSS variables.
- Make all changes through branches and pull requests unless asked otherwise.
- **Run `/preflight` before opening a PR for any new or rewritten article, and
  again before merging.** It measures the rendered page at 390 / 768 / 1280 for
  overflow, contrast, fused words and jargon, then walks the editorial checks a
  script cannot make. The build passing and `check_page.py` passing have both
  coexisted with defects that reached production; the assertions live in
  `scripts/render-audit.js` and grow each time something gets through.
- **Verify against the live DOM, not the built HTML.** Anything a component
  renders with JavaScript does not exist in `dist/*.html`, so grepping the file
  will clear a page that is visibly wrong on screen.
- Deployment is automatic: merging a PR into `main` triggers GitHub Actions,
  which builds and deploys to Cloudflare Pages via `cloudflare/wrangler-action`
  (see `.github/workflows/deploy.yml`), authenticated with the
  `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` repo secrets. No manual step
  needed for normal publishing. Cloudflare's own "Automatic deployments" is
  paused on the project to avoid two systems deploying the same push.
- The deploy workflow gates on `python scripts/seo-audit.py` and the offline
  `python scripts/link-sweep.py` between build and deploy: titles,
  descriptions, canonical ↔ sitemap agreement, alt text, structured data and
  internal links. A red deploy keeps the previous version live — read the
  Actions log, fix on a branch, merge again. Run both gates locally after
  `npm run build` before merging; `/preflight` includes them.
- Emergency fallback only, if the Actions deploy ever fails: run these two
  lines locally from an up-to-date `main` (needs `wrangler login` or a
  `CLOUDFLARE_API_TOKEN` env var with Cloudflare Pages: Edit permission):
  - `npm run build`
  - `npx wrangler pages deploy dist --project-name=theenoughpoint --branch=main`
