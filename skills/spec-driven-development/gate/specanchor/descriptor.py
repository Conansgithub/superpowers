import json
import os
from dataclasses import dataclass
from typing import Optional

DESCRIPTOR_NAME = ".spec-check.json"
_KEYS = {"lang", "invariants", "manifests", "skip", "anchor_strict", "resolver",
         "index", "shape_strict", "contracts"}


class DescriptorError(Exception):
    pass


def load_descriptor(root):
    """Load <root>/.spec-check.json. Return None if absent (legacy mode).
    Raise DescriptorError on malformed JSON, unknown keys, or wrong value types.
    """
    path = os.path.join(root, DESCRIPTOR_NAME)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise DescriptorError(f"{path}: {e}")
    if not isinstance(data, dict):
        raise DescriptorError(f"{path}: top level must be a JSON object")
    unknown = set(data) - _KEYS
    if unknown:
        raise DescriptorError(f"{path}: unknown keys {sorted(unknown)}")
    _typecheck(path, data)
    return data


def _typecheck(path, data):
    for k in ("lang", "invariants", "manifests", "resolver", "index", "contracts"):
        if k in data and data[k] is not None and not isinstance(data[k], str):
            raise DescriptorError(f"{path}: {k} must be a string")
    if data.get("index") == "":
        raise DescriptorError(f"{path}: index must be a non-empty string or omitted")
    if "anchor_strict" in data and not isinstance(data["anchor_strict"], bool):
        raise DescriptorError(f"{path}: anchor_strict must be a boolean")
    if "skip" in data:
        ok = isinstance(data["skip"], list) and all(isinstance(x, str) for x in data["skip"])
        if not ok:
            raise DescriptorError(f"{path}: skip must be a list of strings")
    if "shape_strict" in data and data["shape_strict"] not in ("warn", "block"):
        raise DescriptorError(f"{path}: shape_strict must be 'warn' or 'block'")


_DEFAULTS = {
    "lang": None,
    "invariants": "docs/migration/INVARIANTS.md",
    "manifests": "spec/*/spec.md",
    "skip": [],
    "anchor_strict": False,
    "resolver": None,
    "index": None,
    "shape_strict": "block",
    "contracts": None,
}


@dataclass
class ResolvedConfig:
    lang: Optional[str]
    invariants: str
    manifests: str
    skip: list
    anchor_strict: bool
    resolver: Optional[str]
    invariants_from_descriptor: bool
    index: Optional[str]
    index_from_descriptor: bool
    shape_strict: str
    contracts: Optional[str]
    contracts_from_descriptor: bool


def merge(flags, descriptor):
    """Resolve each setting by precedence: explicit flag > descriptor > default.
    `flags` maps key -> value where None means 'not given on the CLI'. `descriptor`
    is the loaded dict (or {} when absent). Only records whether `invariants` came
    from the descriptor (so the caller can join it to root); does no path joining.
    """
    d = descriptor or {}

    def pick(key):
        if flags.get(key) is not None:
            return flags[key], False
        if d.get(key) is not None:
            return d[key], True
        return _DEFAULTS[key], False

    lang, _ = pick("lang")
    invariants, inv_from_desc = pick("invariants")
    manifests, _ = pick("manifests")
    anchor_strict, _ = pick("anchor_strict")
    resolver, _ = pick("resolver")
    skip, _ = pick("skip")
    index, index_from_desc = pick("index")
    shape_strict, _ = pick("shape_strict")
    contracts, contracts_from_desc = pick("contracts")
    return ResolvedConfig(lang, invariants, manifests, list(skip),
                          bool(anchor_strict), resolver, inv_from_desc,
                          index, index_from_desc, str(shape_strict),
                          contracts, contracts_from_desc)
