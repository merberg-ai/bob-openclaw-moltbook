"""R4 private outbox owner forms, inherited HTTPS and no-public-send tests."""
from contextlib import contextmanager
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_r4_outbox as outbox
import bob_r4_web as web
import bob_r4_projection as projection

RUN="20261101T151033Z"
SEAL="a"*64


class Legacy:
    def __init__(self):
        self.path="/r4/outbox/"+RUN+"/queue"
        self.response=None
        self.headers={}
        self.rfile=io.BytesIO()
        self.good_host=True
        self.good_auth=True
        self.good_origin=True
        self.response_headers={}
    def form(self,data):
        b=urlencode(data).encode()
        self.headers={"Content-Length":str(len(b))}
        self.rfile=io.BytesIO(b)
    def _valid_host(self):return self.good_host
    def _authenticated(self):return self.good_auth
    def _valid_origin(self):return self.good_origin
    def _auth_required(self):self.response="auth_required"
    def _send(self,status,*args):self.response=status
    def _error_page(self,status,*args):self.response=status
    def send_response(self,status):self.response=status
    def send_header(self,name,value):self.response_headers[name]=value
    def end_headers(self):pass
    def do_POST(self):self.response="legacy"


class Handler(web.R4HandlerMixin,Legacy):
    R4_CSRF_TOKEN="test-csrf"


class R4OutboxOwnerWebTests(unittest.TestCase):
    def make(self,operation="queue",csrf="test-csrf"):
        h=Handler()
        h.path="/r4/outbox/"+RUN+"/"+operation
        phrase=("QUEUE R4 UPVOTE " if operation=="queue"
                else "CANCEL R4 ")+RUN
        h.form({"csrf":csrf,"seal":SEAL,"confirmation":phrase})
        return h

    def test_host_auth_origin_and_csrf_must_precede_queue(self):
        for k,expected in (
                ("good_host",403),("good_auth","auth_required"),
                ("good_origin",403)):
            with self.subTest(k=k):
                h=self.make()
                setattr(h,k,False)
                with patch.object(outbox,"queue",
                      side_effect=AssertionError("bad boundary called queue")):
                    h.do_POST()
                self.assertEqual(h.response,expected)
        h=self.make(csrf="forged")
        with patch.object(outbox,"queue",
                          side_effect=AssertionError("csrf bypassed")):
            h.do_POST()
        self.assertEqual(h.response,403)

    def test_queue_uses_owner_verified_source_and_never_calls_api(self):
        @contextmanager
        def private():
            yield "private_test_db"
        h=self.make()
        with patch.object(web,"publish_conn",private), \
             patch("bob_r313d_package.load_verified",
                   return_value="verified_registry_archive"), \
             patch("bob_r313d_owner.trusted_manager_boundary",
                   return_value=True), \
             patch.object(outbox,"queue",
                          return_value="queued_no_public_send") as f:
            h.do_POST()
        self.assertEqual(h.response,303)
        self.assertEqual(h.response_headers["Location"],"/r4/inbox")
        args,kw=f.call_args
        from bob_publish_common import DATA
        self.assertEqual(args[:5],(
            "private_test_db",DATA,RUN,SEAL,"QUEUE R4 UPVOTE "+RUN))
        self.assertTrue(kw["trusted"])
        self.assertTrue(outbox.PUBLIC_DISPATCH_COMPILED_OFF)

    def test_cancel_can_only_cancel_owner_queued_private_job(self):
        @contextmanager
        def private():
            yield "private_test_db"
        h=self.make(operation="cancel")
        with patch.object(web,"publish_conn",private), \
             patch("bob_r313d_package.load_verified",
                   return_value="verified_registry_archive"), \
             patch("bob_r313d_owner.trusted_manager_boundary",
                   return_value=True), \
             patch.object(outbox,"cancel",
                          return_value="cancelled") as f:
            h.do_POST()
        self.assertEqual(h.response,303)
        _,kw=f.call_args
        self.assertEqual(kw["provided_seal"],SEAL)
        self.assertTrue(kw["trusted"])

    def test_inbox_labels_approved_as_not_queued_and_queue_as_not_sent(self):
        d=projection.empty()
        d["available"]=True
        decision={
            "run":RUN,"seal":SEAL,"kind":"upvote","state":"approved",
            "source_title":"An idea","source_author":"Example_Agent",
            "reason":"An actual expressed reason","body":"","title":"",
            "outbox_state":"none"}
        d["r4_recent"]=[decision]
        html=web.content("inbox",d,"test-csrf")
        self.assertIn("/r4/outbox/"+RUN+"/queue",html)
        self.assertIn("Queue privately (R4 send Off)",html)
        decision["outbox_state"]="queued"
        html=web.content("inbox",d,"test-csrf")
        self.assertNotIn("/r4/outbox/"+RUN+"/queue",html)
        self.assertIn("/r4/outbox/"+RUN+"/cancel",html)
        self.assertIn("No API send is authorized",html)
        decision["outbox_state"]="uncertain"
        html=web.content("inbox",d,"test-csrf")
        self.assertNotIn("/r4/outbox/"+RUN+"/queue",html)
        self.assertNotIn("/r4/outbox/"+RUN+"/cancel",html)
        self.assertIn("no automatic retry",html)


if __name__=="__main__":
    unittest.main()
