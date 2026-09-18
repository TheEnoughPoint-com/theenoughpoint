// ─── Observed cashback rates, dated ──────────────────────────────────────────
// The memory behind /cashback-calendar's rate table. Rate pages show today and
// remember nothing; this file is the history nobody else in Singapore keeps.
//
// Append-only, in chronological order: every time a ShopBack rate is verified
// for a piece or a real booking, add one reading at the end with the date it
// was read. Never edit an old reading to "correct" it — a reading is what the
// page said on that day, and the drift is the point.

export interface RateReading {
  /** ISO date the rate was read off the page or dashboard (YYYY-MM-DD) */
  date: string;
  /** Store name as ShopBack lists it */
  store: string;
  /** The tier the rate applies to, as the merchant page names it */
  tier: string;
  /** Display rate, e.g. "14%" — a string because rates come in odd shapes
   *  ("up to S$35" for flat-amount insurance offers) */
  rate: string;
  /** everyday = the standing rate on the merchant page;
   *  upsized  = a campaign window we actually caught, not a ceiling */
  kind: 'everyday' | 'upsized';
  /** One line of context: what was running, or what we did with it */
  note: string;
  /** Where the reading came from — a merchant page, or our own dashboard */
  source: { label: string; href: string };
}

export const rateLog: RateReading[] = [
  {
    date: '2026-07-25',
    store: 'Trip.com',
    tier: 'hotels',
    rate: '14%',
    kind: 'upsized',
    note: 'Payday-window upsize, roughly three times the everyday 4.5% — our S$468.01 stay returned S$65.52.',
    source: { label: 'our booking, in the routing guide', href: '/shopback-used-properly/' },
  },
  {
    date: '2026-08-06',
    store: 'Booking.com',
    tier: 'stays',
    rate: '5.5%',
    kind: 'everyday',
    note: 'Confirms up to 70 days after the trip ends.',
    source: { label: 'merchant page', href: 'https://www.shopback.sg/booking-com' },
  },
  {
    date: '2026-08-06',
    store: 'Trip.com',
    tier: 'hotels',
    rate: '4.5%',
    kind: 'everyday',
    note: 'Confirms up to 120 days after the trip ends.',
    source: { label: 'merchant page', href: 'https://www.shopback.sg/trip-com' },
  },
  {
    date: '2026-08-06',
    store: 'Agoda',
    tier: 'hotels',
    rate: '4.5%',
    kind: 'everyday',
    note: 'Confirms up to 120 days after the trip ends.',
    source: { label: 'merchant page', href: 'https://www.shopback.sg/agoda' },
  },
  {
    date: '2026-08-06',
    store: 'Klook',
    tier: 'hotels',
    rate: '6%',
    kind: 'everyday',
    note: 'The fattest everyday hotel rate of the four portals; confirms up to 120 days after the trip ends.',
    source: { label: 'merchant page', href: 'https://www.shopback.sg/klook' },
  },
  {
    date: '2026-08-06',
    store: 'Shopee',
    tier: 'existing customers',
    rate: 'token rate',
    kind: 'everyday',
    note: 'The headline rate is new-customer only; the routing guide recorded the condition, not a figure.',
    source: { label: 'merchant page', href: 'https://www.shopback.sg/shopee-web' },
  },
  {
    date: '2026-08-06',
    store: 'Lazada',
    tier: 'existing customers',
    rate: '~1%',
    kind: 'everyday',
    note: 'Capped at S$3 per purchase; items already in the cart before the click-through are excluded.',
    source: { label: 'merchant page', href: 'https://www.shopback.sg/lazada' },
  },
  {
    date: '2026-09-18',
    store: 'Shopee',
    tier: 'new customers',
    rate: '3.8%',
    kind: 'everyday',
    note: 'First reading of this tier as a figure. Capped at S$1.27 per item. Tracked in 2 days, confirmed in 20.',
    source: { label: 'merchant page', href: 'https://www.shopback.sg/shopee-web' },
  },
  {
    date: '2026-09-18',
    store: 'Shopee',
    tier: 'existing customers',
    rate: '0.1%',
    kind: 'everyday',
    note: 'From "token rate" (6 Aug 2026), which recorded the condition but never a number — the page now states 0.1%, capped at S$3 per item.',
    source: { label: 'merchant page', href: 'https://www.shopback.sg/shopee-web' },
  },
  {
    date: '2026-09-18',
    store: 'Lazada',
    tier: 'all customers',
    rate: '0.1%',
    kind: 'everyday',
    note: 'From "~1%, capped S$3 per purchase" for existing customers (6 Aug 2026). The floor tier is now named "All Customers" at 0.1%, capped S$3 per order, with category tiers stacked above it — 1% on Mobiles & Tablets (capped S$7 per order) and on the beauty/home/baby group, 8% on selected beauty brands. A flat reading has become a category structure, and the cap moved from per purchase to per order. Tracked in 3 days, confirmed in 75.',
    source: { label: 'merchant page', href: 'https://www.shopback.sg/lazada' },
  },
  {
    date: '2026-09-18',
    store: 'iHerb',
    tier: 'all customers',
    rate: '0.5%',
    kind: 'everyday',
    note: 'First reading. A 7% campaign was running over it, ending 19 Sep 2026; 0.5% is the standing rate underneath. Tracked in 2 days, confirmed in 40.',
    source: { label: 'merchant page', href: 'https://www.shopback.sg/iherb' },
  },
  {
    date: '2026-09-18',
    store: 'FWD Insurance',
    tier: 'per policy',
    rate: 'up to S$35',
    kind: 'everyday',
    note: 'First reading. A flat amount per policy, by product: CI Plus S$35, Term Life Plus S$22, Cancer 100 and Big 3 Critical Illness S$20, Cancer S$15, Maid and Annual Trip Travel S$12, FWD Flex and Home S$10, Single Trip Travel S$3. Tracked in 2 days, confirmed in 90.',
    source: { label: 'merchant page', href: 'https://www.shopback.sg/fwd-insurance-promo-code' },
  },
  {
    date: '2026-09-18',
    store: 'Golden Village',
    tier: 'standard movies',
    rate: '4%',
    kind: 'everyday',
    note: 'First reading. Capped at S$2 per item. Tracked in 2 days, confirmed in 45.',
    source: { label: 'merchant page', href: 'https://www.shopback.sg/golden-village' },
  },
];
