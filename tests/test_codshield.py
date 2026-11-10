import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import codshield as cs


def order(**kw):
    base = {"order_id": "1", "name": "Rahul Sharma", "phone": "9811045672",
            "email": "rahul@gmail.com",
            "address": "C-42, Lajpat Nagar Part 2, Near Central Market",
            "city": "New Delhi", "pincode": "110024", "total": "1499",
            "total_value": 1499.0, "payment": "Cash on Delivery",
            "status": "processing"}
    base.update(kw)
    return base


def score(o, all_orders=None):
    ctx = cs.build_context(all_orders or [o])
    return cs.score_order(o, ctx, 5000.0, 10000.0)


class TestPhone(unittest.TestCase):
    def test_normalise_variants(self):
        self.assertEqual(cs.normalise_phone("+91 98110 45672"), "9811045672")
        self.assertEqual(cs.normalise_phone("09811045672"), "9811045672")
        self.assertEqual(cs.normalise_phone("9811045672"), "9811045672")

    def test_normalise_rejects(self):
        self.assertIsNone(cs.normalise_phone("12345"))
        self.assertIsNone(cs.normalise_phone(""))
        self.assertIsNone(cs.normalise_phone("981104567"))  # 9 digits

    def test_patterns(self):
        self.assertIn("repeated", cs.phone_pattern_flags("9999999999"))
        self.assertIn("sequential", cs.phone_pattern_flags("1234567890"))
        self.assertIn("sequential", cs.phone_pattern_flags("9876543210"))

    def test_real_number_ending_in_sequence_not_flagged(self):
        # Regression: 9847012345 contains "012345" but is a plausible number.
        self.assertEqual(cs.phone_pattern_flags("9847012345"), [])
        s, reasons = score(order(phone="9847012345"))
        self.assertFalse(any("sequence" in r for r in reasons))


class TestScoring(unittest.TestCase):
    def test_clean_order_is_low(self):
        s, reasons = score(order())
        band, _ = cs.band_for(s)
        self.assertEqual(band, "LOW")
        self.assertEqual(reasons, [])

    def test_fake_phone_scores(self):
        s, reasons = score(order(phone="9999999999"))
        self.assertTrue(any("repeated" in r for r in reasons))
        self.assertGreaterEqual(s, 25)

    def test_sequential_phone_scores(self):
        s, reasons = score(order(phone="1234567890"))
        self.assertTrue(any("sequence" in r for r in reasons))

    def test_missing_phone(self):
        s, reasons = score(order(phone=""))
        self.assertIn("Phone missing or unreadable", reasons)

    def test_bad_pincode(self):
        s, reasons = score(order(pincode="1234"))
        self.assertIn("PIN code format invalid", reasons)

    def test_missing_pincode(self):
        s, reasons = score(order(pincode=""))
        self.assertIn("PIN code missing", reasons)

    def test_junk_and_short_address(self):
        s, reasons = score(order(name="test test", address="asdf"))
        self.assertTrue(any("junk" in r for r in reasons))
        self.assertTrue(any("too short" in r for r in reasons))

    def test_disposable_email(self):
        s, reasons = score(order(email="a@mailinator.com"))
        self.assertIn("Disposable / throwaway email domain", reasons)

    def test_high_value(self):
        s, reasons = score(order(total_value=12500.0, total="12500"))
        self.assertTrue(any("Very-high-value" in r for r in reasons))

    def test_repeat_cancelled_phone(self):
        bad = order(order_id="9", status="cancelled")
        new = order(order_id="10")
        s, reasons = score(new, [bad, new])
        self.assertIn("This phone had a cancelled/failed order before", reasons)

    def test_same_phone_different_names(self):
        a = order(order_id="1", name="Mohammed Faiz")
        b = order(order_id="2", name="Faiz M")
        s, reasons = score(b, [a, b])
        self.assertIn("Same phone used with different names", reasons)


class TestBandsAndPrepaid(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(cs.band_for(0)[0], "LOW")
        self.assertEqual(cs.band_for(24)[0], "LOW")
        self.assertEqual(cs.band_for(25)[0], "MEDIUM")
        self.assertEqual(cs.band_for(50)[0], "HIGH")

    def test_prepaid_not_scored(self):
        results = cs.score_orders([order(payment="UPI")])
        self.assertEqual(results[0]["band"], "PREPAID")

    def test_closed_order_not_scored(self):
        results = cs.score_orders([order(status="cancelled")])
        self.assertEqual(results[0]["band"], "CLOSED")

    def test_score_capped_at_100(self):
        o = order(phone="9999999999", name="test", address="asdf",
                  pincode="", email="a@mailinator.com", total_value=99999.0)
        s, _ = score(o)
        self.assertLessEqual(s, 100)


if __name__ == "__main__":
    unittest.main()
