import unittest
from specanchor.invariant import parse_invariants, InvariantError, ENFORCED, STATED


class TestParseInvariants(unittest.TestCase):
    def test_two_entries(self):
        md = (
            "# baseline\n\n"
            "### INV-LEDGER-1 — Refund reverses recorded entries\n"
            "Holds:  refund negates the recorded delta.\n"
            "Why:    config drifts.\n"
            "Guarded by: x_test.go (spec:INV-LEDGER-1)\n"
            "Status: enforced\n"
            "Since:  2026-05-31 / slice-1\n\n"
            "### INV-RES-3 — materials not modeled\n"
            "Holds:  materials must not appear in cost paths.\n"
            "Status: stated\n"
            "Since:  2026-05-31\n"
        )
        got = parse_invariants(md)
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0].id, "INV-LEDGER-1")
        self.assertEqual(got[0].status, ENFORCED)
        self.assertEqual(got[1].id, "INV-RES-3")
        self.assertEqual(got[1].status, STATED)
        self.assertEqual(got[1].since, "2026-05-31")
        self.assertEqual(got[1].holds, "materials must not appear in cost paths.")

    def test_missing_status_raises(self):
        with self.assertRaises(InvariantError):
            parse_invariants("### INV-X-1 — no status\nHolds: nothing\n")

    def test_duplicate_id_raises(self):
        md = (
            "### INV-X-1 — a\nStatus: stated\nSince: 2026-05-31\n\n"
            "### INV-X-1 — b\nStatus: enforced\nSince: 2026-05-31\n"
        )
        with self.assertRaises(InvariantError):
            parse_invariants(md)

    def test_multiline_holds_and_anchor(self):
        md = (
            "### INV-RES-2 — XP is progression\n"
            'Holds:  XP is hero-bound and non-tradeable. "Spending" XP moves it from\n'
            "        xp_available to xp_invested; it is never destroyed. Level is a\n"
            "        projection of xp_invested.\n"
            "Why:    XP-as-currency loses the audit trail.\n"
            "Guarded by: x_test.go (spec:INV-RES-2)\n"
            "Anchor:  sha-1a2b3c4\n"
            "Status: enforced\n"
            "Since:  2026-05-31\n"
        )
        got = parse_invariants(md)
        self.assertEqual(len(got), 1)
        want = (
            'XP is hero-bound and non-tradeable. "Spending" XP moves it from '
            "xp_available to xp_invested; it is never destroyed. Level is a "
            "projection of xp_invested."
        )
        self.assertEqual(got[0].holds, want)
        self.assertEqual(got[0].anchor, "1a2b3c4")


if __name__ == "__main__":
    unittest.main()
