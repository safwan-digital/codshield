=== COD Shield ===
Contributors: safwandigital
Tags: woocommerce, cod, cash on delivery, fraud, orders, risk
Requires at least: 6.0
Tested up to: 6.9
Requires PHP: 7.4
Stable tag: 1.0.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Score WooCommerce COD orders for fake-order risk before you dispatch — 17 explainable checks, every score with its reasons.

== Description ==

Every Indian e-commerce seller knows the pattern: a cash-on-delivery order with a phone number like 9999999999, an address that says "asdf street", and a customer who never picks up. You pay the courier both ways and the parcel comes back.

COD Shield helps you catch those orders **before** dispatch. Export your orders (WooCommerce > Orders > Export), upload the CSV under WooCommerce > COD Shield, and every COD order is scored 0–100 by a transparent rules engine:

* LOW (0–24) — safe to dispatch
* MEDIUM (25–49) — confirm on WhatsApp / call before dispatch
* HIGH (50+) — hold, verify by call, or take a part-prepayment first

The 17 checks cover fake phone shapes (repeated digits, typed sequences, wrong series), incomplete names, junk addresses, missing or invalid PIN codes, disposable email domains, repeat offenders (same phone with different names, or a phone whose earlier order was cancelled), and high-value COD orders.

Every point in every score comes with its reason, printed in the report. No black box, no machine learning. The uploaded file is read once and discarded — nothing is stored, no data leaves your site, and nothing in your store is changed. Prepaid and already-cancelled orders are listed but never scored.

COD Shield is also available as a command-line tool: https://github.com/safwan-digital/codshield — both versions use identical rules and score the same order the same way.

Developed by [Safwan.Digital](https://safwan.digital).

== Installation ==

1. Upload the `codshield` folder to `/wp-content/plugins/`, or install the zip via Plugins > Add New > Upload Plugin.
2. Activate the plugin.
3. Go to WooCommerce > COD Shield, export your orders as CSV, upload, and read the report.

== Frequently Asked Questions ==

= Does COD Shield change anything in my store? =

No. It only reads the CSV you upload. It never edits orders, products or settings, and it stores nothing.

= Which orders are scored? =

Cash-on-delivery orders that are not already cancelled, failed or refunded. Prepaid orders and closed orders are shown as PREPAID / CLOSED and are not scored.

= Are the rules India-specific? =

In this version, yes — phone checks assume 10-digit Indian mobiles and PIN checks assume 6-digit PIN codes. Thresholds for high-value orders are configurable on the report page.

= Is a high score proof of a fake order? =

No. A score is a triage signal, not a verdict. Confirm HIGH orders before dispatch; do not auto-cancel on a score alone.

== Screenshots ==

1. The COD Shield report: every COD order scored, riskiest first, with reasons.

== Changelog ==

= 1.0.0 =
* Initial release: CSV upload scoring with 17 explainable checks, HIGH/MEDIUM/LOW bands, configurable value thresholds.

== Upgrade Notice ==

= 1.0.0 =
Initial release.
