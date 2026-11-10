# COD Shield

**Score your WooCommerce COD orders for fake-order risk — before you dispatch, not after the courier brings the parcel back.**

Every Indian e-commerce seller knows the pattern: a cash-on-delivery order with a phone number like `9999999999`, an address that says "asdf street", and a customer who never picks up. You pay the courier both ways, the product comes back, and the "order" was never real.

COD Shield reads a plain orders CSV export, scores every COD order with a **transparent rules engine** (17 explainable checks — fake phone shapes, junk addresses, repeat offenders, disposable emails, high-value first orders), and gives you a report with a risk band and a suggested action for each order:

| Band | Score | Action |
|---|---|---|
| LOW | 0–24 | Safe to dispatch |
| MEDIUM | 25–49 | Confirm on WhatsApp / call before dispatch |
| HIGH | 50+ | Hold — verify by call, or take a part-prepayment first |

Every point in every score comes with its reason, printed in the report. No black box, no machine learning, no data leaving your machine.

## Two ways to use it

**1. WordPress plugin (point and click)** — the `wordpress-plugin/` folder in this repo is a complete WooCommerce plugin, built to WordPress.org directory standards (GPLv2). Zip the inner `codshield` folder (or use `wordpress-plugin/codshield.zip`), upload it under Plugins > Add New > Upload Plugin, and COD Shield appears under **WooCommerce > COD Shield**: upload your orders CSV there and read the report in your admin. Same rules, same scores as the CLI. (WordPress.org directory submission is in progress.)

**2. Command line (below)** — one Python file, no installation, works on any computer for any store.

## Quick start

```bash
# See it work on built-in sample data (no install, Python 3.10+ only)
python codshield.py demo

# Score your own export (WooCommerce > Orders > Export)
python codshield.py score orders.csv --out report.csv

# Print the scoring rules
python codshield.py rules
```

No dependencies — Python standard library only. No logins, no API keys.

## What it checks

- **Phone**: missing, not a valid 10-digit Indian mobile, wrong series, repeated digits (`9999999999`), typed sequences (`1234567890`)
- **Name & address**: incomplete names, junk text (`test`, `asdf`, `fake`), addresses too short to deliver, missing or invalid PIN codes
- **Email**: missing, or a disposable/throwaway domain
- **Patterns across the file**: same phone on 3+ orders, same phone under different names, a phone whose earlier order was cancelled/failed
- **Value**: high-value and very-high-value COD orders (thresholds configurable: `--high-value 5000 --very-high-value 10000`)

Prepaid orders are listed as `PREPAID` and never scored — they are already paid. Cancelled/failed/refunded orders are listed as `CLOSED` and skipped too — but a cancelled order's phone number still counts as a warning sign when it appears on a new order.

## Column names

COD Shield recognises common WooCommerce export headers automatically (`Billing Phone`, `Order Total`, `Payment Method`, `Order Status`, …) and most reasonable variants. If a column is missing, the related checks simply report what they can see — the tool flags what it cannot read instead of guessing.

## Honest limits

- A score is a **triage signal, not a verdict**. A genuine customer can share a phone with family (different names), and a determined fake can look clean. Confirm HIGH orders; don't auto-cancel on a score.
- Phone rules are India-specific in v0.1 (10-digit mobiles, 6-digit PINs). The rules live in one small function and are easy to adapt.
- It works on exports, not live API sync — by design, so it needs no credentials and touches nothing in your store.

## Roadmap

- Optional WooCommerce REST API sync (read-only)
- WhatsApp confirmation message templates for MEDIUM orders
- Country packs beyond India

## Licence

MIT © Safwan Siddi
