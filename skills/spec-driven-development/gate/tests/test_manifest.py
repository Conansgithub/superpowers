import unittest
from specanchor.manifest import parse_manifest, ManifestError
from specanchor.invariant import ENFORCED, STATED

SAMPLE = (
    "## response-contract — 清单\n"
    "说明：共享响应 envelope、业务错误码、HTTP status 映射。\n\n"
    "| 编号 | 规则句子 | 哪类 | 连到哪 | 状态 |\n"
    "|------|----------|------|--------|------|\n"
    "| RC-1 | API SHALL 把每个响应返回为 {code,message,data,timestamp}。 | 接口 | 生成: api/openapi.json（快照对比） | enforced |\n"
    "| RC-2 | 当登录成功时，API SHALL 返回 code=100000。 | 行为·当 | 测试: internal/gameapi/login_test.go::TestLogin_Envelope | enforced |\n"
    "| RC-9 | 待补的规则。 | 行为·若 | 测试: …/todo_test.go::TestTodo | stated |\n"
)


class TestParseManifest(unittest.TestCase):
    def test_sample(self):
        m = parse_manifest("spec/response-contract/spec.md", SAMPLE)
        self.assertEqual(m.module, "response-contract")
        self.assertEqual(len(m.requirements), 3)
        rc2 = m.requirements[1]
        self.assertEqual(rc2.id, "RC-2")
        self.assertEqual(rc2.status, ENFORCED)
        self.assertEqual(rc2.kind, "行为·当")
        self.assertIn("login_test.go::TestLogin_Envelope", rc2.pointer)
        self.assertEqual(rc2.module, "response-contract")
        self.assertEqual(rc2.file, "spec/response-contract/spec.md")
        self.assertEqual(rc2.line, 7)
        self.assertEqual(m.requirements[2].status, STATED)

    def test_aligned_separator(self):
        md = ("| 编号 | 规则句子 | 哪类 | 连到哪 | 状态 |\n"
              "|:-----|:--------:|-----:|--------|------|\n"
              "| RC-1 | x | 接口 | 生成: a.json | enforced |\n")
        m = parse_manifest("spec/x/spec.md", md)
        self.assertEqual(len(m.requirements), 1)
        self.assertEqual(m.requirements[0].id, "RC-1")

    def test_module_from_dir(self):
        md = ("| 编号 | 规则句子 | 哪类 | 连到哪 | 状态 |\n"
              "|--|--|--|--|--|\n"
              "| AUTH-1 | x | 接口 | 生成: api/x.json | enforced |\n")
        self.assertEqual(parse_manifest("spec/auth/spec.md", md).module, "auth")

    def test_errors(self):
        bad = {
            "unknown status": "| 编号 | 规则句子 | 哪类 | 连到哪 | 状态 |\n|--|--|--|--|--|\n| RC-1 | x | 接口 | 生成: a.json | donezo |\n",
            "wrong columns": "| 编号 | 规则句子 | 哪类 | 连到哪 | 状态 |\n|--|--|--|--|--|\n| RC-1 | x | 接口 | enforced |\n",
            "empty id": "| 编号 | 规则句子 | 哪类 | 连到哪 | 状态 |\n|--|--|--|--|--|\n|  | x | 接口 | 生成: a.json | enforced |\n",
            "dup id": "| 编号 | 规则句子 | 哪类 | 连到哪 | 状态 |\n|--|--|--|--|--|\n| RC-1 | x | 接口 | 生成: a.json | enforced |\n| RC-1 | y | 接口 | 生成: b.json | enforced |\n",
        }
        for name, md in bad.items():
            with self.subTest(name=name):
                with self.assertRaises(ManifestError):
                    parse_manifest("spec/x/spec.md", md)


if __name__ == "__main__":
    unittest.main()
