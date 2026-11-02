"""One R4 generated dashboard over all accepted HTTPS/R3/R2/legacy layers."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import build_ch_https3_manager_candidate as accepted
import build_r4_manager_candidate as r4


class R4ManagerChainTests(unittest.TestCase):
    def test_r4_adds_only_outer_authenticated_route_layer(self):
        old,old_nav=accepted.build()
        manager,nav=r4.build()
        self.assertIn(old.rstrip().split(b"\n")[-2], manager)
        self.assertNotEqual(manager,old)
        self.assertNotEqual(nav,old_nav)
        self.assertIn(b"serve_tls(Handler, HOST, PORT)",manager)
        self.assertIn(b"HTTPSOnlyHandlerMixin",manager)
        self.assertIn(b"class Handler(R3HandlerMixin, _LegacyHandler):",manager)
        self.assertIn(b"class Handler(R4HandlerMixin, _R4PreviousHandler):",manager)
        self.assertIn(b"R4_CSRF_TOKEN = TOKEN",manager)
        self.assertIn(b'("/r4/now", "Bob R4',nav)
        self.assertIn(b'("/r3", "Bob R3 Controls",',nav)
        self.assertIn(b'("/v08/now", "Bob v0.8',nav)
        self.assertIn(b'("/moltbook/social-memory",',nav)
        self.assertIn(b'("/mind/memory",',nav)
        self.assertIn(b'("/mind/personality",',nav)
        self.assertIn(b'("/moltbook/friends",',nav)
        self.assertEqual(accepted.build(),(old,old_nav))

    def test_generated_manager_contains_no_new_untrusted_http_listener(self):
        mgr,_=r4.build()
        self.assertEqual(mgr.count(b"serve_tls(Handler, HOST, PORT)"),1)
        self.assertNotIn(b"ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()",mgr)
        self.assertNotIn(b"from bob_moltbook_api import api_key",mgr)
        self.assertNotIn(b"bob-r3-canary-arm --arm",mgr)


if __name__=="__main__":
    unittest.main()
