# COD Shield — Explanation Video Scripts

Two videos, same pattern as FeedGuard / LabelDesk / PriceScout:
- **Script A** — @safwan.digital reel (~55s, vertical, motion graphics, Helio voice)
- **Script B** — GitHub demo video (~45s, landscape terminal walkthrough)

Both use only real output from the tool's own demo run (scores 90/70/60/100,
HIGH 4 · LOW 4 · PREPAID 1 · CLOSED 1 on the 10-order sample).

---

## Script A — Reel (@safwan.digital)

**Title card:** THE ORDER LOOKED REAL. / IT WASN'T.
**Series tag:** OPEN SOURCE · TOOL 04
**Hook sub:** Every COD seller has paid for this lesson
**Chat label:** The fake order
**Chat text:** "Sir, address pe aake phone bandh. Parcel wapas bhej diya."
**Chip:** Courier paid twice / Product came back / Profit gone

| # | Line (voice) | On screen |
|---|---|---|
| Hook | "This order cost the seller money before it even shipped. Phone number: nine, nine, nine, nine. Address: 'asdf street'. It was never real." | Order card with the fake phone + junk address highlighted |
| 1 | "So I built COD Shield. Feed it your WooCommerce orders export — the file you already have." | STEP 1 · FEED THE EXPORT — `codshield.py score orders.csv` |
| 2 | "It runs seventeen checks. Fake phone shapes. Junk addresses. Disposable emails. And the dangerous one — the same phone whose last order already came back." | STEP 2 · 17 CHECKS — rule cards |
| 3 | "Every order gets a score, a band, and the exact reason. Ninety out of a hundred — hold it. Zero — ship it." | STEP 3 · SCORE + REASON — report rows (90 HIGH / 0 LOW) |
| 4 | "Confirm the risky ones on WhatsApp BEFORE the courier does his first trip — that's where the money is saved." | STEP 4 · CONFIRM FIRST — band actions |
| Outro | "It's free, it's open source, link in my profile. Comment SHIELD and I'll send you the repo." | COD SHIELD / comment SHIELD |

**Result chips on outro:** 10 sample orders scored / 4 fakes caught
**CTA:** comment **SHIELD**

---

## Script B — Demo (repo, landscape)

**Title card:** COD SHIELD — fake COD orders, scored before dispatch
**Narration (7 beats):**

1. "This is COD Shield — it scores cash-on-delivery orders for fake-order risk, before you dispatch."
2. "It starts from the orders export you already have. No login, no API key, nothing leaves your machine."
3. (demo command) "One command scores the whole file."
4. "Ten sample orders. Four come back high risk — a typed phone number, a junk address, a repeat offender whose last order was cancelled, and a twelve-thousand-rupee order on a throwaway email."
5. "Every score shows its reasons. No black box — you can argue with every point."
6. "Clean orders score zero and ship as normal. Prepaid and cancelled orders are never scored at all."
7. "COD Shield is free and open source — the link is on screen. Score first, dispatch second."

**End card:** github.com/safwan-digital/codshield
