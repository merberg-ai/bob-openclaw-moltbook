"""R4 Inbox exact review POST: inherited Host/Auth/Origin/CSRF gates.

All tests are synthetic Handler objects. No localhost server, publisher or
Moltbook API is touched. Test mode does not create a production database.
"""
from contextlib import contextmanager
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/lib/bob"))
import bob_r4_web as web
import bob_r4_ledger as ledger

RUN="20261101T151033Z"
SEAL="a"*64


class Legacy:
    def __init__(self):
        self.path="/r4/review/"+RUN+"/approve"
        self.good_host=True
        self.good_auth=True
        self.good_origin=True
        self.response=None
        self.headers={}
        self.rfile=io.BytesIO()
        self.response_headers={}
    def form(self,data):
        raw=urlencode(data).encode()
        self.headers={"Content-Length":str(len(raw))}
        self.rfile=io.BytesIO(raw)
    def _valid_host(self): return self.good_host
    def _authenticated(self): return self.good_auth
    def _valid_origin(self): return self.good_origin
    def _auth_required(self): self.response="auth"
    def _send(self,status,*args): self.response=status
    def _error_page(self,status,*args): self.response=status
    def send_response(self,status): self.response=status
    def send_header(self,name,value): self.response_headers[name]=value
    def end_headers(self): pass
    def do_POST(self): self.response="legacy"


class Handler(web.R4HandlerMixin,Legacy):
    R4_CSRF_TOKEN="synthetic_csrf"


class R4OwnerReviewWebTests(unittest.TestCase):
    def setUp(self):
        self.h=Handler()
        self.form()

    def form(self,**changes):
        values={"csrf":"synthetic_csrf","seal":SEAL,
                "confirmation":"APPROVE R4 "+RUN}
        values.update(changes)
        self.h.form(values)

    def test_bad_host_login_origin_or_csrf_cannot_call_review(self):
        for field,expected in (("good_host",403),
                               ("good_auth","auth"),
                               ("good_origin",403)):
            with self.subTest(field=field):
                h=Handler()
                h.form({"csrf":"synthetic_csrf","seal":SEAL,
                        "confirmation":"APPROVE R4 "+RUN})
                setattr(h,field,False)
                with patch.object(ledger,"review",
                    side_effect=AssertionError("no db or review before owner gate")):
                    h.do_POST()
                self.assertEqual(h.response,expected)
        self.form(csrf="bad")
        with patch.object(ledger,"review",
                side_effect=AssertionError("CSRF must prevent owner review")):
            self.h.do_POST()
        self.assertEqual(self.h.response,403)

    def test_valid_review_forwards_exact_run_seal_and_typed_phrase_only(self):
        @contextmanager
        def mock_conn():
            yield "synthetic_db"
        with patch.object(web,"publish_conn",mock_conn), \\
             patch("bob_r313d_package.load_verified",return_value="verified_registry_archive"), \\
             patch("bob_r313d_owner.trusted_manager_boundary",return_value=True), \\
             patch.object(ledger,"review",return_value="approved") as reviewed:
            self.h.do_POST()
        self.assertEqual(self.h.response,303)
        self.assertEqual(self.h.response_headers["Location"],"/r4/inbox")
        self.assertEqual(reviewed.call_count,1)
        args,kwargs=reviewed.call_args
        self.assertEqual(args[:6],(
            "synthetic_db",web_path_source(),RUN,SEAL,
            "approve","APPROVE R4 "+RUN))
        self.assertTrue(kwargs["trusted"])
        self.assertEqual(kwargs["at"].tzinfo is not None,True)

    def test_unexpected_extra_form_field_is_rejected(self):
        self.h.form({"csrf":"synthetic_csrf","seal":SEAL,
                     "confirmation":"APPROVE R4 "+RUN,
                     "queue":"true"})
        self.h.do_POST()
        self.assertEqual(self.h.response,409)

    def test_other_r4_paths_delegate_to_existing_manager(self):
        self.h.path="/r3/review/"+RUN+"/approve"
        self.h.do_POST()
        self.assertEqual(self.h.response,"legacy")


def web_path_source():
    from bob_publish_common import DATA
    return DATA


if __name__=="__main__":
    unittest.main()
