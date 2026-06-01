#!/usr/bin/env python3
"""Run the language-neutral conformance corpus against spec_check.py by shelling
out, comparing exit code and required stdout/stderr substrings. Implementation-
agnostic: any gate that accepts the same args can be checked against this corpus.
"""
import json
import os
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.dirname(HERE)
SPEC_CHECK = os.path.join(GATE, "spec_check.py")
CASES = os.path.join(HERE, "cases")


def run_case(name):
    cdir = os.path.join(CASES, name)
    with open(os.path.join(cdir, "cmd.txt"), encoding="utf-8") as f:
        args = shlex.split(f.read().strip())
    with open(os.path.join(cdir, "expect.json"), encoding="utf-8") as f:
        expect = json.load(f)
    proc = subprocess.run([sys.executable, SPEC_CHECK] + args, cwd=cdir,
                          capture_output=True, text=True)
    errs = []
    if proc.returncode != expect["exit"]:
        errs.append(f"exit {proc.returncode}, want {expect['exit']}")
    out = proc.stdout + proc.stderr
    for sub in expect.get("stdout_contains", []):
        if sub not in out:
            errs.append(f"missing {sub!r}")
    return errs


def main():
    names = sorted(d for d in os.listdir(CASES)
                   if os.path.isdir(os.path.join(CASES, d)))
    failed = 0
    for name in names:
        errs = run_case(name)
        if errs:
            failed += 1
            print(f"FAIL {name}: {'; '.join(errs)}")
        else:
            print(f"ok   {name}")
    if failed:
        print(f"conformance: {failed}/{len(names)} cases failed")
        return 1
    print(f"conformance: all {len(names)} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
