"""R4 installed acceptance probe cannot mutate or publish.

Mocks only. No local Manager socket, Moltbook API, production SQLite or
systemd needed; tests ensure it refuses pre-release/HTTP/invalid routes.
"""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import report_r4_installed as report


class Response:
    status=200
    def read(self,n):
        return b"<html>authenticated R4 read-only source</html>"


class FakeConnection:
    def __init__(self,record):
        self.record=record
    def request(self,method,path,headers=None):
        self.record.append((method,path,headers))
    def getresponse(self):
        return Response()
    def close(self):
        pass


class R4InstalledAcceptanceTests(unittest.TestCase):
    def test_uninstalled_r3_release_refuses_before_network_or_db(self):
        with patch.object(report.updater,"registry",return_value={
                "release":"v0.8.0-r3canary1"}) as reg, \
             patch.object(report.updater,"healthy",
                side_effect=AssertionError("no HTTPS on wrong release")):
            result=report.inspect()
        self.assertFalse(result["signed_installed_source"])
        self.assertFalse(result["authenticated_https"])
        self.assertFalse(result["database_changed_by_report"])
        self.assertFalse(result["public_send_armed_by_report"])
        reg.assert_called_once()

    def test_r4_https_checks_are_get_only_private_host(self):
        calls=[]
        with patch.object(report.updater,"manager_transport",
                          return_value="https"), \
             patch.object(report.updater,"_manager_connection",
                          side_effect=lambda **_:FakeConnection(calls)):
            self.assertTrue(report.authenticated_r4_routes("Basic synthetic"))
        self.assertEqual([x[1] for x in calls],list(report.ROUTES))
        self.assertTrue(all(method=="GET" for method,*_ in calls))
        self.assertTrue(all(h["Host"]=="127.0.0.1:18790"
                            for _,_,h in calls))

    def test_http_transport_refuses_without_fallback(self):
        with patch.object(report.updater,"manager_transport",
                          return_value="http"), \
             patch.object(report.updater,"_manager_connection",
                side_effect=AssertionError("HTTP fallback would be unsafe")):
            self.assertFalse(report.authenticated_r4_routes("none"))

    def test_check_only_cli_never_creates_state(self):
        self.assertEqual(report.main(["--write"]),2)
        with patch.object(report,"inspect",return_value={
            "signed_installed_source":False,
            "legacy_and_r3_registry":False,
            "authenticated_https":False,"new_r4_routes":False,
            "versioned_additive_schema":False,
            "publisher_inactive_at_check":False,
            "new_r4_actions_attempted":None,
        }):
            self.assertEqual(report.main(["--check"]),1)


if __name__=="__main__":
    unittest.main()
