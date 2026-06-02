import unittest
from specanchor.refs import dangling
from specanchor.manifest import Manifest, Requirement
from specanchor.invariant import Invariant


def _man(*ids):
    return Manifest(module="m", requirements=[Requirement(id=i, status="enforced") for i in ids])


class TestDangling(unittest.TestCase):
    def test_guarded_by_resolves(self):
        invs = [Invariant(id="INV-A-1", status="enforced", guarded_by="AUTH-3")]
        self.assertEqual(dangling([_man("AUTH-3")], invs), [])

    def test_guarded_by_dangling(self):
        invs = [Invariant(id="INV-A-1", status="enforced", guarded_by="GHOST-9")]
        out = dangling([_man("AUTH-3")], invs)
        self.assertEqual([r[0] for r in out], ["GHOST-9"])

    def test_test_func_guarded_by_ignored(self):
        invs = [Invariant(id="INV-A-1", guarded_by="internal/x_test.go::TestX")]
        self.assertEqual(dangling([_man("AUTH-3")], invs), [])

    def test_dash_guarded_by_ignored(self):
        invs = [Invariant(id="INV-A-1", guarded_by="—")]
        self.assertEqual(dangling([_man("AUTH-3")], invs), [])

    def test_multi_id_guarded_by(self):
        invs = [Invariant(id="INV-A-1", guarded_by="AUTH-3, GHOST-9")]
        self.assertEqual([r[0] for r in dangling([_man("AUTH-3")], invs)], ["GHOST-9"])


if __name__ == "__main__":
    unittest.main()
