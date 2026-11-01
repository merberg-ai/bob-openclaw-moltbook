"""The ONLY prospective R4 entry through Bob's existing publisher.

Production R4 social writes are compiled OFF. Importing this adapter, an
approved R4 proposal or a queued R4 outbox row does not grant permission to
call the Moltbook API. Existing api()/api_key() remain owned exclusively
by the original publisher process, and no second publisher or timer exists.

Offline synthetic action send/receipt exercises live in bob_r4_outbox,
not inside the real publisher. Never use an environment flag or model output
to bypass the source-off gates.
"""
from __future__ import annotations

R4_REAL_DISPATCH_COMPILED_OFF=True


def maybe_r4_publisher_step(db,*,api_call,credential_loader):
    """Publisher-callable disabled integration. No credential access."""
    if R4_REAL_DISPATCH_COMPILED_OFF:
        return None
    # Do not silently activate a partial implementation by flipping one bit.
    # A later signed release must add host, payload, source-age,
    # verified remote post/author GET, rate/cooldown and receipt gates here.
    # All approved R4 social proposals remain private until that review.
    return "R4 public integration incomplete; fail closed"
