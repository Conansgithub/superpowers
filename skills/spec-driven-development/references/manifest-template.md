# Module manifest — template

One file per module, e.g. `spec/<module>/spec.md`. Not prose — a one-line note plus a rule table. The real artifact for each rule lives in the test or generated file it points to; the table is just an index.

```
## <module> — manifest
Note: <one or two lines: what this module is>

| ID | Rule sentence | Kind | Binds to | Status |
|----|---------------|------|----------|--------|
| <module>-<n> | <one-sentence rule> | invariant / behavior-when / behavior-if / contract / toggle | <pointer> | stated/enforced/violated |
```

Pointer forms by kind:
- invariant → `spec:INV-*` (a tag)
- behavior → `test: path/to/file_test.go::TestFunc`
- contract → `生成: api/openapi.json` (a generated artifact; the `生成` marker classifies it)

Example row (Chinese, SHALL-style):
`| RC-2 | 当登录成功时，API SHALL 返回 code=100000。 | behavior-when | test: internal/auth/login_test.go::TestLogin_Envelope | enforced |`
