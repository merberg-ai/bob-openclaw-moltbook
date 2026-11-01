"""R4 memory/relationship review endpoints: HTTPS owner checks, no posts."""
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
import bob_r4_suggestions as suggestions
import bob_r4_projection as projection

RUN="20261101T151033Z"
SEAL="a"*64


class Legacy:
    def __init__(self):
        self.path=f"/r4/suggestion/{RUN}/memory/approve"
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
    def send_header(self,key,value): self.response_headers[key]=value
    def end_headers(self): pass
    def do_POST(self): self.response="legacy"


class Handler(web.R4HandlerMixin,Legacy):
    R4_CSRF_TOKEN="synthetic_csrf"


class R4SuggestionsWebTests(unittest.TestCase):
    def make(self,csrf="synthetic_csrf",kind="memory",operation="approve"):
        h=Handler()
        h.path=f"/r4/suggestion/{RUN}/{kind}/{operation}"
        h.form({"csrf":csrf,"seal":SEAL,
                "confirmation":operation.upper()+" R4 "+
                               kind.upper()+" "+RUN})
        return h

    def test_unauthorized_requests_never_reach_memory_suggestions(self):
        for key,expected in (("good_host",403),("good_auth","auth"),
                             ("good_origin",403)):
            with self.subTest(key=key):
                h=self.make()
                setattr(h,key,False)
                with patch.object(suggestions,"review",
                    side_effect=AssertionError("no review without auth")):
                    h.do_POST()
                self.assertEqual(h.response,expected)
        h=self.make(csrf="invalid")
        with patch.object(suggestions,"review",
            side_effect=AssertionError("no review without csrf")):
            h.do_POST()
        self.assertEqual(h.response,403)

    def test_exact_owner_review_reaches_only_private_suggestion_function(self):
        @contextmanager
        def private():
            yield "synthetic_private_db"
        h=self.make(kind="relationship")
        with patch.object(web,"publish_conn",private), \
             patch("bob_r313d_package.load_verified",return_value="verified_registry_archive"), \
             patch("bob_r313d_owner.trusted_manager_boundary",return_value=True), \
             patch.object(suggestions,"review",return_value={"state":"approved"}) as tested:
            h.do_POST()
        self.assertEqual(h.response,303)
        self.assertEqual(h.response_headers["Location"],"/r4/inbox")
        self.assertEqual(tested.call_count,1)
        args,kw=tested.call_args
        from bob_publish_common import DATA
        self.assertEqual(args,(
            "synthetic_private_db",DATA,RUN,"relationship",SEAL,
            "approve","APPROVE R4 RELATIONSHIP "+RUN))
        self.assertTrue(kw["trusted"])
        self.assertIsNotNone(kw["at"].tzinfo)

    def test_source_linked_suggestion_text_is_escaped_and_follow_unknown(self):
        data=projection.empty()
        data["available"]=True
        data["r4_suggestions"]=[{
            "source_run":RUN,"kind":"relationship","state":"pending",
            "social_state":"proposed","seal":SEAL,
            "title":"<script>bad</script>","detail":"<img onerror=bad>",
            "source_author":"Someone","applied_ref":""}]
        html=web.content("inbox",data,"synthetic_csrf")
        self.assertNotIn("<script>bad</script>",html)
        self.assertNotIn("<img onerror=bad>",html)
        self.assertIn("&lt;script&gt;",html)
        self.assertIn("APPROVE R4 RELATIONSHIP "+RUN,html)
        self.assertIn("Friend Discovery",html)
        self.assertIn("not the Friends directory",html)

    def test_rejected_social_parent_never_has_suggestion_approve_control(self):
        data=projection.empty()
        data["available"]=True
        data["r4_suggestions"]=[{
            "source_run":RUN,"kind":"memory","state":"pending",
            "social_state":"rejected","seal":SEAL,
            "title":"Unconfirmed","detail":"Bob had an opinion",
            "source_author":"Someone","applied_ref":""}]
        html=web.content("inbox",data,"token")
        self.assertNotIn(
            f'/r4/suggestion/{RUN}/memory/approve',html)
        self.assertIn(
            f'/r4/suggestion/{RUN}/memory/reject',html)


if __name__=="__main__":
    unittest.main()
