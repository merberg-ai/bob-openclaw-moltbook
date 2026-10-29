#!/usr/bin/env python3
"""Isolated real-HTTP lifecycle adapter lab. No systemd or production access."""
from __future__ import annotations
import argparse
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time

class FixtureHandler(BaseHTTPRequestHandler):
    response_ok = True
    def do_GET(self):
        if self.path != "/healthz":
            self.send_error(404)
            return
        data = b"healthy" if self.response_ok else b"unhealthy"
        self.send_response(200 if self.response_ok else 503)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *args):
        pass

class IsolatedService:
    """Only manages a private in-process 127.0.0.1 fixture server."""
    def __init__(self, healthy=True):
        self.healthy = healthy
        self.server = None
        self.thread = None
        self.starts = 0
    def start(self):
        if self.server is not None or self.starts >= 2:
            raise ValueError("start refused")
        handler = type("PrivateFixture", (FixtureHandler,), {"response_ok": self.healthy})
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.starts += 1
    def probe(self):
        if self.server is None:
            return False
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        try:
            conn.request("GET", "/healthz", headers={"Host": "127.0.0.1"})
            response = conn.getresponse()
            body = response.read(64)
            return response.status == 200 and body == b"healthy"
        except (OSError, TimeoutError):
            return False
        finally:
            conn.close()
    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=3)
            self.server = None
            self.thread = None

def bounded_health(service, attempts=2):
    if not 1 <= attempts <= 2:
        raise ValueError("invalid health budget")
    return any(service.probe() for _ in range(attempts))

def exercise(scenario):
    if scenario not in {"healthy", "failed-health", "failed-recovery"}:
        raise ValueError("invalid scenario")
    service = IsolatedService(healthy=scenario == "healthy")
    probes = 0
    try:
        service.start()
        probes += 1
        if bounded_health(service):
            return "candidate_healthy", service.starts
        service.stop()
        service.healthy = scenario == "failed-health"
        service.start()
        probes += 1
        if bounded_health(service):
            return "rolled_back", service.starts
        return "recovery_failed", service.starts
    finally:
        service.stop()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("healthy","failed-health","failed-recovery"),
                        default="failed-health")
    args = parser.parse_args()
    try:
        outcome, starts = exercise(args.scenario)
        expected = {"healthy":"candidate_healthy","failed-health":"rolled_back",
                    "failed-recovery":"recovery_failed"}[args.scenario]
        if outcome != expected:
            raise ValueError("wrong synthetic result")
    except (OSError, ValueError, AssertionError) as exc:
        print("v0.7.1 HTTP SERVICE ADAPTER: REFUSED", type(exc).__name__)
        return 1
    print("v0.7.1 HTTP SERVICE ADAPTER: PASS")
    print("scenario:", args.scenario)
    print("outcome:", outcome)
    print("isolated_starts:", starts)
    print("real_loopback_http: YES; production_service: UNTOUCHED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
