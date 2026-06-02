import unittest
from specanchor.manifest import parse_manifest, ManifestError, EXPECTED_HEADER
from specanchor.invariant import ENFORCED, STATED

SAMPLE = (
    "## response-contract — 清单\n"
    "说明：共享响应 envelope。\n\n"
    "| 编号 | 陈述 | Why | 类型 | 绑定 | scope | 状态 |\n"
    "|--|--|--|--|--|--|--|\n"
    "| RC-2 | 当登录成功，API SHALL 返回 code=100000。 | 防空值歧义 | event | 测试: internal/gameapi/login_test.go::TestLogin_Envelope | — | enforced |\n"
    "| RC-9 | 当 X，API SHALL Y。 | 待补 | event | 测试: x/todo_test.go::TestTodo | — | stated |\n"
)


class TestParseManifest(unittest.TestCase):
    def test_sample(self):
        m = parse_manifest("spec/response-contract/spec.md", SAMPLE)
        self.assertEqual(m.module, "response-contract")
        self.assertEqual(len(m.requirements), 2)
        rc2 = m.requirements[0]
        self.assertEqual(rc2.id, "RC-2")
        self.assertEqual(rc2.status, ENFORCED)
        self.assertEqual(rc2.kind, "event")
        self.assertEqual(rc2.why, "防空值歧义")
        self.assertEqual(rc2.scope, "—")
        self.assertIn("login_test.go::TestLogin_Envelope", rc2.pointer)
        self.assertEqual(rc2.module, "response-contract")
        self.assertEqual(rc2.file, "spec/response-contract/spec.md")
        self.assertEqual(rc2.line, 6)
        self.assertEqual(m.requirements[1].status, STATED)

    def test_module_from_dir(self):
        md = ("| 编号 | 陈述 | Why | 类型 | 绑定 | scope | 状态 |\n"
              "|--|--|--|--|--|--|--|\n"
              "| AUTH-1 | 服务 SHALL x | w | event | 测试: a_test.go::T | — | enforced |\n")
        self.assertEqual(parse_manifest("spec/auth/spec.md", md).module, "auth")

    def test_aligned_separator(self):
        md = ("| 编号 | 陈述 | Why | 类型 | 绑定 | scope | 状态 |\n"
              "|:--|:--:|--:|--|--|--|--|\n"
              "| RC-1 | 服务 SHALL x | w | event | 测试: a_test.go::T | — | enforced |\n")
        m = parse_manifest("spec/x/spec.md", md)
        self.assertEqual(len(m.requirements), 1)
        self.assertEqual(m.requirements[0].id, "RC-1")

    def test_expected_header_constant(self):
        self.assertEqual(EXPECTED_HEADER,
            ["编号", "陈述", "Why", "类型", "绑定", "scope", "状态"])

    def test_errors(self):
        good_hdr = "| 编号 | 陈述 | Why | 类型 | 绑定 | scope | 状态 |\n|--|--|--|--|--|--|--|\n"
        bad = {
            "wrong header": "| 编号 | 规则句子 | 哪类 | 连到哪 | 状态 |\n|--|--|--|--|--|\n| RC-1 | x | 接口 | 生成: a.json | enforced |\n",
            "wrong columns": good_hdr + "| RC-1 | x | y | event | 测试: a_test.go::T | enforced |\n",
            "unknown status": good_hdr + "| RC-1 | x | y | event | 测试: a_test.go::T | — | donezo |\n",
            "empty id": good_hdr + "|  | x | y | event | 测试: a_test.go::T | — | enforced |\n",
            "dup id": good_hdr + "| RC-1 | x | y | event | 测试: a_test.go::T | — | enforced |\n| RC-1 | z | y | event | 测试: b_test.go::T | — | enforced |\n",
        }
        for name, md in bad.items():
            with self.subTest(name=name):
                with self.assertRaises(ManifestError):
                    parse_manifest("spec/x/spec.md", md)


if __name__ == "__main__":
    unittest.main()
