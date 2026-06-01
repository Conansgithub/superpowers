import hashlib


def holds_hash(holds: str) -> str:
    """Short stable fingerprint of an invariant's Holds text.

    Whitespace is normalized (any run collapses to one space) so reflowing
    prose without changing words keeps the hash; rewording changes it.
    Seven hex chars mirror a git short hash. Mirrors due's Go HoldsHash.
    """
    norm = " ".join(holds.split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:7]
