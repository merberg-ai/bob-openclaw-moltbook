"""Single reviewed source of Bob release identities and their properties.

Every component that must recognise a release (updater, bobctl, installed
gate, R4 scheduler, acceptance reports) reads THIS table instead of keeping
its own hardcoded list. A new signed release is one reviewed entry here plus
its manifest. Unknown identities fail closed everywhere: lookups return
None/False, never a permissive default.

This module is pure data: no I/O, no environment, no network. It is installed
flat next to the other ``bob_*`` modules and verified by the updater registry
hash like any other code file.

Families (what a membership PERMITS is decided by the consuming code, not
here; membership never grants Moltbook send authority):

``r4``           R4 installed-code attestation accepts this registry release.
``r4_patch``     Pre-install requires the original publisher idle and prints
                 the safe R4 refusal stage (updater).
``r4_schedule``  Release carries the R4 scheduler. The registry must include
                 the scheduler files; code-only rollback refuses while R4 units
                 exist; a schedule journal written under any family member is
                 acceptable provided the exact unit bytes still match.
"""
from __future__ import annotations

FORMAT = "bob-release-lineage-v1"

# id: (predecessor or None if not recorded here, manager transport, families)
RELEASES: dict[str, tuple[str | None, str, frozenset[str]]] = {
    "v0.8.0-r3stage1": (None, "http", frozenset()),
    "v0.8.0-chhttps1": (None, "http", frozenset()),
    "v0.8.0-chhttps3": (None, "https", frozenset()),
    "v0.8.0-cutover1": (None, "https", frozenset()),
    "v0.8.0-r3diag1": (None, "https", frozenset()),
    "v0.8.0-r3format1": (None, "https", frozenset()),
    "v0.8.0-r3skip1": (None, "https", frozenset()),
    "v0.8.0-r3canary1": (None, "https", frozenset()),
    "v0.8.0-autonomy1": ("v0.8.0-r3canary1", "https", frozenset({"r4"})),
    "v0.8.0-r4propose1": ("v0.8.0-autonomy1", "https", frozenset({"r4", "r4_patch"})),
    "v0.8.0-r4format1": ("v0.8.0-r4propose1", "https", frozenset({"r4", "r4_patch"})),
    "v0.8.0-r4schedule1": ("v0.8.0-r4format1", "https",
                           frozenset({"r4", "r4_patch", "r4_schedule"})),
    "v0.8.0-r4schedule2": ("v0.8.0-r4schedule1", "https",
                           frozenset({"r4", "r4_patch", "r4_schedule"})),
}

# The release this source tree describes. The R4 scheduler stamps it into
# newly written journals and status output. Bump together with a new entry.
LATEST = "v0.8.0-r4schedule2"

TRANSPORTS = frozenset(("http", "https"))
FAMILIES = frozenset(("r4", "r4_patch", "r4_schedule"))


def known(release: object) -> bool:
    return isinstance(release, str) and release in RELEASES


def transport(release: object) -> str | None:
    return RELEASES[release][1] if known(release) else None


def predecessor(release: object) -> str | None:
    return RELEASES[release][0] if known(release) else None


def in_family(release: object, family: str) -> bool:
    if family not in FAMILIES:
        raise ValueError("unknown_release_family")
    return known(release) and family in RELEASES[release][2]


def family(name: str) -> frozenset[str]:
    if name not in FAMILIES:
        raise ValueError("unknown_release_family")
    return frozenset(r for r, (_, _, fams) in RELEASES.items() if name in fams)


def manager_transports() -> dict[str, str]:
    return {r: t for r, (_, t, _) in RELEASES.items()}


def rollback_predecessors() -> dict[str, str]:
    """Completed-R4 code rollback map: only R4 releases with a recorded predecessor."""
    return {r: p for r, (p, _, f) in RELEASES.items() if p and "r4" in f}


def _self_check() -> None:
    assert LATEST in RELEASES
    for rid, (prev, trans, fams) in RELEASES.items():
        assert trans in TRANSPORTS and fams <= FAMILIES, rid
        assert prev is None or prev in RELEASES, rid
        assert not ("r4_schedule" in fams and "r4" not in fams), rid


_self_check()
