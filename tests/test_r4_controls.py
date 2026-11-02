"""R4 independently owned policy modes and documented API request shapes."""
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_r4_controls as core


class R4ControlsTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:",isolation_level=None)
        self.addCleanup(self.db.close)
        self.db.execute(
            "CREATE TABLE publish_settings(name TEXT PRIMARY KEY,value TEXT NOT NULL)")
        self.db.execute(
            "CREATE TABLE publish_events(id INTEGER PRIMARY KEY,at TEXT,"
            "kind TEXT,details TEXT)")

    def test_all_six_families_start_off_and_global_pause_on(self):
        self.assertEqual(core.read_modes(self.db),
                         {item:"off" for item in core.ACTIONS})
        self.assertTrue(core.pause_state(self.db))
        self.assertTrue(core.AUTO_ENGINE_COMPILED_OFF)

    def test_propose_is_private_owner_preference_not_post_authority(self):
        after=core.set_mode(
            self.db,"follow","propose","SET R4 FOLLOW PROPOSE",trusted=True)
        self.assertEqual(after["follow"],"propose")
        self.assertTrue(all(after[x]=="off" for x in core.ACTIONS if x!="follow"))
        self.assertEqual(self.db.execute(
            "SELECT kind,details FROM publish_events").fetchall(),
            [("r4_owner_mode","follow:off->propose")])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM publish_settings").fetchone()[0],1)

    def test_auto_off_even_with_typed_owner_phrase(self):
        for action in core.ACTIONS:
            with self.subTest(action=action):
                with self.assertRaisesRegex(ValueError,"r4_auto_worker_not_approved"):
                    core.set_mode(self.db,action,"auto",
                                  f"SET R4 {action.upper()} AUTO",trusted=True)
        self.assertEqual(core.read_modes(self.db),
                         {name:"off" for name in core.ACTIONS})

    def test_typo_untrusted_action_and_invalid_persisted_mode_refused(self):
        for args in (
            ("follow","propose","SET R4 FOLLOW AUTO",True),
            ("follow","propose","SET R4 FOLLOW PROPOSE",False),
            ("all","propose","SET R4 ALL PROPOSE",True),
            ("follow","other","SET R4 FOLLOW OTHER",True),
        ):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    core.set_mode(self.db,*args[:3],trusted=args[3])
        self.db.execute(
            "INSERT INTO publish_settings VALUES('r4_mode_follow','enabled')")
        with self.assertRaises(ValueError):
            core.read_modes(self.db)
        self.db.execute(
            "UPDATE publish_settings SET value='auto' WHERE name='r4_mode_follow'")
        with self.assertRaisesRegex(ValueError,"r4_auto_mode_not_currently_supported"):
            core.read_modes(self.db)

    def test_pause_is_separate_and_does_not_modify_legacy_flags(self):
        self.db.execute("INSERT INTO publish_settings VALUES('auto_enabled','1')")
        self.assertFalse(core.set_pause(self.db,False,"RESUME R4",trusted=True))
        self.assertTrue(core.set_pause(self.db,True,"PAUSE R4",trusted=True))
        self.assertEqual(self.db.execute(
            "SELECT value FROM publish_settings WHERE name='auto_enabled'"
        ).fetchone(),("1",))
        with self.assertRaises(ValueError):
            core.set_pause(self.db,False,"RESUME R4",trusted=False)
        with self.assertRaises(ValueError):
            core.set_pause(self.db,False,"PAUSE R4",trusted=True)

    def test_official_endpoint_contract_never_accepts_arbitrary_url(self):
        post="bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a"
        self.assertEqual(core.api_contract("post",""),("POST","/posts"))
        self.assertEqual(core.api_contract("upvote",post),
                         ("POST","/posts/"+post+"/upvote"))
        self.assertEqual(core.api_contract("reply",post),
                         ("POST","/posts/"+post+"/comments"))
        self.assertEqual(core.api_contract("comment",post),
                         ("POST","/posts/"+post+"/comments"))
        self.assertEqual(core.api_contract("follow","BobFriend"),
                         ("POST","/agents/BobFriend/follow"))
        self.assertEqual(core.api_contract("unfollow","BobFriend"),
                         ("DELETE","/agents/BobFriend/follow"))
        for action,target in (
            ("follow","http://evil"),("follow","a/b"),("follow","a?x=1"),
            ("upvote","https://host"),("upvote","bad"),("post",post),
            ("unknown","anything"),("unfollow","..")):
            with self.subTest(action=action,target=target):
                with self.assertRaises(ValueError):
                    core.api_contract(action,target)


if __name__=="__main__":
    unittest.main()
