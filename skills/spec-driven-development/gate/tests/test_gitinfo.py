import os, subprocess, tempfile, unittest
from specanchor.gitinfo import GitRunner, is_repo, blame_line, log_since


def _git(root, *a):
    subprocess.run(["git", "-C", root, *a], check=True, capture_output=True, text=True)


class TestGitInfo(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        _git(self.d, "init", "-q")
        _git(self.d, "config", "user.email", "t@t")
        _git(self.d, "config", "user.name", "t")
        with open(os.path.join(self.d, "rule.md"), "w") as f:
            f.write("rule line\n")
        os.makedirs(os.path.join(self.d, "pkg"))
        with open(os.path.join(self.d, "pkg/a.go"), "w") as f:
            f.write("package p\n")
        _git(self.d, "add", "-A"); _git(self.d, "commit", "-qm", "c1")
        out, _ = GitRunner(self.d).run(["rev-parse", "HEAD"])
        self.c1 = out.strip()
        with open(os.path.join(self.d, "pkg/a.go"), "a") as f:
            f.write("// changed\n")
        _git(self.d, "add", "-A"); _git(self.d, "commit", "-qm", "c2")

    def test_is_repo(self):
        self.assertTrue(is_repo(GitRunner(self.d)))
        self.assertFalse(is_repo(GitRunner(tempfile.mkdtemp())))

    def test_blame_line(self):
        # rule.md 自 c1 未改 → 第1行 blame 应为 c1 全长 SHA
        self.assertEqual(blame_line(GitRunner(self.d), "rule.md", 1), self.c1)

    def test_log_since_detects_code_change(self):
        # 代码在 c2 改过,晚于 rule 的 c1 → 非空
        self.assertTrue(log_since(GitRunner(self.d), self.c1, ["pkg/a.go"]))

    def test_log_since_quiet_when_unchanged(self):
        self.assertEqual(log_since(GitRunner(self.d), "HEAD", ["pkg/a.go"]), [])


if __name__ == "__main__":
    unittest.main()
