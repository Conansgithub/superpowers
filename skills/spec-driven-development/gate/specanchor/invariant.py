import re
from dataclasses import dataclass

STATED = "stated"
ENFORCED = "enforced"
VIOLATED = "violated"


class InvariantError(ValueError):
    """A structural problem in INVARIANTS.md — fail loud, never drop silently."""


@dataclass
class Invariant:
    id: str
    status: str = ""
    since: str = ""
    holds: str = ""   # normalized Holds block text — drives B4
    anchor: str = ""  # optional fingerprint (hex, "sha-" stripped, lowercased)
    guarded_by: str = ""  # raw "Guarded by:" value: manifest-ID ref / test::Func / —


_HEADER_RE = re.compile(r"^###\s+(INV-[A-Z]+(?:-[A-Z]+)*-\d+)\b")
_STATUS_RE = re.compile(r"^Status:\s*(stated|enforced|violated)$")
_SINCE_RE = re.compile(r"^Since:\s*(.+?)$")
_HOLDS_RE = re.compile(r"^Holds:\s*(.*)$")
_ANCHOR_RE = re.compile(r"^Anchor:\s*(?:sha-)?([0-9a-fA-F]+)\s*$")
_GUARDED_RE = re.compile(r"^Guarded by:\s*(.+?)\s*$")
# Lines that terminate a Holds block. Holds itself is the block start, so absent.
_FIELD_START_RE = re.compile(r"^(Why|Guarded by|Anchor|Status|Since):")


def parse_invariants(md: str):
    """Parse INVARIANTS.md. An entry starts at '### INV-...'; its Holds block
    (possibly multi-line) plus Anchor/Status/Since follow until the next header
    or EOF. A header without a Status line, or a duplicate ID, is an error.
    Mirrors due's Go ParseInvariants.
    """
    out = []
    cur = None
    holds = []
    in_holds = False

    def flush():
        nonlocal cur, holds, in_holds
        if cur is None:
            return
        cur.holds = " ".join(holds).strip()
        holds = []
        in_holds = False
        if cur.status == "":
            raise InvariantError(f"invariant {cur.id}: missing Status line")
        out.append(cur)
        cur = None

    for raw in md.split("\n"):
        line = raw.strip()
        m = _HEADER_RE.match(line)
        if m:
            flush()
            cur = Invariant(id=m.group(1))
            continue
        if cur is None:
            continue
        if in_holds and (line == "" or _FIELD_START_RE.match(line)):
            in_holds = False
        m = _HOLDS_RE.match(line)
        if m:
            in_holds = True
            if m.group(1) != "":
                holds.append(m.group(1))
            continue
        if in_holds:
            holds.append(line)
            continue
        m = _ANCHOR_RE.match(line)
        if m:
            cur.anchor = m.group(1).lower()
        m = _STATUS_RE.match(line)
        if m:
            cur.status = m.group(1)
        m = _SINCE_RE.match(line)
        if m:
            cur.since = m.group(1)
        m = _GUARDED_RE.match(line)
        if m:
            cur.guarded_by = m.group(1)
    flush()

    seen = set()
    for inv in out:
        if inv.id in seen:
            raise InvariantError(f"duplicate invariant ID: {inv.id}")
        seen.add(inv.id)
    return out
