=== COD Shield ===
Contributors: safwandigital
Tags: woocommerce, cod, cash on delivery, fraud, orders, risk
Requires at least: 6.0
Tested up to: 6.9
Requires PHP: 7.4
Stable tag: 1.1.1
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Score WooCommerce COD orders for fake-order risk before you dispatch — 17 explainable checks, every score with its reasons.

== Description ==

Every Indian e-commerce seller knows the pattern: a cash-on-delivery order with a phone number like 9999999999, an address that says "asdf street", and a customer who never picks up. You pay the courier both ways and the parcel comes back.

COD Shield helps you catch those orders **before** dispatch. Open WooCommerce > COD Shield and score your live dispatch queue directly — pick the statuses waiting to ship and every COD order is scored 0–100 by a transparent rules engine, with each phone checked against your recent order history. Prefer files? You can still export your orders and upload the CSV instead.

* LOW (0–24) — safe to dispatch
* MEDIUM (25–49) — confirm on WhatsApp / call before dispatch
* HIGH (50+) — hold, verify by call, or take a part-prepayment first

The 17 checks cover fake phone shapes (repeated digits, typed sequences, wrong series), incomplete names, junk addresses, missing or invalid PIN codes, disposable email domains, repeat offenders (same phone with different names, or a phone whose earlier order was cancelled, failed or returned), and high-value COD orders.

Every point in every score comes with its reason, printed in the report. No black box, no machine learning. Nothing is stored, no data leaves your site, and nothing in your store is changed — COD Shield only reads. Prepaid and already-cancelled orders are listed but never scored.

COD Shield is also available as a command-line tool: https://github.com/safwan-digital/codshield — both versions use identical rules and score the same order the same way.

Developed by [Safwan.Digital](https://safwan.digital).

== Installation ==

1. Upload the `codshield` folder to `/wp-content/plugins/`, or install the zip via Plugins > Add New > Upload Plugin.
2. Activate the plugin.
3. Go to WooCommerce > COD Shield, pick the statuses waiting for dispatch, and click "Score live orders" — or export your orders as CSV and upload the file instead.

== Frequently Asked Questions ==

= Does COD Shield change anything in my store? =

No. In live mode it only reads your orders; in CSV mode it only reads the file you upload. It never edits orders, products or settings, and it stores nothing.

= Which orders are scored? =

Cash-on-delivery orders that are not already cancelled, failed or refunded. Prepaid orders and closed orders are shown as PREPAID / CLOSED and are not scored.

= Are the rules India-specific? =

In this version, yes — phone checks assume 10-digit Indian mobiles and PIN checks assume 6-digit PIN codes. Thresholds for high-value orders are configurable on the report page.

= Is a high score proof of a fake order? =

No. A score is a triage signal, not a verdict. Confirm HIGH orders before dispatch; do not auto-cancel on a score alone.

== Screenshots ==

1. The COD Shield report: every COD order scored, riskiest first, with reasons.

== Changelog ==

= 1.1.1 =
* Fix: live scoring could exhaust memory on shared hosting while reading order history as full objects — history is now read as a light table query, and scoring errors surface as a readable notice instead of a blank page.

= 1.1.0 =
* NEW: Live dispatch queue — score orders directly from WooCommerce, no CSV export needed. Pick the statuses to score (Processing, On hold and your custom hold statuses are pre-selected); repeat-offender checks use your latest 1,000 orders of history, including RTO-type custom statuses.
* CSV upload mode unchanged, same rules and bands.

= 1.0.0 =
* Initial release: CSV upload scoring with 17 explainable checks, HIGH/MEDIUM/LOW bands, configurable value thresholds.

== Upgrade Notice ==

= 1.1.1 =
Fixes a blank-page fault in live scoring on memory-limited hosting.

= 1.1.0 =
Adds live order scoring straight from WooCommerce — no CSV export needed. CSV mode unchanged.

= 1.0.0 =
Initial release.
