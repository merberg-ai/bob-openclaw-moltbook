# Archived scripts (frozen, not run)

These are one-off v0.7.1 release-engineering rehearsals, v0.7.2 hot patches and staging labs. No current release manifest, the updater, installed code, CI or a current doc depends on them, and they are kept here for provenance only. Their tests live in `tests/` here and are **not** run by `dev.py` or CI. Their import paths assume the old `scripts/` location.

The selection is computed by dependency closure. A script stays in `scripts/` if any of these reference it, directly or transitively:
- `src/`
- `releases/`
- the CI workflow
- the updater
- a current top-level doc
- a kept test
