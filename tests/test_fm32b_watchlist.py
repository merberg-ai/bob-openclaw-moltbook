"""FM3.2b: paginated watched friends and verifiable, bounded Scout recency.

Uses disposable SQLite and synthetic locally saved Scout reports only.
No live host, network, timer, model, browser, or publication side effects.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
for folder in ("src/lib/bob","scripts","webui"):
    sys.path.insert(0,str(ROOT/folder))

import bob_friend_scout as scout
import bob_friends as friends
import bob_publish_common as common
import build_v075_logs_candidate as logs_builder
import build_v075_fm32b_candidate as fm_builder

POST="01234567-89ab-cdef-0123-456789abcdef"


def fields(name):
    return dict(display_name="Public label "+name,relationship="interesting",
                interests="PRIVATE INTEREST NOTES",notes="PRIVATE SECRET NOTES")


def saved(root,run,author,*,focused=False,chosen=True):
    post=dict(id=POST,author=author,title="Discussing memory",content="Synthetic post")
    if focused:
        post["from_friend"]=True
    feed=dict(posts=[post],friend_focus=focused)
    raw=json.dumps(feed).encode()
    digest=hashlib.sha256(raw).hexdigest()
    (root/("scout-feed-"+run+".json")).write_bytes(raw)
    draft="This is a review draft, not public."
    record=dict(schema=2,run_id=run,status="pending",
                chosen_post_id=POST,chosen_author=author if chosen else "UnrelatedAuthor",
                chosen_title="Discussing memory",why="I am curious",
                snapshot_file="scout-feed-"+run+".json",snapshot_sha256=digest,
                draft_comment=draft,draft_sha256=hashlib.sha256(draft.encode()).hexdigest(),
                approval_sha256=hashlib.sha256(
                    (POST+"\\n"+draft+"\\n"+digest).encode()).hexdigest())
    (root/("scout-result-"+run+".json")).write_text(json.dumps(record))
    return record


class WatchlistTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.path=self.root/"queue.sqlite3"
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT)")
            db.execute("CREATE TABLE publish_events(id INTEGER PRIMARY KEY AUTOINCREMENT,"
                       "at TEXT,kind TEXT,details TEXT)")
            for n in range(1,26):
                friends.create(db,f"Agent{n:02}",fields(str(n)))
        for name,value in (("DATA",self.root),("DB",self.path)):
            p=patch.object(common,name,value)
            p.start()
            self.addCleanup(p.stop)

    def db(self):
        return sqlite3.connect(self.path)

    def view(self,db,records=None,params=None):
        return scout.page(db,"csrf",lambda title,body,path:body,records or [],params)

    def test_pagination_reaches_all_25_instead_of_first_ten(self):
        with self.db() as db:
            first=self.view(db)
            second=self.view(db,params={"page":["2"]})
            third=self.view(db,params={"page":["3"]})
            clamped=self.view(db,params={"page":["999"]})
        self.assertEqual(first.count('<div class="bfs-card"><strong>@Agent'),10)
        self.assertEqual(second.count('<div class="bfs-card"><strong>@Agent'),10)
        self.assertEqual(third.count('<div class="bfs-card"><strong>@Agent'),5)
        self.assertIn("@Agent01",first)
        self.assertNotIn("@Agent25",first)
        self.assertIn("@Agent25",third)
        self.assertIn("page 3 of 3",clamped)
        self.assertIn("Previous page",third)
        self.assertNotIn("Next page",third)
        self.assertNotIn("PRIVATE SECRET",third)
        self.assertNotIn("PRIVATE INTEREST",third)

    def test_filter_watched_paused_integrity_issues_and_search(self):
        with self.db() as db:
            scout.init_preferences(db)
            a=db.execute("SELECT id FROM bob_friends WHERE handle='Agent21'").fetchone()[0]
            f=friends._get(db,a)
            scout.change(db,dict(csrf="x",operation="watch",id=a,friend_sha=f["sha256"],
                                 watch_sha="default",watch_enabled="0"))
            b=db.execute("SELECT id FROM bob_friends WHERE handle='Agent22'").fetchone()[0]
            b_friend=friends._get(db,b)
            scout.change(db,dict(csrf="x",operation="watch",id=b,
                                 friend_sha=b_friend["sha256"],watch_sha="default",
                                 watch_enabled="0"))
            db.execute("UPDATE bob_friend_watch_prefs SET enabled=1 WHERE friend_id=?",(b,))
            paused=self.view(db,params={"show":["paused"]})
            issues=self.view(db,params={"show":["issues"]})
            watched=self.view(db,params={"show":["watching"]})
            exact=self.view(db,params={"q":["agent21"]})
        self.assertIn("@Agent21",paused)
        self.assertNotIn("@Agent22",paused)
        self.assertIn("@Agent22",issues)
        self.assertNotIn("@Agent21",issues)
        self.assertNotIn("@Agent21",watched)
        self.assertNotIn("@Agent22",watched)
        self.assertIn("@Agent21",exact)
        self.assertNotIn("@Agent20",exact)
        self.assertIn('name="operation" value="watch"',paused)
        self.assertNotIn('name="operation" value="watch"',issues)

    def test_watch_post_keeps_canonical_sanitized_filters(self):
        u=scout.watchlist_location("/moltbook/friend-scout?q=Agent21&show=paused&page=2")
        self.assertEqual(u,"/moltbook/friend-scout?q=Agent21&show=paused&page=2")
        self.assertEqual(scout.watchlist_location(
            "/moltbook/friend-scout?q=%0d%0aSet-Cookie%3Aevil&show=nope&page=99999"),
            "/moltbook/friend-scout?q=Set-Cookie%3Aevil&show=all&page=1")
        self.assertEqual(scout.watchlist_location("/evil?show=paused"),
                         "/moltbook/friend-scout")
        self.assertEqual(scout.watchlist_location("/moltbook/friend-scout?a=1&b=2&c=3&d=4"),
                         "/moltbook/friend-scout")
        with self.db() as db:
            html=self.view(db,params={"q":["Agent21"],"show":["paused"]})
        self.assertIn('action="/moltbook/friend-scout?q=Agent21&amp;show=paused&amp;page=1"',html)
        with self.db() as db:
            attack=self.view(db,params={"q":['"><svg onload=alert(1)>']})
        self.assertIn("&quot;&gt;&lt;svg",attack)
        self.assertNotIn("<svg onload",attack)

    def test_saved_focused_and_selected_dates_are_independently_verified(self):
        observed=saved(self.root,"20261029T220000Z","Agent23",focused=True,chosen=False)
        chosen=saved(self.root,"20261030T010000Z","Agent23",focused=False,chosen=True)
        with self.db() as db:
            active=scout._watch(db,include_disabled=True)
            history=scout.friend_activity([chosen,observed],active)
            fid=next(f["id"] for f in active if f["handle"]=="Agent23")
            self.assertEqual(history[fid]["observed_run"],"20261029T220000Z")
            self.assertEqual(history[fid]["selected_run"],"20261030T010000Z")
            html=self.view(db,[chosen,observed],{"q":["Agent23"]})
            self.assertIn("2026-10-29 22:00 UTC",html)
            self.assertIn("2026-10-30 01:00 UTC",html)
            self.assertIn("Last verified friend-focused source",html)
            self.assertIn("Last selected discussion",html)
            self.assertNotIn("PRIVATE SECRET",html)

    def test_corrupt_source_does_not_fabricate_recent_activity(self):
        rec=saved(self.root,"20261029T220000Z","Agent23",focused=True)
        p=self.root/"scout-feed-20261029T220000Z.json"
        p.write_text('{"posts":[{"author":"Agent23","from_friend":true}]}')
        with self.db() as db:
            activity=scout.friend_activity([rec],scout._watch(db,include_disabled=True))
            self.assertEqual(activity,{})
            html=self.view(db,[rec],{"q":["Agent23"]})
            self.assertIn("No verified saved friend-focused or selected discussion",html)
            self.assertNotIn("Last selected discussion:",html)
        p.unlink()
        with self.db() as db:
            self.assertEqual(scout.friend_activity([rec],
                             scout._watch(db,include_disabled=True)),{})

    def test_valid_global_selection_is_not_mislabeled_as_focus(self):
        rec=saved(self.root,"20261029T220000Z","Agent23",focused=False)
        with self.db() as db:
            a=scout._watch(db,include_disabled=True)
            f=next(x for x in a if x["handle"]=="Agent23")
            history=scout.friend_activity([rec],a)
            self.assertNotIn("observed_run",history[f["id"]])
            self.assertEqual(history[f["id"]]["selected_run"],rec["run_id"])

    def test_builder_is_readonly_plus_same_origin_return_and_existing_import(self):
        before,nav_before=logs_builder.build()
        after,nav_after=fm_builder.build()
        self.assertEqual(nav_before,nav_after)
        self.assertEqual(after.count(b"friend_scout_return_path(self.path)"),1)
        self.assertIn(b"parse_qs(urlsplit(self.path).query[:256]",after)
        # Undo only the three pinned substitutions and require exactly
        # identical previous dashboard bytes, including auth/CSRF handlers.
        backward=after.decode()
        replacements=(
            ("safe_error as friend_scout_safe_error, "
             "watchlist_location as friend_scout_return_path)",
             "safe_error as friend_scout_safe_error)"),
            ("friend_scout_page(db,TOKEN,wrap,load_records(),"
             "parse_qs(urlsplit(self.path).query[:256],keep_blank_values=True))",
             "friend_scout_page(db,TOKEN,wrap,load_records())"),
            ('self.send_header("Location",friend_scout_return_path(self.path))',
             'self.send_header("Location","/moltbook/friend-scout")'),
        )
        for changed,original in replacements:
            self.assertEqual(backward.count(changed),1)
            backward=backward.replace(changed,original)
        self.assertEqual(backward.encode(),before)


if __name__=="__main__":
    unittest.main()
