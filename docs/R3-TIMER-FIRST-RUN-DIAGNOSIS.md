# R3 proposal timer first-run diagnosis

The existing timer has `OnUnitInactiveSec=35min` but no initial `OnActiveSec`. This explains an active timer with `NEXT -` and no service journal before the first run. The permanent repair should preserve the existing handoff journal's original file digests.

No installed-host changes are implied by this note.
