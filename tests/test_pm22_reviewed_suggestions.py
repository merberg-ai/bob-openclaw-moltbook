"""PM2.2 source-linked suggestion inbox: offline SQLite + verified scout files."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for rel in ("src/lib/bob","webui","scripts"):
    sys.path.insert(0,str(ROOT/rel))

import bob_publish_common as common
import bob_memory as memories
import bob_memory_suggestions as suggestions
import build_v073_pm22_suggestions_candidate as builder
import build_v073_pm2_memory_candidate as previous

RUN="20261029T221200Z"
POST="01234567-89ab-cdef-0123-456789abcdef"
DRAFT="I think this is interesting, but we should verify the author and the timeline."


def fixture():
    db=sqlite3.connect(":memory:")
    db.execute("CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,kind TEXT,details TEXT)")
    db.execute("CREATE TABLE decisions(run_id TEXT PRIMARY KEY,draft_sha256 TEXT,status TEXT,decided_at TEXT)")
    db.execute("INSERT INTO decisions VALUES ('fixture','sha','approved','2026')")
    return db


def make_source(root, *, draft=DRAFT, title="An interesting debate"):
    feed_name="scout-feed-"+RUN+".json"
    feed=json.dumps({"posts":[{"id":POST,"title":title,"content":"Untrusted source body"}]})
    (root/feed_name).write_text(feed)
    snap=hashlib.sha256(feed.encode()).hexdigest()
    approval=hashlib.sha256((POST+"\n"+draft+"\n"+snap).encode()).hexdigest()
    rec=dict(schema=2,run_id=RUN,chosen_post_id=POST,chosen_title=title,
             snapshot_file=feed_name,snapshot_sha256=snap,
             draft_comment=draft,draft_sha256=hashlib.sha256(draft.encode()).hexdigest(),
             approval_sha256=approval,status="pending")
    (root/("scout-result-"+RUN+".json")).write_text(json.dumps(rec))
    return rec


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.patch=patch.object(common,"DATA",self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.db=fixture()
        self.addCleanup(self.db.close)
        self.source=make_source(self.root)
        self.assertEqual(common.load_record(RUN)["run_id"],RUN)

    def pending(self):
        return self.db.execute("SELECT "+",".join(suggestions.COLS)+
                               " FROM bob_memory_suggestions WHERE run_id=?",
                               (RUN,)).fetchone()

    def get(self):
        return dict(zip(suggestions.COLS,self.pending()))

    def test_staging_requires_verified_real_scout_and_deduplicates(self):
        ident=suggestions.stage(self.db,RUN)
        saved=self.get()
        self.assertEqual(saved["id"],ident)
        self.assertEqual(saved["status"],"pending")
        self.assertEqual(saved["source_kind"] if "source_kind" in saved else "scout","scout")
        self.assertNotIn("secret",saved["draft_content"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_memories").fetchone()[0],0)
        with self.assertRaisesRegex(ValueError,"already recorded"):
            suggestions.stage(self.db,RUN)
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_memory_suggestions").fetchone()[0],1)

    def test_approval_is_manual_and_provenance_is_locked(self):
        suggestions.stage(self.db,RUN)
        row=self.get()
        content="Owner-verified note: that historical claim needs independent corroboration."
        payload={"csrf":"test","operation":"approve","id":row["id"],
                 "expected_sha":row["sha256"],"title":"A cautious historical observation",
                 "content":content,"category":"question","confidence":"medium",
                 "reason":"Reviewed claim and kept it tentative"}
        memid=suggestions.dispatch(self.db,payload)
        self.assertEqual(self.get()["status"],"approved")
        self.assertEqual(self.get()["memory_id"],memid)
        memory=memories._get(self.db,memid)
        self.assertEqual(memory["content"],content)
        self.assertEqual(memory["confidence"],"medium")
        self.assertIn(RUN,memory["source_label"])
        self.assertIn(POST,memory["source_label"])
        self.assertEqual(memory["source_url"],"")
        self.assertEqual(memory["version"],1)
        self.assertEqual(self.db.execute("SELECT status FROM decisions").fetchone()[0],"approved")
        with self.assertRaises(ValueError):
            suggestions.dispatch(self.db,payload)
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_memories").fetchone()[0],1)

    def test_explicit_rejection_never_creates_memory(self):
        suggestions.stage(self.db,RUN)
        row=self.get()
        result=suggestions.dispatch(self.db,dict(csrf="test",operation="reject",
             id=row["id"],expected_sha=row["sha256"],reason="Unverified claim"))
        self.assertEqual(result,"")
        self.assertEqual(self.get()["status"],"rejected")
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_memories").fetchone()[0],0)
        with self.assertRaises(ValueError):
            suggestions.dispatch(self.db,dict(csrf="test",operation="reject",
              id=row["id"],expected_sha=row["sha256"],reason="No repeat"))

    def test_changed_or_removed_source_refused_on_stage_or_approval(self):
        path=self.root/("scout-feed-"+RUN+".json")
        path.write_text('{"posts":[]}')
        with self.assertRaisesRegex(ValueError,"unavailable"):
            suggestions.stage(self.db,RUN)
        # Invalid staging aborts before additive tables are initialized.
        self.assertIsNone(self.db.execute(
            "SELECT name FROM sqlite_master WHERE name='bob_memories'").fetchone())
        self.assertIsNone(self.db.execute(
            "SELECT name FROM sqlite_master WHERE name='bob_memory_suggestions'").fetchone())
        make_source(self.root)
        suggestions.stage(self.db,RUN)
        row=self.get()
        record_file=self.root/("scout-result-"+RUN+".json")
        original=json.loads(record_file.read_text())
        original["draft_comment"]="Tampered text"
        record_file.write_text(json.dumps(original))
        with self.assertRaisesRegex(ValueError,"unavailable"):
            suggestions.review(self.db,row["id"],row["sha256"],"approve","Reviewed",
               {"title":"Review title","content":"A note","category":"observation",
                "confidence":"low"})
        self.assertEqual(self.get()["status"],"pending")
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_memories").fetchone()[0],0)

    def test_stale_tampered_or_duplicate_approval_fails_closed(self):
        suggestions.stage(self.db,RUN)
        row=self.get()
        proposal={"title":"Valid title","content":"Evidence needs review",
                  "category":"observation","confidence":"low"}
        with self.assertRaisesRegex(ValueError,"changed"):
            suggestions.review(self.db,row["id"],"0"*64,"approve","review",proposal)
        with self.assertRaisesRegex(ValueError,"Invalid suggestion form"):
            suggestions.dispatch(self.db,dict(csrf="x",operation="approve",id=row["id"],
                expected_sha=row["sha256"],reason="review",**proposal,source_url="https://fake.example"))
        self.db.execute("UPDATE bob_memory_suggestions SET draft_content=? WHERE id=?",
                        ("modified without digest",row["id"]))
        with self.assertRaisesRegex(ValueError,"not found or modified"):
            suggestions.review(self.db,row["id"],row["sha256"],"approve","review",proposal)
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_memories").fetchone()[0],0)

    def test_atomic_rollback_if_memory_created_but_suggestion_update_fails(self):
        suggestions.stage(self.db,RUN)
        self.db.commit()
        row=self.get()
        # The owner-visible mutation handler uses one enclosing publish_conn
        # transaction; emulate its rollback when late failure occurs.
        with patch.object(suggestions,"event",side_effect=sqlite3.OperationalError("synthetic failure")):
            try:
                suggestions.review(self.db,row["id"],row["sha256"],"approve","Reviewed",
                    {"title":"Good title","content":"Good note",
                     "category":"observation","confidence":"low"})
            except sqlite3.OperationalError:
                self.db.rollback()
        self.assertEqual(self.db.execute("SELECT count(*) FROM bob_memories").fetchone()[0],0)
        self.assertEqual(self.get()["status"],"pending")

    def test_html_has_bounded_staging_and_escaped_review(self):
        make_source(self.root,draft="Model says: <script>evil()</script>")
        html=suggestions.page(self.db,"token",lambda title,body,path:body,[self.source])
        self.assertIn("Stage for memory review",html)
        self.assertIn('name="run_id"',html)
        self.assertIn("NOT a new LLM summary",html)
        self.assertNotIn("<script>evil()</script>",html)
        suggestions.stage(self.db,RUN)
        html=suggestions.page(self.db,"token",lambda title,body,path:body,[self.source])
        self.assertIn("Approve as private memory",html)
        self.assertIn("Reject suggestion",html)
        self.assertIn("source post",html)
        self.assertNotIn('name="source_url"',html)
        self.assertNotIn("<script>evil()</script>",html)

    def test_only_new_get_post_and_no_change_to_prior_handlers(self):
        old,old_nav=previous.build()
        new,nav=builder.build()
        self.assertIn(b'elif urlsplit(self.path).path == "/mind/memory/suggestions":',new)
        self.assertIn(b'if path == "/mind/memory/suggestions":',new)
        self.assertIn(b'max_num_fields=11',new)
        self.assertIn(b'self._valid_origin()',new)
        self.assertIn(b'hmac.compare_digest(values.get("csrf"',new)
        self.assertIn(b'/mind/memory/suggestions',nav)
        self.assertIn(b'Suggestion unchanged',new)
        def methods(blob):
            tree=ast.parse(blob)
            cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Handler")
            return {n.name:ast.dump(n,include_attributes=False)
                    for n in cls.body if isinstance(n,ast.FunctionDef)}
        a,b=methods(old),methods(new)
        self.assertEqual(set(b)-set(a),{"_save_memory_suggestion"})
        for n in ("_save_memory","_apply_personality","_save_personality",
                  "_handle_publication","_handle_original","_handle_manage_bulk",
                  "_authenticated","_valid_origin","_change_activity_limits"):
            self.assertEqual(a[n],b[n],n)
        compile(new,"bob-activity-manager","exec")


if __name__=="__main__":
    unittest.main()
