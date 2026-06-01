import unittest
from specanchor.hash import holds_hash


class TestHoldsHash(unittest.TestCase):
    def test_stable_under_reflow(self):
        a = holds_hash("refund negates the recorded delta")
        b = holds_hash("refund   negates\nthe recorded   delta")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 7)

    def test_changes_on_reword(self):
        self.assertNotEqual(
            holds_hash("refund negates the recorded delta"),
            holds_hash("refund recomputes the delta"),
        )

    def test_pinned_value_matches_go(self):
        # Normalized-whitespace SHA256, first 7 hex; locks byte-parity with due's Go HoldsHash.
        self.assertEqual(holds_hash("refund negates the recorded delta"), "15c4450")
        self.assertEqual(holds_hash("refund recomputes the delta"), "61f6883")


if __name__ == "__main__":
    unittest.main()
