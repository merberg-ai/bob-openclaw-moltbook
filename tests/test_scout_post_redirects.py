"""Focused offline regression coverage for dashboard section-local POST redirects.

Only synthetic HTML/SQLite and AST inspection; no network, live database,
publishing worker, credentials or systemd calls.
"""
from __future__ import annotations

import ast
from html import unescape
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for d in ("scripts", "src/lib/bob", "webui", "tests"):
    sys.path.insert(0, str(ROOT / d))
from bob_dashboard_return import scout_destination, section_for_action
import bob_dashboard_compact as compact
import build_v072_overview_candidate as before
import build_v072_post_redirect_candidate as after
from test_compact_scout_activity import database, record, fake_status, fake_wrap


class DashboardReturnTests(unittest.TestCase):
    def test_compact_scout_actions_preserve_filters_page_and_anchor(self):
        target="/scout?state=pending&show=all&q=robots&page=2"
        self.assertEqual(scout_destination({"return_to":[target]},
                                           "20261029T010000Z"),
                         target+"#run-20261029T010000Z")
        self.assertEqual(scout_destination({"return_to":[target]}),target)
        self.assertEqual(scout_destination({}),"/scout")

    def test_legacy_history_has_a_safe_return_destination(self):
        self.assertEqual(scout_destination({"return_to":["/scout/full"]},
                                           "20261029T010000Z"),
                         "/scout/full#run-20261029T010000Z")

    def test_open_redirect_and_invalid_filters_rejected(self):
        attacks = (
            "https://attacker.example/", "//attacker.example/",
            "/", "/activity", "/settings/users",
            "/scout/full?state=pending", "/scout#other",
            "/scout?state=untrusted", "/scout?show=wrong",
            "/scout?state=pending&state=approved",
            "/scout?foreign=1", "/scout?page=0",
            "/scout?state=pending\r\nLocation: //attacker.example/",
        )
        for target in attacks:
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    scout_destination({"return_to":[target]})
        with self.assertRaises(ValueError):
            scout_destination({"return_to":["/scout","/scout/full"]})
        with self.assertRaises(ValueError):
            scout_destination({},run_id="../../invalid")

    def test_compact_forms_all_embed_same_safe_destination(self):
        db=database()
        try:
            items=[record(i) for i in range(18)]
            db.execute("INSERT INTO publish_settings VALUES ('auto_enabled','1')")
            html=compact.scout_page(
                db,items,fake_status,
                {"state":["pending"],"show":["all"],"q":["Draft"],
                 "page":["2"]},"synthetic-csrf",fake_wrap)
            destinations=re.findall(r'name="return_to" value="([^"]+)"',html)
            self.assertTrue(destinations)
            for encoded in destinations:
                self.assertEqual(unescape(encoded),
                    "/scout?state=pending&show=all&q=Draft&page=2")
            self.assertIn('action="/autopost/disable"',html)
            self.assertIn('action="/review/20261029T',html)
            self.assertIn('name="csrf" value="synthetic-csrf"',html)
        finally:
            db.close()

    def test_auto_enable_and_scout_challenge_forms_return_locally(self):
        db=database()
        try:
            records=[record(0)]
            disabled=compact.scout_page(db,records,fake_status,{},"csrf",fake_wrap)
            self.assertIn('action="/autopost/enable"',disabled)
            self.assertIn('name="return_to" value="/scout?state=pending',disabled)
            # Existing challenge still uses its original guarded POST route.
            db.execute("INSERT INTO publish_jobs "
                       "(run_id,mode,state,draft_comment,created_at,post_id,comment_id) "
                       "VALUES (?,?,?,?,?,?,?)",
                       (records[0]["run_id"],"manual","awaiting_verification",
                        "synthetic","2026-10-29T00:00:00Z","postid",None))
            challenge=compact.scout_page(db,records,fake_status,{},"csrf",fake_wrap)
            self.assertIn('action="/verify/'+records[0]["run_id"]+'"',challenge)
            self.assertIn('name="return_to"',challenge)
        finally:
            db.close()

    def test_generated_manager_all_scout_redirects_are_scoped(self):
        source,_=after.build()
        code=source.decode()
        self.assertIn("destination = scout_destination(params, run_id)",code)
        self.assertIn("destination = scout_destination(",code)
        self.assertIn('self.send_header("Location", destination)',code)
        self.assertIn("self.send_header('Location',destination)",code)
        self.assertNotIn('self.send_header("Location", f"/#run-{run_id}")',code)
        self.assertNotIn("self.send_header('Location','/')",code)
        self.assertEqual(code.count('name="return_to" value="/scout/full"'),5)
        self.assertIn('section_for_action(self.path)',code)
        # Confirm other dashboard sections continue returning to themselves.
        self.assertIn("self.send_header('Location','/originals')",code)
        self.assertIn('self.send_header("Location", "/settings/activity-limits")',code)
        self.assertIn('self.send_header("Location", location)',code)

    def test_other_section_actions_keep_existing_logic(self):
        old=ast.parse(before.build()[0])
        new=ast.parse(after.build()[0])
        def methods(tree):
            cls=next(x for x in tree.body if isinstance(x,ast.ClassDef)
                     and x.name=="Handler")
            return {x.name:ast.dump(x,include_attributes=False) for x in cls.body
                    if isinstance(x,ast.FunctionDef)}
        left,right=methods(old),methods(new)
        for method in ("do_GET","_handle_original","_handle_manage_bulk",
                       "_change_password","_change_activity_limits",
                       "_authenticated","_valid_origin"):
            self.assertEqual(left[method],right[method],method)

    def test_error_page_return_matches_originating_section(self):
        sections={
            "/review/20261029T010000Z/approve":"/scout",
            "/publish/20261029T010000Z":"/scout",
            "/verify/20261029T010000Z":"/scout",
            "/autopost/disable":"/scout",
            "/original/aaaaaaaaaaaaaaaaaaaaaaaa/approve":"/originals",
            "/originals/request/thought":"/originals",
            "/manage/bulk":"/manage",
            "/settings/activity-limits":"/settings/activity-limits",
            "/settings/password":"/settings/users",
        }
        for path,expected in sections.items():
            self.assertEqual(section_for_action(path),expected)


if __name__ == "__main__":
    unittest.main()
