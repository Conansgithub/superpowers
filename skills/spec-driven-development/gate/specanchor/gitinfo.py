import subprocess


class GitRunner:
    """git CLI 极薄封装;可注入(测试塞假对象)。永不抛。"""
    def __init__(self, root):
        self.root = root

    def run(self, args):
        try:
            p = subprocess.run(["git", "-C", self.root, *args],
                               capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return "", False
        return p.stdout, p.returncode == 0


def is_repo(runner) -> bool:
    out, ok = runner.run(["rev-parse", "--is-inside-work-tree"])
    return ok and out.strip() == "true"


def blame_line(runner, relpath, line) -> str:
    """relpath:line 最后被碰的 commit SHA;未提交/未知→''。"""
    out, ok = runner.run(["blame", "-L", f"{line},{line}", "--porcelain", "--", relpath])
    if not ok or not out:
        return ""
    sha = out.split(None, 1)[0].strip()
    return "" if set(sha) <= {"0"} else sha


def log_since(runner, commit, files) -> list:
    """<commit>..HEAD 内触碰任一 file 的短 SHA 列表;commit 空/files 空→[]。"""
    if not commit or not files:
        return []
    out, ok = runner.run(["log", f"{commit}..HEAD", "--format=%h", "--", *files])
    if not ok:
        return []
    return [s for s in out.split("\n") if s.strip()]
