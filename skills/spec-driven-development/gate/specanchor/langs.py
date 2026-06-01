from dataclasses import dataclass


@dataclass(frozen=True)
class Lang:
    name: str
    test_suffix: str   # scan_dir filter, e.g. "_test.go"
    pointer_ext: str   # ext of a manifest test pointer's file, e.g. "go"
    decl_template: str  # verified-behavior declaration, e.g. "func {fn}("

    def behavior_decl(self, fn: str) -> str:
        return self.decl_template.format(fn=fn)


# To add a language: one row here. Nothing else in the engine is language-aware.
LANGS = {
    "go": Lang("go", "_test.go", "go", "func {fn}("),
    "python": Lang("python", "_test.py", "py", "def {fn}("),
}
