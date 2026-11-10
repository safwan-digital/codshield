#!/usr/bin/env python3
"""COD Shield — score WooCommerce COD orders for fake-order risk before you dispatch.

Reads a plain orders CSV export (WooCommerce > Orders > Export, or any CSV with
recognisable columns), scores every cash-on-delivery order with a transparent,
explainable rules engine, and writes a report: risk score, band, suggested action,
and the exact reasons for every point. No logins, no API keys, no data leaves
your machine.

Commands:
    score   Score an orders CSV and write a risk report.
    demo    Generate a sample orders file and score it, so you can see it work.
    rules   Print the scoring rules and what each one costs.

The philosophy is the same as PriceScout's: every score can be explained, and
the tool never invents data — an order it cannot read is flagged, not guessed.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict

VERSION = "0.1.0"

# --------------------------------------------------------------------------
# Column mapping: many names, one meaning. Case-insensitive, punctuation-free.
# --------------------------------------------------------------------------

COLUMN_ALIASES = {
    "order_id": ["order id", "order number", "order", "id", "number"],
    "name": ["billing name", "customer name", "name", "full name",
             "billing first name"],
    "last_name": ["billing last name"],
    "phone": ["billing phone", "phone", "mobile", "phone number",
              "billing mobile", "customer phone"],
    "email": ["billing email", "email", "customer email", "email address"],
    "address": ["billing address 1", "billing address", "address",
                "shipping address 1", "shipping address", "address 1"],
    "city": ["billing city", "city", "shipping city"],
    "pincode": ["billing postcode", "postcode", "pincode", "pin code", "zip",
                "billing pin code", "shipping postcode"],
    "total": ["order total", "total", "grand total", "amount"],
    "payment": ["payment method", "payment", "payment gateway"],
    "status": ["order status", "status"],
}

JUNK_TOKENS = {"test", "asdf", "qwerty", "xxxx", "xxx", "fake", "none", "na",
               "n/a", "abc", "xyz", "demo", "sample", "nil", "-"}
DISPOSABLE_DOMAINS = {"mailinator.com", "guerrillamail.com", "10minutemail.com",
                      "tempmail.com", "temp-mail.org", "yopmail.com",
                      "throwawaymail.com", "getnada.com", "sharklasers.com"}
BAD_STATUSES = {"cancelled", "canceled", "failed", "refunded", "on-hold"}

DEFAULT_HIGH_VALUE = 5000.0
DEFAULT_VERY_HIGH_VALUE = 10000.0


def _norm_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (h or "").lower()).strip()


def map_columns(fieldnames):
    """Return {canonical: actual header} for the headers we recognise."""
    norm = {_norm_header(h): h for h in fieldnames or []}
    mapping = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in norm:
                mapping[canonical] = norm[alias]
                break
    return mapping


def get(row, mapping, key, default=""):
    col = mapping.get(key)
    if col is None:
        return default
    return (row.get(col) or "").strip()


# --------------------------------------------------------------------------
# Phone handling (India defaults)
# --------------------------------------------------------------------------

def normalise_phone(raw: str):
    """Return the 10-digit Indian mobile, or None if it cannot be one."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return digits


def _longest_sequence_run(phone: str) -> int:
    """Longest run of consecutive ascending or descending digits."""
    best = run = 1
    direction = 0
    for a, b in zip(phone, phone[1:]):
        step = int(b) - int(a)
        if step in (1, -1) and (direction == 0 or step == direction):
            run += 1
            direction = step
        elif step in (1, -1):
            run = 2
            direction = step
        else:
            run = 1
            direction = 0
        best = max(best, run)
    return best


def phone_pattern_flags(phone: str):
    """Fake-number shapes: repeated digits and keyboard sequences.

    A sequence only counts when at least 8 of the 10 digits run consecutively
    (1234567890, 9876543210). A real number that merely ends in ...012345 is
    common and must NOT be flagged — false alarms kill trust in the tool.
    """
    flags = []
    counts = Counter(phone)
    if counts and counts.most_common(1)[0][1] >= 7:
        flags.append("repeated")
    if _longest_sequence_run(phone) >= 8:
        flags.append("sequential")
    return flags


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

RULES = [
    ("Phone missing or unreadable", 30),
    ("Phone is not a valid 10-digit Indian mobile", 30),
    ("Phone series cannot be a mobile (does not start 6-9)", 15),
    ("Phone looks typed, not real (repeated digits)", 25),
    ("Phone looks typed, not real (number sequence)", 25),
    ("Name looks incomplete", 10),
    ("Name or address contains junk text (test/asdf/fake...)", 20),
    ("Address too short to deliver reliably", 15),
    ("PIN code missing", 15),
    ("PIN code format invalid", 15),
    ("Email missing", 5),
    ("Disposable / throwaway email domain", 15),
    ("Same phone on 3+ orders in this file", 15),
    ("Same phone used with different names", 20),
    ("This phone had a cancelled/failed order before", 25),
    ("High-value COD order (>= high threshold)", 10),
    ("Very-high-value COD order (>= very-high threshold)", 15),
]


def band_for(score: int):
    if score >= 50:
        return "HIGH", "Hold - verify by call, or take a part-prepayment first"
    if score >= 25:
        return "MEDIUM", "Confirm on WhatsApp / call before dispatch"
    return "LOW", "Safe to dispatch"


def looks_junk(text: str) -> bool:
    tokens = re.split(r"[^a-z]+", (text or "").lower())
    return any(t in JUNK_TOKENS for t in tokens if t)


def score_order(order, context, high_value, very_high_value):
    """Return (score, [reasons]). `context` carries cross-order facts."""
    score = 0
    reasons = []

    def add(points, reason):
        nonlocal score
        score += points
        reasons.append(reason)

    raw_phone = order["phone"]
    phone = normalise_phone(raw_phone)
    if not raw_phone or phone is None and not re.sub(r"\D", "", raw_phone):
        add(30, "Phone missing or unreadable")
    elif phone is None:
        add(30, "Phone is not a valid 10-digit Indian mobile")
    if phone is not None:
        if phone[0] not in "6789":
            add(15, "Phone series cannot be a mobile (does not start 6-9)")
        for flag in phone_pattern_flags(phone):
            if flag == "repeated":
                add(25, "Phone looks typed, not real (repeated digits)")
            if flag == "sequential":
                add(25, "Phone looks typed, not real (number sequence)")

    name = order["name"]
    if len(re.sub(r"[^A-Za-z]", "", name)) < 3:
        add(10, "Name looks incomplete")
    if looks_junk(name) or looks_junk(order["address"]):
        add(20, "Name or address contains junk text (test/asdf/fake...)")

    address = (order["address"] + " " + order["city"]).strip()
    if len(address) < 20:
        add(15, "Address too short to deliver reliably")

    pin = re.sub(r"\D", "", order["pincode"] or "")
    if not pin:
        add(15, "PIN code missing")
    elif len(pin) != 6 or pin.startswith("0"):
        add(15, "PIN code format invalid")

    email = (order["email"] or "").lower()
    if not email:
        add(5, "Email missing")
    elif "@" in email and email.split("@")[-1] in DISPOSABLE_DOMAINS:
        add(15, "Disposable / throwaway email domain")

    if phone is not None:
        if context["phone_counts"].get(phone, 0) >= 3:
            add(15, "Same phone on 3+ orders in this file")
        if len(context["phone_names"].get(phone, set())) >= 2:
            add(20, "Same phone used with different names")
        if phone in context["bad_phones"]:
            add(25, "This phone had a cancelled/failed order before")

    total = order["total_value"]
    if total is not None:
        if total >= very_high_value:
            add(15, "Very-high-value COD order (>= very-high threshold)")
        elif total >= high_value:
            add(10, "High-value COD order (>= high threshold)")

    return min(score, 100), reasons


def parse_total(raw):
    cleaned = re.sub(r"[^0-9.]", "", (raw or "").replace(",", ""))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def is_cod(order) -> bool:
    payment = (order["payment"] or "").lower()
    if not payment:
        return True  # no payment column: score everything
    return "cod" in payment or "cash on delivery" in payment


def load_orders(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        mapping = map_columns(reader.fieldnames)
        orders = []
        for row in reader:
            name = get(row, mapping, "name")
            last = get(row, mapping, "last_name")
            if last and last.lower() not in name.lower():
                name = (name + " " + last).strip()
            orders.append({
                "order_id": get(row, mapping, "order_id"),
                "name": name,
                "phone": get(row, mapping, "phone"),
                "email": get(row, mapping, "email"),
                "address": get(row, mapping, "address"),
                "city": get(row, mapping, "city"),
                "pincode": get(row, mapping, "pincode"),
                "total": get(row, mapping, "total"),
                "total_value": parse_total(get(row, mapping, "total")),
                "payment": get(row, mapping, "payment"),
                "status": get(row, mapping, "status").lower(),
            })
    return orders


def build_context(orders):
    phone_counts = Counter()
    phone_names = defaultdict(set)
    bad_phones = set()
    for order in orders:
        phone = normalise_phone(order["phone"])
        if phone is None:
            continue
        phone_counts[phone] += 1
        if order["name"]:
            phone_names[phone].add(order["name"].lower())
        if order["status"] in BAD_STATUSES:
            bad_phones.add(phone)
    return {"phone_counts": phone_counts, "phone_names": phone_names,
            "bad_phones": bad_phones}


def score_orders(orders, high_value=DEFAULT_HIGH_VALUE,
                 very_high_value=DEFAULT_VERY_HIGH_VALUE):
    context = build_context(orders)
    results = []
    for order in orders:
        if order["status"] in BAD_STATUSES:
            results.append({**order, "score": "", "band": "CLOSED",
                            "action": "Not scored (order already "
                                      "cancelled/failed/refunded)",
                            "reasons": []})
            continue
        if not is_cod(order):
            results.append({**order, "score": "", "band": "PREPAID",
                            "action": "Not scored (prepaid order)",
                            "reasons": []})
            continue
        score, reasons = score_order(order, context, high_value, very_high_value)
        band, action = band_for(score)
        results.append({**order, "score": score, "band": band,
                        "action": action, "reasons": reasons})
    return results


REPORT_FIELDS = ["Order ID", "Name", "Phone", "Total", "Risk Score",
                 "Risk Band", "Suggested Action", "Reasons"]


def write_report(results, out_path):
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "PREPAID": 3, "CLOSED": 4}
    ranked = sorted(results,
                    key=lambda r: (order.get(r["band"], 9),
                                   -(r["score"] if isinstance(r["score"], int) else -1)))
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(REPORT_FIELDS)
        for r in ranked:
            writer.writerow([r["order_id"], r["name"], r["phone"], r["total"],
                             r["score"], r["band"], r["action"],
                             "; ".join(r["reasons"])])
    return ranked


def print_summary(results):
    counts = Counter(r["band"] for r in results)
    print(f"\nScored {len(results)} orders: "
          f"HIGH {counts.get('HIGH', 0)} · MEDIUM {counts.get('MEDIUM', 0)} · "
          f"LOW {counts.get('LOW', 0)} · PREPAID (not scored) {counts.get('PREPAID', 0)}"
          f" · CLOSED (not scored) {counts.get('CLOSED', 0)}")
    risky = [r for r in results if r["band"] == "HIGH"]
    if risky:
        print("\nHighest risk first:")
        for r in risky[:10]:
            print(f"  #{r['order_id']}  score {r['score']}  {r['name']}  "
                  f"({r['phone']})  Rs {r['total']}")
            print(f"      {'; '.join(r['reasons'])}")


def cmd_score(args):
    orders = load_orders(args.orders_csv)
    if not orders:
        print("No orders found in that file.", file=sys.stderr)
        return 1
    results = score_orders(orders, args.high_value, args.very_high_value)
    out = args.out or "codshield-report.csv"
    write_report(results, out)
    print_summary(results)
    print(f"\nReport written to {out}")
    return 0


DEMO_ORDERS = [
    # order_id, name, phone, email, address, city, pincode, total, payment, status
    ("1001", "Rahul Sharma", "9811045672", "rahul.sharma@gmail.com",
     "C-42, Lajpat Nagar Part 2, Near Central Market", "New Delhi", "110024",
     "1499", "Cash on Delivery", "processing"),
    ("1002", "test test", "9999999999", "",
     "asdf street", "Delhi", "", "8999", "Cash on Delivery", "processing"),
    ("1003", "Priya Nair", "9847012345", "priya.nair@yahoo.in",
     "TC 14/221, Pattom Palace PO, Near Kesavadasapuram", "Trivandrum",
     "695004", "2499", "Cash on Delivery", "processing"),
    ("1004", "Amit Verma", "1234567890", "amit@mailinator.com",
     "House 7, MG Road", "Lucknow", "226001", "12500",
     "Cash on Delivery", "processing"),
    ("1005", "Sneha Kulkarni", "9822045671", "sneha.k@gmail.com",
     "Flat 9B, Koregaon Park, Lane 6, Near German Bakery", "Pune", "411001",
     "999", "UPI", "processing"),
    ("1006", "Mohammed Faiz", "9008023456", "faiz.m@outlook.com",
     "12, 3rd Cross, Frazer Town, Near Coles Park", "Bengaluru", "560005",
     "1899", "Cash on Delivery", "cancelled"),
    ("1007", "Faiz M", "9008023456", "faiz.m@outlook.com",
     "12, 3rd Cross, Frazer Town", "Bengaluru", "560005", "11500",
     "Cash on Delivery", "processing"),
    ("1008", "Kavitha Reddy", "9652109876", "kavitha.r@gmail.com",
     "Plot 88, Road No 12, Banjara Hills, Near City Centre Mall",
     "Hyderabad", "500034", "3299", "Cash on Delivery", "processing"),
    ("1009", "x x", "5555555555", "",
     "na", "Mumbai", "400001", "7499", "Cash on Delivery", "processing"),
    ("1010", "Deepak Yadav", "9792011234", "deepak.y@gmail.com",
     "Village Rampur, Post Office Khas, District Jaunpur", "Jaunpur",
     "222001", "1150", "Cash on Delivery", "processing"),
]

DEMO_HEADER = ["Order ID", "Billing First Name", "Billing Phone",
               "Billing Email", "Billing Address 1", "Billing City",
               "Billing Postcode", "Order Total", "Payment Method",
               "Order Status"]


def cmd_demo(args):
    out_orders = args.orders_out or "examples/sample-orders.csv"
    import os
    os.makedirs(os.path.dirname(out_orders) or ".", exist_ok=True)
    with open(out_orders, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(DEMO_HEADER)
        writer.writerows(DEMO_ORDERS)
    print(f"Sample orders written to {out_orders}")
    orders = load_orders(out_orders)
    results = score_orders(orders)
    out_report = args.out or "examples/sample-report.csv"
    write_report(results, out_report)
    print_summary(results)
    print(f"\nReport written to {out_report}")
    print("Expected: #1002, #1004, #1007 and #1009 land HIGH; "
          "#1001, #1003, #1008, #1010 stay LOW; #1005 is prepaid and "
          "#1006 is already cancelled (neither is scored).")
    return 0


def cmd_rules(_args):
    print("COD Shield scoring rules (score is capped at 100):\n")
    for reason, points in RULES:
        print(f"  +{points:<3} {reason}")
    print("\nBands:  0-24 LOW (safe to dispatch) · 25-49 MEDIUM "
          "(confirm first) · 50+ HIGH (hold and verify)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="codshield",
        description="Score WooCommerce COD orders for fake-order risk "
                    "before you dispatch.")
    parser.add_argument("--version", action="version",
                        version=f"COD Shield {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_score = sub.add_parser("score", help="Score an orders CSV export.")
    p_score.add_argument("orders_csv")
    p_score.add_argument("--out", default=None,
                         help="Report path (default: codshield-report.csv)")
    p_score.add_argument("--high-value", type=float,
                         default=DEFAULT_HIGH_VALUE)
    p_score.add_argument("--very-high-value", type=float,
                         default=DEFAULT_VERY_HIGH_VALUE)
    p_score.set_defaults(func=cmd_score)

    p_demo = sub.add_parser("demo", help="Generate and score a sample file.")
    p_demo.add_argument("--orders-out", default=None)
    p_demo.add_argument("--out", default=None)
    p_demo.set_defaults(func=cmd_demo)

    p_rules = sub.add_parser("rules", help="Print the scoring rules.")
    p_rules.set_defaults(func=cmd_rules)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
