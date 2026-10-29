"""Focused offline regression checks for verification and original output formats."""
from __future__ import annotations
import base64
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/lib/bob"))
sys.path.insert(0, str(ROOT / "scripts"))
import audit_comment_visibility as audit
import bob_live_status as status
import build_v072_publication_truth_candidate as display


def import_worker(name):
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(ROOT / "src/bin" / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class OriginalFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = import_worker("bob-original-worker")
        cls.body = "A locally hosted agent can reason about evidence and versioned decisions without pretending its prompts are memory. That is important because persistence should not become an excuse to make unsupported claims about identity, authorship, or human intentions. A careful design records provenance, protects human approval boundaries, and makes changes inspectable by the operator. The interesting question is how much historical context a future agent should be allowed to reuse before that context becomes an unsafe instruction rather than grounded reference material."

    def test_original_markers_remain_supported(self):
        title, body = self.worker.parse_draft(
            "TITLE: Testing bounded context\nBODY_START\n" + self.body + "\nBODY_END")
        self.assertEqual(title, "Testing bounded context")
        self.assertEqual(body, self.body)

    def test_explicit_labelled_body_supported(self):
        title, body = self.worker.parse_draft(
            "**TITLE:** Trust boundaries for local agents\n**BODY:**\n" + self.body)
        self.assertEqual(title, "Trust boundaries for local agents")
        self.assertEqual(body, self.body)

    def test_json_and_markdown_supported(self):
        title, body = self.worker.parse_draft(
            json.dumps({"title": "Why local provenance matters", "body": self.body}))
        self.assertEqual(title, "Why local provenance matters")
        self.assertEqual(body, self.body)
        title, body = self.worker.parse_draft("# Why local provenance matters\n\n" + self.body)
        self.assertEqual(title, "Why local provenance matters")
        self.assertEqual(body, self.body)

    def test_ambiguous_and_oversized_are_refused(self):
        for text in ("Write me an original thought without any field names.", "",
                     '{"title": "Not enough"}', "x" * 65537):
            with self.subTest(text=text[:20]), self.assertRaises(ValueError):
                self.worker.parse_draft(text)

    def test_validated_draft_still_requires_safety_rules(self):
        with self.assertRaises(ValueError):
            self.worker.validate("general", "short", "no")


class VisibilityTests(unittest.TestCase):
    def test_tree_match_and_no_false_match(self):
        a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        self.assertTrue(audit.contains_comment([
            {"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
             "replies": [{"id": a, "replies": []}]}], a))
        self.assertFalse(audit.contains_comment([
            {"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"}], a))

    def test_unidentified_comment_is_not_treated_as_visible(self):
        post_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        self.assertEqual(audit.audit_one(post_id, "", opener=object()), "id_unconfirmed")

    def test_read_only_audit_does_not_modify_existing_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "records.sqlite3"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE publish_jobs (run_id TEXT, post_id TEXT, comment_id TEXT, state TEXT, attempted_at TEXT)")
                db.execute("INSERT INTO publish_jobs VALUES (?,?,?,?,?)",
                           ("20261029T022156Z","aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                            None,"published","2026-10-29T02:21:56Z"))
                db.commit()
            results = audit.audit(path, opener=object())
            self.assertEqual(results[0]["public_observation"], "id_unconfirmed")
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT state FROM publish_jobs").fetchone()[0], "published")

    def test_dashboard_uses_unconfirmed_label(self):
        manager, _ = display.build()
        self.assertIn(b"ID unconfirmed; visibility unknown", manager)
        self.assertIn(b"Cancelled before sending", manager)
        self.assertIn(b"visibility unverified", manager)
        self.assertNotIn(b"Confirmed comment jobs", manager)
        compile(manager, "generated-dashboard", "exec")


if __name__ == "__main__":
    unittest.main()
