import unittest
from specanchor.langs import LANGS


class TestLangs(unittest.TestCase):
    def test_go(self):
        go = LANGS["go"]
        self.assertEqual(go.test_suffix, "_test.go")
        self.assertEqual(go.pointer_ext, "go")
        self.assertEqual(go.behavior_decl("TestDemo"), "func TestDemo(")

    def test_python(self):
        py = LANGS["python"]
        self.assertEqual(py.test_suffix, "_test.py")
        self.assertEqual(py.pointer_ext, "py")
        self.assertEqual(py.behavior_decl("test_demo"), "def test_demo(")


if __name__ == "__main__":
    unittest.main()
