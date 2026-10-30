"""R2 OpenClaw JSON envelope regression tests; no live OpenClaw or network."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bob_v08.core import Observation, parse_decision
from bob_v08.shadow import openclaw_decide, _safe_error_reason


RUN = "20261030T222037Z"
POST = "11111111-2222-3333-4444-555555555555"
SESSION = "moltbook-v08-shadow-" + RUN


def decision():
    return json.dumps({
        "type": "skip", "source_run": RUN, "target_id": POST,
        "reason": "No interesting topic to contribute to", "text": ""})


def envelope(reply, **other):
    return json.dumps({"status": "ok", "runId": "synthetic",
                       "summary": "synthetic", "result": {
                           "payloads": [{"text": reply}], "meta": {}}, **other})


class OpenClawEnvelopeTests(unittest.TestCase):
    def test_user_observed_nested_result_payload_is_decoded_and_validated(self):
        want = decision()
        captured = []
        def fake_run(command, *, env, capture_output, text, timeout, check):
            captured.append(command)
            self.assertIn("--json", command)
            self.assertEqual(command[command.index("--agent") + 1], "main")
            file = Path(command[command.index("--message-file") + 1])
            self.assertEqual(file.read_text(), "safe synthetic test")
            self.assertEqual(timeout, 300)
            return subprocess.CompletedProcess(command, 0, envelope(want), "")
        with patch("bob_v08.shadow.subprocess.run", side_effect=fake_run):
            reply = openclaw_decide("safe synthetic test", SESSION)
        self.assertEqual(reply, want)
        self.assertEqual(len(captured), 1)
        obs = Observation(RUN, POST, "author", "title", "content", "a" * 64,
                          "b" * 64, "")
        action = parse_decision(reply, obs)
        self.assertEqual(action.kind, "skip")
        self.assertEqual(action.target_id, POST)

    def test_nonzero_exit_and_broken_envelopes_fail_without_disclosing_data(self):
        cases = [
            (1, "not-json", "private stderr", "shadow_agent_cli_failed"),
            (0, "not-json", "", "shadow_agent_envelope_invalid"),
            (0, json.dumps({"status":"error","result":{"payloads":[]}}), "",
             "shadow_agent_envelope_invalid"),
            (0, json.dumps({"status":"ok","result":{"payloads":[]}}), "",
             "shadow_agent_payload_invalid"),
            (0, json.dumps({"status":"ok","result":{"payloads":[{"text":"{}"},{"text":"{}"}]}}), "",
             "shadow_agent_payload_invalid"),
            (0, json.dumps({"status":"ok","result":{"payloads":[{"text":None}]}}), "",
             "shadow_agent_payload_invalid"),
        ]
        for exit_code, stdout, stderr, reason in cases:
            with self.subTest(reason=reason, stdout=stdout[:24]):
                reply = subprocess.CompletedProcess(["openclaw"], exit_code, stdout, stderr)
                with patch("bob_v08.shadow.subprocess.run", return_value=reply):
                    with self.assertRaises((ValueError, RuntimeError)) as err:
                        openclaw_decide("safe synthetic test", SESSION)
                self.assertEqual(str(err.exception), reason)
                self.assertEqual(_safe_error_reason(err.exception), reason)
                self.assertNotIn("private stderr", str(err.exception))

    def test_fail_closed_on_untrusted_decision_even_with_valid_envelope(self):
        bad = '{"type":"comment","source_run":"' + RUN + '","target_id":"' + (
            "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee") + '","reason":"wrong target","text":"hello"}'
        with patch("bob_v08.shadow.subprocess.run",
                   return_value=subprocess.CompletedProcess(
                       ["openclaw"], 0, envelope(bad), "")):
            reply = openclaw_decide("safe synthetic test", SESSION)
        obs = Observation(RUN, POST, "author", "title", "content", "a" * 64,
                          "b" * 64, "")
        with self.assertRaisesRegex(ValueError, "unverified_model_target"):
            parse_decision(reply, obs)

    def test_unknown_internal_error_is_not_logged_raw(self):
        self.assertEqual(_safe_error_reason(RuntimeError("private token data")),
                         "invalid_or_unavailable_model_output")
        with self.assertRaisesRegex(ValueError, "unexpected_shadow_session"):
            openclaw_decide("safe synthetic test", "untrusted")


if __name__ == "__main__":
    unittest.main()
