// Singapore property duty schedules — the arithmetic behind the right-size tool.
//
// EVERY rate here was verified against IRAS primary pages on 2026-07-28. Do not
// edit a number without re-checking the source and updating the date beside it.
// Rates change at budget and cooling-measure announcements, historically without
// a transition period.

export interface BsdBand { upTo: number | null; rate: number }

/**
 * Buyer's Stamp Duty — residential.
 * Source: IRAS, "Buyer's Stamp Duty (BSD)" (page last updated 27 Jul 2026).
 * Schedule in force since 15 Feb 2023.
 * https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/buyer's-stamp-duty-(bsd)
 */
export const BSD_BANDS: BsdBand[] = [
  { upTo:   180_000, rate: 0.01 },
  { upTo:   360_000, rate: 0.02 },   // next 180,000
  { upTo: 1_000_000, rate: 0.03 },   // next 640,000
  { upTo: 1_500_000, rate: 0.04 },   // next 500,000
  { upTo: 3_000_000, rate: 0.05 },   // next 1,500,000
  { upTo: null,      rate: 0.06 },   // remainder
];

/** BSD is payable on HDB flats exactly as on private property — IRAS FAQ, same page. */
export function buyersStampDuty(price: number): number {
  if (!(price > 0)) return 0;
  let duty = 0;
  let lower = 0;
  for (const band of BSD_BANDS) {
    const upper = band.upTo ?? Infinity;
    if (price > lower) duty += (Math.min(price, upper) - lower) * band.rate;
    lower = upper;
    if (price <= upper) break;
  }
  return Math.floor(duty);
}

/**
 * Seller's Stamp Duty — residential.
 * Source: IRAS, "Seller's Stamp Duty (SSD) for Residential Property"
 * (page last updated 20 Feb 2026). Schedule in force since 4 Jul 2025, which
 * extended the holding period from 3 to 4 years and raised each tier by 4pp.
 * https://www.iras.gov.sg/taxes/stamp-duty/for-property/selling-or-disposing-property/seller's-stamp-duty-(ssd)-for-residential-property
 */
export const SSD_BANDS = [
  { heldUpToYears: 1, rate: 0.16 },
  { heldUpToYears: 2, rate: 0.12 },
  { heldUpToYears: 3, rate: 0.08 },
  { heldUpToYears: 4, rate: 0.04 },
];

/** Rate only — caller supplies the holding period in years at the point of sale. */
export function sellersStampDutyRate(yearsHeld: number): number {
  for (const band of SSD_BANDS) {
    if (yearsHeld <= band.heldUpToYears) return band.rate;
  }
  return 0;
}

export function sellersStampDuty(price: number, yearsHeld: number): number {
  return Math.floor(Math.max(0, price) * sellersStampDutyRate(yearsHeld));
}

/**
 * Additional Buyer's Stamp Duty.
 * Source: IRAS, "Additional Buyer's Stamp Duty (ABSD)" (page last updated
 * 2 Jun 2026). Rates in force since 27 Apr 2023.
 * https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/additional-buyer's-stamp-duty-(absd)
 *
 * Modelled only for the two profiles this tool serves — a Singapore Citizen or
 * Singapore PR buying an HDB resale flat. Foreigners and entities cannot buy
 * HDB flats, so those rates are deliberately absent rather than unused.
 */
export const ABSD = {
  sc:  { first: 0,    second: 0.20, third: 0.30 },
  spr: { first: 0.05, second: 0.30, third: 0.35 },
} as const;

export type BuyerProfile = 'sc' | 'spr';

/**
 * ABSD on an HDB resale flat bought while a private property is still held.
 *
 * IRAS grants the remission UPFRONT for HDB resale purchases, because HDB's own
 * rules require disposal of all private property within 6 months of completion
 * — so the buyer pays at their post-disposal count, not their current count.
 * IRAS FAQ, ABSD page: an SPR downgrading from a private apartment "only need[s]
 * to pay ABSD at 5% instead of 30%".
 *
 * The remission is CONDITIONAL. Miss the disposal deadline and the difference
 * becomes payable, which is the largest single risk in the whole move — hence
 * `atRiskIfNotDisposed`.
 */
export function absdOnResaleFlat(price: number, profile: BuyerProfile, stillOwnsPrivate: boolean) {
  const table = ABSD[profile];
  const remittedRate = table.first;                       // treated as first property
  const fullRate     = stillOwnsPrivate ? table.second : table.first;
  const payableNow   = Math.floor(Math.max(0, price) * remittedRate);
  const withoutRemission = Math.floor(Math.max(0, price) * fullRate);
  return {
    remittedRate,
    fullRate,
    payableNow,
    atRiskIfNotDisposed: Math.max(0, withoutRemission - payableNow),
  };
}

/**
 * CPF Ordinary Account interest rate, 1 Jul 2026 – 30 Sep 2026.
 * Source: CPF Board, "Earning attractive interest" (banner states the quarter).
 * https://www.cpf.gov.sg/member/growing-your-savings/earning-higher-returns/earning-attractive-interest
 *
 * Used ONLY to estimate accrued interest where the reader has not yet pulled the
 * exact figure from their CPF statement. CPF computes accrued interest on the
 * actual withdrawal profile over time; this yearly-compounded approximation on a
 * single principal is deliberately labelled as an estimate in the interface.
 */
export const CPF_OA_RATE = 0.025;

export function estimateAccruedInterest(principal: number, years: number): number {
  if (!(principal > 0) || !(years > 0)) return 0;
  return Math.round(principal * (Math.pow(1 + CPF_OA_RATE, years) - 1));
}

/**
 * Minimum remaining lease for ANY CPF usage on a purchase: 20 years.
 * Sources: CPF Board service article on pro-rated usage, and HDB "Mode of
 * financing" (last updated 24 Jul 2026), both conditioning usage on a remaining
 * lease of at least 20 years that covers the youngest buyer to age 95.
 *
 * NOTE: where the lease does NOT cover the youngest buyer to 95, usage is
 * pro-rated — but neither CPF nor HDB publishes the formula, only a worked
 * example. We therefore do NOT compute pro-rated usage anywhere in this tool;
 * we flag the condition and send the reader to CPF's own calculator.
 */
export const CPF_MIN_REMAINING_LEASE_YEARS = 20;
export const CPF_LEASE_COVERAGE_AGE = 95;
