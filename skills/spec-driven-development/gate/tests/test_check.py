import unittest
from specanchor.check import check
from specanchor.invariant import Invariant, ENFORCED, STATED, VIOLATED
from specanchor.tags import TagRef
from specanchor.hash import holds_hash


class TestCheck(unittest.TestCase):
    def test_b1_b2_b3_stated(self):
        invs = [
            Invariant(id="INV-LEDGER-1", status=ENFORCED),
            Invariant(id="INV-LEDGER-2", status=ENFORCED),  # uncovered → B1
            Invariant(id="INV-RES-3", status=STATED),       # advisory
            Invariant(id="INV-CFG-1", status=VIOLATED),     # B3
        ]
        tags = [
            TagRef(id="INV-LEDGER-1", file="a_test.go", line=3),
            TagRef(id="INV-GHOST-9", file="b_test.go", line=7),  # orphan → B2
        ]
        r = check(invs, tags)
        self.assertEqual(r.uncovered, ["INV-LEDGER-2"])
        self.assertEqual([o.id for o in r.orphans], ["INV-GHOST-9"])
        self.assertEqual(r.violated, ["INV-CFG-1"])
        self.assertEqual([s.id for s in r.stated], ["INV-RES-3"])
        self.assertTrue(r.blocking())

    def test_all_stated_not_blocking(self):
        r = check([Invariant(id="INV-RES-1", status=STATED)], [])
        self.assertFalse(r.blocking())

    def test_b4_suspect_order_and_advisory(self):
        holds = "refund negates the recorded delta"
        live = holds_hash(holds)
        invs = [
            Invariant(id="INV-LEDGER-1", status=ENFORCED, holds=holds),         # tag anchor stale → B4a
            Invariant(id="INV-RES-2", status=ENFORCED, holds="x", anchor="dead000"),  # Anchor line stale → B4b
        ]
        tags = [
            TagRef(id="INV-LEDGER-1", file="a_test.go", line=3, anchor="0000000"),
            TagRef(id="INV-RES-2", file="b_test.go", line=9),
        ]
        r = check(invs, tags)
        self.assertEqual(len(r.suspect), 2)
        self.assertEqual((r.suspect[0].where, r.suspect[0].id), ("Anchor:", "INV-RES-2"))
        self.assertEqual((r.suspect[1].where, r.suspect[1].id), ("a_test.go:3", "INV-LEDGER-1"))
        self.assertFalse(r.blocking())  # B4 advisory
        # matching anchor → no longer suspect
        tags[0].anchor = live
        self.assertEqual(len(check(invs[:1], tags[:1]).suspect), 0)


if __name__ == "__main__":
    unittest.main()
