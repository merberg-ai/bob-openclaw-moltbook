"""Focused offline tests for Bob's compact queue manager.

Synthetic in-memory data only. No Moltbook network calls, live DB, workers,
dashboard restarts or host credentials.
"""
from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_dashboard_manage as mgr
import bob_originals
import build_v072_dashboard_manage_candidate as candidate


def fixture_db():
    db=sqlite3.connect(":memory:")
    db.execute("CREATE TABLE decisions(run_id TEXT PRIMARY KEY,draft_sha256 TEXT,status TEXT,decided_at TEXT)")
    db.execute("CREATE TABLE publish_jobs(run_id TEXT PRIMARY KEY,mode TEXT,state TEXT,draft_comment TEXT,created_at TEXT,post_id TEXT,comment_id TEXT)")
    db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,kind TEXT,details TEXT)")
    bob_originals.initialize(db)
    mgr.initialize(db)
    return db


def state_fn(record, decisions):
    item=decisions.get(record["run_id"])
    return item[1] if item and item[0]==record["approval_sha256"] else (
        "pending" if record["verified_draft"] else "needs review")


def scout(rid, label="Safe generated comment"):
    sha=mgr.fingerprint("scout-digest",rid)
    return dict(run_id=rid, approval_sha256=sha, chosen_title=label,
                chosen_author="Author", draft_comment="A bounded synthetic draft.",
                verified_draft=True, status="pending")


def original(db, rid, state="draft"):
    title="Test original topic"
    body=("This is a synthetic draft used only for the offline queue review tests. "
          "It intentionally contains no real network credentials or external data.")
    dig=bob_originals.digest("general",title,body)
    db.execute("INSERT INTO original_posts(id,submolt,title,content,digest,state,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
               (rid,"general",title,body,dig,state,"bob","2026-10-29T02:00:00Z","2026-10-29T02:00:00Z"))
    return rid+":"+dig


class QueueManagerTests(unittest.TestCase):
    def setUp(self):
        self.db=fixture_db()
        self.records=[scout("20261029T020000Z"),scout("20261029T030000Z")]

    def tearDown(self):
        self.db.close()

    def selection(self,tab,ident,records=None):
        items=mgr.get_items(self.db,tab,self.records if records is None else records,state_fn)
        row=next(x for x in items if x["id"]==ident)
        return ident+":"+row["digest"]

    def test_bulk_scout_approval_then_queue_does_not_publish(self):
        keys=[self.selection("scout",x["run_id"]) for x in self.records]
        count=mgr.apply_batch(self.db,self.records,state_fn,"scout","approve",keys,"")
        self.assertEqual(count,2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM decisions WHERE status='approved'").fetchone()[0],2)
        with patch.object(mgr,"queue_manual") as fake, patch.object(mgr,"original_transition") as original_send:
            count=mgr.apply_batch(self.db,self.records,state_fn,"scout","queue",keys,"QUEUE 2")
            self.assertEqual(count,2)
            self.assertEqual(fake.call_count,2)
            original_send.assert_not_called()

    def test_batch_rejection_and_stale_fingerprint(self):
        keys=[self.selection("scout",x["run_id"]) for x in self.records]
        with self.assertRaises(ValueError):
            mgr.apply_batch(self.db,self.records,state_fn,"scout","reject",
                            [keys[0],keys[1][:-1]+("0" if keys[1][-1]!="0" else "1")],"")
        self.assertEqual(self.db.execute("SELECT count(*) FROM decisions").fetchone()[0],0)
        mgr.apply_batch(self.db,self.records,state_fn,"scout","reject",keys,"")
        self.assertEqual(self.db.execute("SELECT count(*) FROM decisions WHERE status='rejected'").fetchone()[0],2)

    def test_originals_bulk_approve_queue_requires_exact_confirmation(self):
        keys=[original(self.db,"aaaaaaaaaaaaaaaaaaaaaaaa"),
              original(self.db,"bbbbbbbbbbbbbbbbbbbbbbbb")]
        self.db.commit()
        mgr.apply_batch(self.db,[],state_fn,"originals","approve",keys,"")
        with self.assertRaises(ValueError):
            mgr.apply_batch(self.db,[],state_fn,"originals","queue",keys,"PUBLISH")
        self.assertEqual(self.db.execute("SELECT count(*) FROM original_posts WHERE state='queued'").fetchone()[0],0)
        mgr.apply_batch(self.db,[],state_fn,"originals","queue",keys,"QUEUE 2")
        self.assertEqual(self.db.execute("SELECT count(*) FROM original_posts WHERE state='queued'").fetchone()[0],2)

    def test_archive_restore_preserves_originals_and_publishing_state(self):
        key=original(self.db,"aaaaaaaaaaaaaaaaaaaaaaaa",state="approved")
        self.db.commit()
        mgr.apply_batch(self.db,[],state_fn,"originals","archive",[key],"")
        all_items=mgr.get_items(self.db,"originals",[],state_fn)
        self.assertTrue(all_items[0]["hidden"])
        self.assertEqual(len(mgr.filtered(all_items,"all","active","")),0)
        self.assertEqual(len(mgr.filtered(all_items,"all","archived","")),1)
        self.assertEqual(self.db.execute("SELECT state FROM original_posts").fetchone()[0],"approved")
        mgr.apply_batch(self.db,[],state_fn,"originals","restore",[key],"")
        self.assertFalse(mgr.get_items(self.db,"originals",[],state_fn)[0]["hidden"])

    def test_activity_only_archives_never_publishes(self):
        self.db.execute("INSERT INTO publish_jobs VALUES (?,?,?,?,?,?,?)",
                        ("20261029T021111Z","auto","queued","Queued test comment",
                         "2026-10-29T02:11:11Z","post1",None))
        key=self.selection("activity","20261029T021111Z")
        self.assertEqual(mgr.ALLOWED["activity"],("archive","restore"))
        mgr.apply_batch(self.db,[],state_fn,"activity","archive",[key],"")
        self.assertEqual(self.db.execute("SELECT state FROM publish_jobs").fetchone()[0],"queued")
        with self.assertRaises(ValueError):
            mgr.apply_batch(self.db,[],state_fn,"activity","queue",[key],"QUEUE 1")

    def test_pagination_filter_and_selection_limit(self):
        records=[scout("20261029T%02d0000Z"%n,"A mock result %02d"%n) for n in range(23)]
        html=mgr.page(self.db,records,state_fn,
                      {"tab":["scout"],"page":["2"],"q":["mock"]},"fake-token",
                      lambda title,content,route:content)
        self.assertIn("Page 2 of 3",html)
        self.assertEqual(html.count('class="bqm-item"'),10)
        self.assertIn('name="selected"',html)
        selections=[x["run_id"]+":"+x["approval_sha256"] for x in records[:11]]
        with self.assertRaises(ValueError):
            mgr.apply_batch(self.db,records,state_fn,"scout","approve",selections,"")

    def test_candidate_routes_keep_existing_handlers(self):
        code,nav=candidate.build()
        self.assertIn(b'if path == "/manage/bulk":',code)
        self.assertIn(b'elif urlsplit(self.path).path == "/manage":',code)
        self.assertIn(b'def _handle_publication(',code)
        self.assertIn(b'def _handle_original(',code)
        self.assertIn(b'("/manage", "Manage queues", "Manage queues")',nav)
        compile(code,"bob-activity-manager","exec")


if __name__=="__main__":
    unittest.main()
