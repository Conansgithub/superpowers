from dataclasses import dataclass, field
from .invariant import STATED, ENFORCED, VIOLATED
from .hash import holds_hash


@dataclass
class Suspect:
    id: str
    where: str  # "a_test.go:3" for a tag anchor, "Anchor:" for the entry line
    want: str   # live fingerprint of current Holds text
    got: str    # the stale fingerprint found


@dataclass
class Result:
    uncovered: list = field(default_factory=list)  # B1
    orphans: list = field(default_factory=list)     # B2
    violated: list = field(default_factory=list)    # B3
    stated: list = field(default_factory=list)      # A1 advisory
    suspect: list = field(default_factory=list)     # B4 advisory

    def blocking(self) -> bool:
        return bool(self.uncovered) or bool(self.orphans) or bool(self.violated)


def check(invs, tags) -> Result:
    """Apply binding-integrity rules to a baseline plus the tags found in the
    test tree. Mirrors due's Go Check. B4 is advisory (not in blocking()).
    """
    known = {inv.id for inv in invs}
    tagged = {tg.id for tg in tags}
    r = Result()
    for inv in invs:
        if inv.status == ENFORCED:
            if inv.id not in tagged:
                r.uncovered.append(inv.id)
        elif inv.status == VIOLATED:
            r.violated.append(inv.id)
        elif inv.status == STATED:
            r.stated.append(inv)
    for tg in tags:
        if tg.id not in known:
            r.orphans.append(tg)
    r.uncovered.sort()
    r.violated.sort()

    # B4: build live Holds hash per invariant and flag a stale Anchor: line in the
    # same pass; then flag stale tag anchors.
    live = {}
    for inv in invs:
        if inv.holds != "":
            live[inv.id] = holds_hash(inv.holds)
        if inv.anchor != "":
            h = live.get(inv.id, "")
            if h != "" and inv.anchor != h:
                r.suspect.append(Suspect(id=inv.id, where="Anchor:", want=h, got=inv.anchor))
    for tg in tags:
        if tg.anchor == "":
            continue
        h = live.get(tg.id)
        if h is not None and tg.anchor != h:
            r.suspect.append(Suspect(id=tg.id, where=f"{tg.file}:{tg.line}", want=h, got=tg.anchor))
    return r
