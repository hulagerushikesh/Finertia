# Payments — research and plan

_Drafted 24 Oct 2026 (PM + Backend + Cloud). Research only: nothing here is
switched on, signed or paid for, and none of it is legal or tax advice. The
questions marked **CA / counsel** go into the legal brief (NEXT-MILESTONE item
4) and to a chartered accountant before anything goes live._

## The gates are unchanged

Charging starts only when all three hold (DECISIONS 8 Oct and 13 Oct):

1. Phase 4 reads **two or more clear "would pay"** (decided by 1 Nov).
2. The **legal check** is done: SEBI positioning, DPDP, and Terms and Privacy pages published.
3. **Licensed data** is in place behind `PRICE_PROVIDER` (the data sprint).

This plan is written now so that, if the gates open, the payment work is
a choice already made, not fresh research. If phase 4 reads Portfolio or
Education, this document is shelved as is.

## What exists today

- `backend/billing.py`: Stripe Checkout (subscription mode), a hand-written
  webhook signature check (constant time, 5-minute replay window, secret
  rotation), and `plan_from_event` mapping four event types to free/pro.
- `POST /api/billing/checkout`, `POST /api/billing/webhook`; the uid travels
  in checkout and subscription metadata.
- All env-gated: with no `STRIPE_SECRET_KEY`, `/api/plans` says
  `billing_enabled: false` and Pricing shows Pro as "Coming soon".
- `DELETE /api/me` refuses while a Stripe-sourced Pro is active.
- Price: **$12 / month**, one plan (`plans.py`). DECISIONS 8 Oct asks testers
  about "₹1,000 / $12", so INR is already the price most testers hear.

**Gaps in the existing code, found in this review**, to fix whichever provider
is chosen:

| # | Gap | Why it matters |
|---|---|---|
| G1 | No record of processed event IDs | Providers retry webhooks. A replayed old `updated(active)` after a `deleted` would grant Pro again |
| G2 | Events applied in arrival order | Delivery order is not guaranteed. The safe pattern is to treat an event as a nudge and read the subscription's current state from the provider |
| G3 | `checkout.session.completed` grants Pro without checking `payment_status` | Async methods (UPI, bank debits) complete the session before the money arrives |
| G4 | No customer or subscription ID stored on the user | No way to open a billing portal, refund, or reconcile; a user who changes email is lost |
| G5 | No self-serve cancel | Pricing promises "Cancel any time". There must be a portal link in Profile. RBI rules also require an easy opt-out for Indian cards |
| G6 | Disputes, refunds and failed renewals are not handled | A charged-back or unpaid user keeps Pro |
| G7 | One USD price | Indian buyers pay FX on top, and UPI needs INR |
| G8 | Redirects use `ALLOWED_ORIGINS[0]` | Fine today; brittle after B1 or with a preview origin. Use a dedicated `PUBLIC_ORIGIN` |

## The constraint that decides most of it: where the seller is

The author sells as an individual in India. That rules some options in and
others out.

### Stripe directly

- New Indian accounts have been **invite-only since May 2024**. Applicants
  must be a registered business (a sole proprietorship counts; an individual
  does not). Since **1 Jan 2026** onboarding includes **video KYC**.
  International cards need an **Import Export Code** as well.
- Recurring Indian cards fall under the RBI e-mandate rules (below), which
  Stripe India supports but which lower renewal success.
- **Stripe Managed Payments** (Stripe as merchant of record, generally
  available 2026) is reported as **not open to India-based sellers**.
  Confirm on Stripe's eligibility page; the sources disagree in places.
- Verdict: the existing code targets the provider that is hardest for this
  seller to get. Keep the code as one implementation, not as the plan.

### Indian gateways (Razorpay as the example; Cashfree and PayU are similar)

- Domestic gateway about **2% + 18% GST** on the fee; **subscriptions add
  0.99%**. International cards **3% + GST**, enabled separately.
- Native **UPI AutoPay** and card e-mandates, INR settlement, fast payouts.
- Needs business KYC (PAN, bank account, a website with Terms, Privacy,
  Refund and Contact pages, which we do not have yet).
- **Finertia becomes the seller of record everywhere.** That means GST in
  India, and for foreign buyers: EU/UK VAT, and sales tax in the US states
  that tax SaaS, all registered for and filed by the author. For one person
  that is the real cost, not the 3%.

### Merchant of record (MoR)

The MoR is the legal seller to the customer. It collects and files consumer
tax worldwide, handles disputes and fraud, and pays the author out.

| | Headline fee | On a $12 international subscription* | India-specific | Notes |
|---|---|---|---|---|
| **Dodo Payments** | 4% + $0.40; +0.5% subscriptions; +1.5% non-US cards | ≈ 6% + $0.40 ≈ **$1.12 (9.3%)** | India-founded; **UPI** at an India-domestic rate (4% + $0.15) | Payout fee wording conflicts on its own page ($0 vs $5 under $1,000; $25 SWIFT); most comparisons that rank it first are its own blog |
| **Paddle** | 5% + $0.50 | ≈ **$1.10 (9.2%)** | India not on the block list, but every seller is reviewed; **no INR payouts**; UPI only for one-time USD items, **not subscriptions** | $100 payout minimum, monthly payouts |
| **Lemon Squeezy** | 5% + $0.50 | ≈ $1.10 | — | Stripe-owned; announced a move onto Stripe Managed Payments (Jan 2026), so India eligibility may follow Stripe's |
| **Polar** | 5% + $0.50 (free tier); ~3.8% + $0.40 at $20/mo | ≈ $1.10 | — | Pricing changed in 2026; aimed at developers |
| _Razorpay (not MoR)_ | 3% + 0.99% + GST on fees | ≈ **$0.56 (4.7%)** | UPI AutoPay, INR | Plus the author's own global tax compliance |

\* Before FX spread and payout fees. Figures from vendors' public pages and
third-party comparisons on 24 Oct 2026. **List prices to confirm in
writing**, as with the data quotes.

### RBI rules any Indian recurring payment has to follow

- The mandate is set up with additional authentication (OTP or similar).
- Renewals **up to ₹15,000** then run without it. Pro is well under that.
- The cardholder gets a **pre-debit notice at least 24 hours** before each
  charge, and can cancel the mandate.
- The provider does all three. Our side: show the renewal date, and make
  cancelling as easy as subscribing (G5).

### Tax, briefly (CA / counsel)

- Domestic B2C SaaS: **18% GST**. Registration becomes compulsory above
  **₹20 lakh** turnover a year; below that it is optional.
- Sales abroad can be a **zero-rated export** under a Letter of Undertaking,
  which needs GST registration.
- With an MoR, the author's sale is arguably to the MoR, not the end user.
  How that is treated for GST and FEMA (foreign inward remittance, FIRC) is
  the main question for the CA.
- Income tax on the payouts either way.

## Recommendation

**A merchant of record, with Dodo Payments as the first application and
Paddle as the fallback. Keep Stripe as code, not as the plan.**

- **Why MoR:** at 20–30 paying users (the break-even in DECISIONS 13 Oct),
  the extra ~$0.55 a sale is ~₹1,000–1,500 a month. Registering and filing
  VAT and sales tax abroad costs more than that in time and fees.
- **Why Dodo first:** it is the one MoR here that accepts Indian sellers by
  design and takes UPI for Indians, and most testers are Indian.
- **Why Paddle second:** it is established, but approval is uncertain, it
  pays out in other currencies, and its UPI does not cover subscriptions.
- **Revisit Razorpay** if paying users turn out to be mostly Indian and the
  author has GST-registered anyway. At that point the MoR premium buys little.
- **Prices:** two, set in the provider: **₹999 / month** for India and
  **$12 / month** elsewhere. The MoR picks one by the buyer's location. `plans.py`
  keeps the entitlement; the provider holds the price. Sign-off by the author.

## Build plan (only once the gates open)

Each step is a PR, merged on green CI. Anything touching production waits for
the author's yes, as now.

| Step | What | Done when |
|---|---|---|
| P0 — Author | Apply to Dodo (and Paddle in parallel; approval takes days). Ask the CA the tax questions above. Decide sole proprietorship or individual | A sandbox account exists. The author sets the keys as secrets; Claude never sees them |
| P1 — Seam | `billing/` package: a `Provider` interface (`checkout_url`, `portal_url`, `verify_webhook`, `subscription_state`), `stripe.py` (today's code moved, no behaviour change) and `dodo.py`, chosen by `BILLING_PROVIDER`. Same pattern as `PRICE_PROVIDER` | Existing billing tests pass unchanged against `stripe` |
| P2 — Correctness | G1–G4, G6: store `billing.customerId`, `subscriptionId`, `status`, `currentPeriodEnd` on the user (server-only fields; Firestore rules updated and tested). Keep processed event IDs (TTL 30 days). On each event, read the subscription's current state from the provider, then set the plan. Grant Pro only on `active` / `trialing` with payment confirmed. Downgrade on dispute, refund or end of period | Unit tests per event, including replayed, out-of-order and duplicate events. Emulator test that the rules refuse client writes to `billing.*` |
| P3 — Product | Pricing: "Upgrade" goes to the provider's checkout. Profile: plan, renewal date, "Manage billing" (the provider portal), which closes G5. Account deletion: cancel first, then delete, which replaces today's 409. Behind a `billing` feature switch | Vitest plus an E2E against a fake provider (a local stub serving checkout and signed webhooks). No real network in CI |
| P4 — Pages | Terms, Privacy, **Refund policy**, Contact, from the legal consult. Providers check these during KYC | Pages live; footer links |
| P5 — Sandbox run | Full loop on the provider's test mode against a staging deploy. Subscribe, renew (test clock), cancel, fail a renewal, refund, dispute | Each one ends in the right plan in Firestore, and a RELEASE.md section for billing |
| P6 — Live | Author sets live secrets; one real ₹999 payment by the author, then a refund | Money arrives in the bank account. `scripts/release-check.sh` reports `billing_enabled: true` |

Rough size: P1–P3 about one sprint of Claude's work. P0, P4 and P6 are on the
author's calendar, and P0 takes the longest, so it starts first.

## Measures, once live

- Funnel: Pricing view → checkout started → paid (provider dashboard plus a
  `checkout_started` count in `usage_counts.py`).
- Free validations used → upgrade (the sprint 2 free-validation switch).
- Churn, and failed renewals recovered by the provider's retries.

## Decisions for the author

1. Seller: individual or sole proprietorship, and whether to GST-register now
   (CA).
2. Provider order: Dodo, then Paddle (recommended), or Razorpay-first if you
   expect Indian users only.
3. Prices: ₹999 and $12, or a single USD price.
4. When to start P0: right after a "would pay" phase 4, in parallel with the
   data sprint, since approval takes time.

## Sources (read 24 Oct 2026)

- Stripe India, invite-only and KYC: [How can I open a Stripe account in India?](https://support.stripe.com/questions/how-can-i-open-a-stripe-account-in-india), [Video KYC for India onboarding](https://support.stripe.com/questions/video-kyc-for-india-onboarding), [India FAQ](https://support.stripe.com/questions/india-faq), [International payments from Indian accounts](https://support.stripe.com/questions/accepting-international-payments-from-stripe-accounts-in-india?locale=en-GB), [TechCrunch on invite-only](https://techcrunch.com/?p=2787172)
- Stripe Managed Payments: [docs](https://docs.stripe.com/payments/managed-payments), [pricing](https://support.stripe.com/questions/managed-payments-pricing), [Freemius on its limits](https://freemius.com/blog/stripe-merchant-of-record/)
- Razorpay: [pricing explained](https://razorpay.com/blog/razorpay-payment-gateway-pricing-explained/), [recurring billing costs](https://razorpay.com/blog/cheapest-payment-gateway-for-recurring-billing-e-nach-upi-autopay-and-subscription/), [international charges (Xflow)](https://www.xflowpay.com/blog/razorpay-international-payment-gateway-charges)
- MoR comparisons: [Dodo pricing](https://dodopayments.com/pricing), [TurboStarter comparison](https://www.turbostarter.dev/blog/stripe-vs-lemonsqueezy-vs-polar-vs-creem-choosing-the-right-saas-payment-provider), [DevToolLab](https://devtoollab.com/blog/best-merchant-of-record-platforms), [FintechSpecs](https://fintechspecs.com/blog/stripe-vs-paddle-vs-lemon-squeezy-vs-polar-merchant-of-record-b2b-saas/)
- Paddle: [supported countries](https://developer.paddle.com/concepts/sell/supported-countries-locales), [UPI](https://developer.paddle.com/concepts/payment-methods/upi.md)
- RBI e-mandates: [RBI notification](https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=12341), [Mondaq on the ₹15,000 limit](https://mondaq.com/india/financial-services/1206696/rbi-enhances-transaction-limits-for-processing-of-e-mandates-for-recurring-transactions-from-inr-5000-to-inr-15000-), [Chargebee on Razorpay e-mandates](https://www.chargebee.com/docs/payments/razorpay-rbi-e-mandate.html)
- GST: [Tally on SaaS exports](https://tallysolutions.com/gst/gst-software-saas-exports-international-clients/), [Ledgers on GST for SaaS](https://ledgers.cloud/in/understanding-gst-for-saas-companies-in-india)
