import unittest
from specanchor.manifest import Manifest, Requirement
from specanchor.invariant import Invariant
from specanchor import audit


class FakeRunner:
    """run() 按预设返回;staleness 只用 blame_line/log_since,故拦 args。"""
    def __init__(self, blame="rowsha", since_out="abc123\n"):
        self.blame, self.since_out = blame, since_out
    def run(self, args):
        if args[0] == "blame":
            return f"{self.blame} 1 1 1\n", True
        if args[0] == "log":
            return self.since_out, True
        return "", True


def _req(rid, sentence="当 x,系统 SHALL y", status="enforced",
         pointer="测试: pkg/a_test.go::TestA", scope="—", kind="event"):
    return Requirement(id=rid, sentence=sentence, status=status, pointer=pointer,
                       scope=scope, kind=kind, module="m", file="spec/m/spec.md", line=6)


class TestDedup(unittest.TestCase):
    def test_finds_identical_sentences(self):
        m = Manifest("m", [_req("A-1", "同句"), _req("B-2", "同句"), _req("C-3", "异")])
        out = audit.dedup([m])
        self.assertEqual([sorted(g) for g in out], [["A-1", "B-2"]])


class TestProseLint(unittest.TestCase):
    def test_vague_word(self):
        m = Manifest("m", [_req("A-1", "当 x,系统 SHALL 处理等情况")])
        ids = [f[0] for f in audit.prose_lint([m])]
        self.assertIn("A-1", ids)


class TestStaleness(unittest.TestCase):
    def test_flags_when_code_moved_after_row(self):
        m = Manifest("m", [_req("A-1", scope="pkg/**")])
        out = audit.staleness([m], tags=[], root="/x",
                              runner=FakeRunner(since_out="abc\n"), test_suffix="_test.go", ext=".go")
        self.assertEqual([f[0] for f in out], ["A-1"])

    def test_quiet_when_code_quiet(self):
        m = Manifest("m", [_req("A-1", scope="pkg/**")])
        out = audit.staleness([m], tags=[], root="/x",
                              runner=FakeRunner(since_out=""), test_suffix="_test.go", ext=".go")
        self.assertEqual(out, [])

    def test_skips_stated_rows(self):
        m = Manifest("m", [_req("A-1", status="stated", scope="pkg/**")])
        out = audit.staleness([m], tags=[], root="/x",
                              runner=FakeRunner(since_out="abc\n"), test_suffix="_test.go", ext=".go")
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
