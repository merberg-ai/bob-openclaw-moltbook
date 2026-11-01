"""R3 sanitized OpenClaw diagnostic classification, no real model or network.

All DB, observations, account identity and OpenClaw outcomes are synthetic.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import json
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"src/lib/bob")]
from bob_v08.core import Observation
import bob_v08.r313d_producer as producer

RUN="20261101T010000Z"
ID="11111111-2222-3333-4444-555555555555"
NOW=datetime(2026,11,1,1,50,tzinfo=timezone.utc)
OBS=Observation(RUN,ID,"synthetic author","synthetic title",
                "synthetic text","a"*64,"b"*64,"")
PRIVATE="PRIVATE NEVER DISPLAY ANY OF THIS"


class ProposalDiagnosticTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="bob-r3-diag-fixture-")
        self.addCleanup(temp.cleanup)
        self.home=Path(temp.name)
        self.saved=self.home/"scout"
        self.saved.mkdir(mode=0o700)
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE r3_proposals(source_run TEXT,post_id TEXT)")
        self.db.execute("CREATE TABLE publish_jobs(run_id TEXT,post_id TEXT)")
        self.db.execute(
            "CREATE TABLE r3_lab_audit(id INTEGER PRIMARY KEY, "
            "source_run TEXT,event TEXT,reason TEXT,at TEXT)")
        patched=(
            patch("bob_publish_common.DATA",self.saved),
            patch("bob_publish_common.connect",return_value=self.db),
            patch("bob_r313d_owner.trusted_manager_boundary",return_value=True),
            patch("bob_r313d_owner.schema_ready",return_value=True),
            patch.object(producer,"latest_observations",return_value=(OBS,)),
            patch.object(producer,"read_observation",return_value=OBS),
            patch.object(producer.os,"geteuid",return_value=1001),
            patch.object(producer.pwd,"getpwuid",
                         return_value=SimpleNamespace(pw_dir=str(self.home))),
            patch.object(producer.Path,"home",return_value=self.home),
        )
        for ctx in patched:
            ctx.start()
            self.addCleanup(ctx.stop)

    def run_model(self, model):
        # Each classification case starts with an unseen synthetic source.
        self.db.execute("DELETE FROM r3_lab_audit WHERE event='r313d_skip'")
        self.db.commit()
        result=producer.run_one(model=model,clock=lambda:NOW)
        self.assertFalse(result.attempted)
        self.assertFalse(result.queued)
        self.assertFalse(result.dispatch_authorized)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_jobs").fetchone()[0],0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r3_proposals").fetchone()[0],0)
        return result

    def test_known_openclaw_errors_have_sanitized_specific_categories(self):
        for original,label in (
            ("shadow_agent_unavailable","openclaw_shadow_agent_unavailable"),
            ("shadow_agent_cli_failed","openclaw_shadow_agent_cli_failed"),
            ("shadow_agent_envelope_invalid","openclaw_shadow_agent_envelope_invalid"),
            ("shadow_agent_payload_invalid","openclaw_shadow_agent_payload_invalid"),
            ("a server error with "+PRIVATE,
             "openclaw_invalid_or_unavailable_model_output"),
        ):
            with self.subTest(label=label):
                def failed(*_):
                    raise RuntimeError(original)
                result=self.run_model(failed)
                self.assertEqual(result.status,"refused")
                self.assertEqual(result.reason,label)
                self.assertEqual(result.source_run,RUN)
                self.assertNotIn(PRIVATE,json.dumps(result.__dict__))

    def test_bad_decision_errors_distinct_from_transport(self):
        for output,expected in (
            ("not a JSON response","decision_invalid_model_json"),
            ('{"type":"skip"}',"decision_shape_missing_fields"),
            (json.dumps({"type":"comment","source_run":RUN,"target_id":ID,
                         "reason":"","text":"hello"}),"decision_model_reason_empty"),
            (json.dumps({"type":"skip","source_run":RUN,"target_id":ID,
                         "reason":"skip","text":"not-empty"}),"decision_skip_must_not_contain_text"),
            (json.dumps({"type":"skip","source_run":RUN,
                         "target_id":"eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                         "reason":"","text":""}),"decision_unverified_model_target"),
        ):
            with self.subTest(category=expected):
                result=self.run_model(lambda *_:output)
                self.assertEqual(result.status,"refused")
                self.assertEqual(result.reason,expected)
                self.assertEqual(result.source_run,RUN)
                self.assertNotIn(PRIVATE,json.dumps(result.__dict__))

    def test_shape_reasons_are_structural_only_and_never_expose_model_fields(self):
        fixtures=(
            (json.dumps({"answer":{"type":"skip"}}),"decision_shape_missing_and_extra_fields"),
            (json.dumps({"type":"skip","source_run":RUN,"target_id":ID,
                         "reason":"","text":"","extra":PRIVATE}),
             "decision_shape_extra_fields"),
            (json.dumps({"type":"skip","source_run":RUN,"target_id":ID,
                         "reason":"","text":"","extra":PRIVATE,
                         "unknown":True}),"decision_shape_extra_fields"),
            (json.dumps({"type":"skip","source_run":RUN,"target_id":ID,
                         "reason":0,"text":""}),"decision_shape_invalid_field_values"),
            (json.dumps({"type":"skip","source_run":RUN,"target_id":ID,
                         "reason":"","text":""},ensure_ascii=True),
             "not_a_failure"),
            ("[]","decision_shape_not_object"),
        )
        for reply,category in fixtures:
            with self.subTest(reason=category):
                result=self.run_model(lambda *_:reply)
                if category=="not_a_failure":
                    self.assertEqual(result.status,"skipped")
                else:
                    self.assertEqual(result.status,"refused")
                    self.assertEqual(result.reason,category)
                self.assertNotIn(PRIVATE,json.dumps(result.__dict__))

    def test_r3_prompt_includes_exact_pinned_ids_and_no_unsafe_example_text(self):
        from bob_v08.r313d_producer import r3_decision_prompt
        prompt=r3_decision_prompt(OBS)
        self.assertIn('"type":"skip"',prompt)
        self.assertIn('"source_run":"'+RUN+'"',prompt)
        self.assertIn('"target_id":"'+ID+'"',prompt)
        self.assertIn('"reason":""',prompt)
        self.assertIn('"text":""',prompt)
        self.assertIn("FINAL OUTPUT CONTRACT",prompt)
        self.assertIn("END_UNTRUSTED_MOLTBOOK_JSON",prompt)
        self.assertNotIn(PRIVATE,prompt)

    def test_accepted_format1_zip_is_not_mutated_by_new_skip_logic(self):
        # One accepted release identity must never silently rebuild to the
        # newest source. Only an explicitly new signed release may carry it.
        import io
        import zipfile
        sys.path.insert(0,str(ROOT/"scripts"))
        import build_r313d_off_package as historic
        import build_r3_skip_package as repaired
        historical,_=historic.build()
        updated,_=repaired.build()
        self.assertNotEqual(historical,updated)
        with zipfile.ZipFile(io.BytesIO(historical)) as z:
            content=z.read("bob_v08/r313d_producer.py")
            self.assertNotIn(b"def record_verified_skip(",content)
        with zipfile.ZipFile(io.BytesIO(updated)) as z:
            content=z.read("bob_v08/r313d_producer.py")
            self.assertIn(b"def record_verified_skip(",content)

    def test_valid_skip_is_accepted_without_proposal_or_public_send(self):
        output=json.dumps({"type":"skip","source_run":RUN,
                           "target_id":ID,"reason":"not relevant","text":""})
        result=self.run_model(lambda *_:output)
        self.assertEqual(result.status,"skipped")
        self.assertEqual(result.reason,"bob_chose_not_to_comment")
        self.assertEqual(result.source_run,RUN)

    def test_valid_skip_is_durable_and_next_tick_does_not_reask_same_source(self):
        output=json.dumps({"type":"skip","source_run":RUN,
                           "target_id":ID,"reason":"","text":""})
        first=self.run_model(lambda *_: output)
        self.assertEqual(first.status,"skipped")
        saved=self.db.execute(
            "SELECT source_run,event,reason FROM r3_lab_audit").fetchall()
        self.assertEqual(saved,[(RUN,"r313d_skip","bob_chose_not_to_comment")])
        calls=[]
        def should_not_run(*args):
            calls.append(args)
            raise AssertionError("Old Scout source must not be re-fed to Bob")
        next_result=producer.run_one(model=should_not_run,clock=lambda:NOW)
        self.assertEqual(next_result.status,"none")
        self.assertEqual(next_result.reason,"no_fresh_unseen_source")
        self.assertEqual(calls,[])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r3_lab_audit").fetchone()[0],1)

    def test_next_fresh_scout_source_is_allowed_after_prior_skip(self):
        from dataclasses import replace
        second_run="20261101T012000Z"
        second_post="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        second=replace(OBS,run_id=second_run,post_id=second_post)
        responses=[]
        def natural_response(prompt,key):
            responses.append(key)
            return json.dumps({"type":"skip","source_run":second_run,
                               "target_id":second_post,"reason":"","text":""})
        self.db.execute(
            "INSERT INTO r3_lab_audit(source_run,event,reason,at) "
            "VALUES(?,?,?,?)",
            (RUN,"r313d_skip","bob_chose_not_to_comment",NOW.isoformat()))
        self.db.commit()
        with patch.object(producer,"latest_observations",
                          return_value=(OBS,second)), patch.object(
                          producer,"read_observation",return_value=second):
            result=producer.run_one(model=natural_response,clock=lambda:NOW)
        self.assertEqual(result.status,"skipped")
        self.assertEqual(result.source_run,second_run)
        self.assertEqual(len(responses),1)
        self.assertIn(second_run,responses[0])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r3_lab_audit "
            "WHERE event='r313d_skip'").fetchone()[0],2)

    def test_refused_model_decision_is_not_falsely_recorded_as_a_skip(self):
        result=self.run_model(lambda *_: "not JSON")
        self.assertEqual(result.status,"refused")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM r3_lab_audit").fetchone()[0],0)


    def test_unexpected_exception_text_is_never_exposed(self):
        def unknown(*_):
            raise ValueError(PRIVATE)
        result=self.run_model(unknown)
        self.assertEqual(result.reason,"openclaw_invalid_or_unavailable_model_output")
        self.assertNotIn(PRIVATE,str(result.__dict__))


if __name__=="__main__":
    unittest.main()
