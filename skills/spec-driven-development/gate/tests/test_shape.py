import unittest
from specanchor.shape import KINDS, check_shape


class TestKinds(unittest.TestCase):
    def test_enum(self):
        self.assertEqual(KINDS,
            {"invariant", "event", "unwanted", "contract", "optional", "gap"})


class TestCheckShape(unittest.TestCase):
    def test_unknown_kind_errors(self):
        errs, _ = check_shape("行为·当", "当 X，API SHALL Y", "测试: a_test.go::T")
        self.assertTrue(any("类型" in e for e in errs))

    def test_event_ok(self):
        errs, warns = check_shape("event", "当创建英雄，服务 SHALL 默认激活", "测试: h_test.go::TestH")
        self.assertEqual(errs, [])

    def test_event_missing_shall_errors(self):
        errs, _ = check_shape("event", "当创建英雄，服务默认激活", "测试: h_test.go::TestH")
        self.assertTrue(any("SHALL" in e for e in errs))

    def test_shall_not_counts(self):
        errs, _ = check_shape("invariant", "服务 SHALL NOT 暴露底层类型", "spec:INV-X-1")
        self.assertEqual(errs, [])

    def test_event_pointer_must_be_test(self):
        errs, _ = check_shape("event", "当 X，SHALL Y", "spec:INV-X-1")
        self.assertTrue(any("指针" in e for e in errs))

    def test_invariant_pointer_must_be_tag(self):
        errs, _ = check_shape("invariant", "服务 SHALL X", "测试: a_test.go::T")
        self.assertTrue(any("指针" in e for e in errs))

    def test_contract_exempt_from_shall(self):
        errs, _ = check_shape("contract", "登录接口的契约符合 生成 api/openapi.json", "生成: api/openapi.json")
        self.assertEqual(errs, [])

    def test_gap_exempt(self):
        errs, _ = check_shape("gap", "本地账号无测试守护", "gap: 覆盖缺口")
        self.assertEqual(errs, [])

    def test_gap_pointer_must_be_gap_prefix(self):
        errs, _ = check_shape("gap", "x", "测试: a_test.go::T")
        self.assertTrue(any("指针" in e for e in errs))

    def test_weasel_warns(self):
        errs, warns = check_shape("event", "当 X，服务 SHALL 合理响应", "测试: a_test.go::T")
        self.assertEqual(errs, [])
        self.assertTrue(any("weasel" in w for w in warns))

    def test_compound_shall_warns(self):
        _, warns = check_shape("event", "当 X，SHALL A 且 SHALL B", "测试: a_test.go::T")
        self.assertTrue(any("复合" in w for w in warns))


if __name__ == "__main__":
    unittest.main()
