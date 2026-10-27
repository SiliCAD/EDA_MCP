import asyncio
import json
import socket
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import src.server as server
import src.core.observer as observer_mod
from src.core.observer import ObserverPort, NOTICE_HEADER, HOLD_MAX_S, VERDICT_UNAVAILABLE

HOLD = {"decision": "hold", "hold_id": 3, "hold_s": 2.0, "message": "deletes layout data",
        "notices": [{"severity": "warn", "text": "risky call"}]}


class FakeObserver:
    """Records every hook call and answers with canned responses."""
    def __init__(self):
        self.calls = []
        self.before_resp = {"decision": "allow"}
        self.after_resp = {"notices": []}
        self.verdict_resp = {"decision": "allow"}
        self.verdict_raw = None                # raw bytes instead of verdict_resp
        self.verdict_drop = False              # close the verdict connection without an answer
        self.delay = 0.0
        self.verdict_delay = 0.0
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.calls.append((self.path, body))
                if self.path == "/v1/verdict":
                    time.sleep(fake.verdict_delay)
                    if fake.verdict_drop:
                        self.close_connection = True
                        return
                    data = fake.verdict_raw if fake.verdict_raw is not None else json.dumps(fake.verdict_resp).encode()
                else:
                    time.sleep(fake.delay)
                    resp = fake.before_resp if self.path == "/v1/before" else fake.after_resp
                    data = json.dumps(resp).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class TestObserverPort(unittest.TestCase):
    """The observer port: plug and play, fail open, block before, notices after."""
    def setUp(self):
        self.fake = FakeObserver()
        self._saved = server.observer
        server.observer = ObserverPort(url=self.fake.url, timeout=0.5, session="test:1")

    def tearDown(self):
        server.observer = self._saved
        self.fake.close()

    @patch.object(server.remote_session, "execute_command", return_value=(0, "ok\n", ""))
    def test_unplugged_is_a_no_op(self, mock_exec):
        server.observer = ObserverPort(url="")
        res = server.remote_control(action="run_command", command="ls ~/Desktop")
        self.assertEqual(res, "Exit Status: 0\n\n--- STDOUT ---\nok\n")
        self.assertEqual(self.fake.calls, [])

    @patch.object(server.remote_session, "execute_command", return_value=(0, "ok\n", ""))
    def test_before_and_after_carry_the_call(self, mock_exec):
        server.remote_control(action="run_command", command="ls ~/Desktop", stage="sim", why="find the deck")
        (p1, before), (p2, after) = self.fake.calls
        self.assertEqual((p1, p2), ("/v1/before", "/v1/after"))
        self.assertEqual(before["call_id"], after["call_id"])
        self.assertEqual((before["tool"], before["action"], before["stage"], before["why"]),
                         ("remote_control", "run_command", "sim", "find the deck"))
        self.assertEqual(before["args"]["command"], "ls ~/Desktop")
        self.assertEqual(before["session"], "test:1")
        self.assertIn("Exit Status: 0", after["result_head"])
        self.assertIn("duration_s", after)

    @patch.object(server.remote_session, "execute_command", return_value=(0, "ok\n", ""))
    def test_notices_are_appended_once(self, mock_exec):
        self.fake.before_resp = {"decision": "allow", "notices": [{"severity": "warn", "text": "probe once, then ask"}]}
        self.fake.after_resp = {"notices": [{"severity": "warn", "text": "probe once, then ask"},
                                            {"severity": "hint", "text": "deck lives in ~/Desktop/eldo"}]}
        res = server.remote_control(action="run_command", command="find ~ -name x")
        self.assertTrue(res.startswith("Exit Status: 0"))
        self.assertIn(NOTICE_HEADER, res)
        self.assertEqual(res.count("probe once, then ask"), 1)
        self.assertIn("- (hint) deck lives in ~/Desktop/eldo", res)

    @patch.object(server.virtuoso_client, "assisted_run", return_value="RESULT: t")
    def test_block_skips_the_tool(self, mock_run):
        self.fake.before_resp = {"decision": "block", "message": "'!' hangs the SKILL channel; use null(x)."}
        res = server.virtuoso(action="assisted_run", command="when(!x 1)")
        mock_run.assert_not_called()
        self.assertIn("Blocked by the observer", res)
        self.assertIn("use null(x)", res)
        self.assertEqual([p for p, _ in self.fake.calls], ["/v1/before"])

    @patch.object(server.remote_session, "execute_command", return_value=(0, "ok\n", ""))
    def test_unreachable_observer_fails_open(self, mock_exec):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            dead = sock.getsockname()[1]
        server.observer = ObserverPort(url=f"http://127.0.0.1:{dead}", timeout=0.5)
        res = server.remote_control(action="run_command", command="ls")
        self.assertEqual(res, "Exit Status: 0\n\n--- STDOUT ---\nok\n")

    @patch.object(server.remote_session, "execute_command", return_value=(0, "ok\n", ""))
    def test_slow_observer_is_cut_off(self, mock_exec):
        self.fake.delay = 1.0
        self.fake.before_resp = {"decision": "block", "message": "too late to matter"}
        server.observer = ObserverPort(url=self.fake.url, timeout=0.2)
        start = time.time()
        res = server.remote_control(action="run_command", command="ls")
        self.assertLess(time.time() - start, 1.0)
        self.assertNotIn("Blocked", res)
        mock_exec.assert_called_once()

    def test_async_workboard_is_observed(self):
        async def fake_workboard(*args):
            return "Local Root: /tmp/x"
        self.fake.after_resp = {"notices": [{"severity": "hint", "text": "one workboard call per batch"}]}
        with patch.object(server, "_workboard", fake_workboard):
            res = asyncio.run(server.workboard(action="status", stage="other", why="check board"))
        self.assertTrue(res.startswith("Local Root: /tmp/x"))
        self.assertIn("one workboard call per batch", res)
        self.assertEqual(self.fake.calls[0][1]["tool"], "workboard")

    def test_tool_schemas_offer_stage_and_why(self):
        tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
        for name in ("virtuoso", "eldo", "remote_control", "workboard"):
            props = tools[name].inputSchema["properties"]
            self.assertIn("stage", props, name)
            self.assertIn("why", props, name)
            self.assertNotIn("stage", tools[name].inputSchema.get("required", []), name)
            self.assertIn("harness_notice", tools[name].description, name)

    @patch.object(server.remote_session, "execute_command", return_value=(0, "ok\n", ""))
    def test_daemon_requests_carry_the_parent_call(self, mock_exec):
        from fastapi.testclient import TestClient
        import daemon
        client = TestClient(daemon.app)
        client.post("/remote_control", json={"action": "run_command", "command": "ls", "parent_call_id": "abc123",
                                             "stage": "route", "why": "arsenal route"})
        client.post("/remote_control", json={"action": "run_command", "command": "ls"})
        before, after, plain = (b for _, b in self.fake.calls[:2] + self.fake.calls[2:3])
        self.assertEqual((before["parent_call_id"], after["parent_call_id"]), ("abc123", "abc123"))
        self.assertEqual((before["stage"], before["why"]), ("route", "arsenal route"))
        self.assertNotIn("parent_call_id", plain)

    def test_daemon_workboard_carries_the_parent_call(self):
        from fastapi.testclient import TestClient
        import daemon

        async def fake_workboard(*args):
            return "Local Root: /tmp/x"
        with patch.object(server, "_workboard", fake_workboard):
            TestClient(daemon.app).post("/workboard", json={"action": "status", "parent_call_id": "wb1"})
        self.assertEqual([b["parent_call_id"] for _, b in self.fake.calls], ["wb1", "wb1"])



class TestHoldForVerdict(unittest.TestCase):
    """A held call waits for the verifier's verdict; only that wait fails closed."""
    def setUp(self):
        self.fake = FakeObserver()
        self.fake.before_resp = HOLD
        self._saved = server.observer
        server.observer = ObserverPort(url=self.fake.url, timeout=0.5, session="test:1")

    def tearDown(self):
        server.observer = self._saved
        self.fake.close()

    @patch.object(server.virtuoso_client, "assisted_run", return_value="RESULT: t")
    def test_before_says_it_understands_hold(self, mock_run):
        self.fake.before_resp = {"decision": "allow"}
        server.virtuoso(action="assisted_run", command="1")
        self.assertEqual(self.fake.calls[0][1]["caps"], ["hold"])
        self.assertNotIn("caps", self.fake.calls[1][1])

    @patch.object(server.virtuoso_client, "assisted_run", return_value="RESULT: t")
    def test_hold_then_allow_runs_the_tool(self, mock_run):
        self.fake.verdict_resp = {"decision": "allow", "notices": [{"severity": "hint", "text": "Verifier allowed this call."}]}
        res = server.virtuoso(action="assisted_run", command="ddDeleteObj(x)")
        mock_run.assert_called_once()
        self.assertTrue(res.startswith("RESULT: t"))
        self.assertTrue(res.endswith(f"{NOTICE_HEADER}\n- (warn) risky call\n- (hint) Verifier allowed this call."))
        (p1, before), (p2, verdict), (p3, after) = self.fake.calls
        self.assertEqual((p1, p2, p3), ("/v1/before", "/v1/verdict", "/v1/after"))
        self.assertEqual(verdict, {"v": 1, "call_id": before["call_id"], "wait_s": 2.0})

    @patch.object(server.virtuoso_client, "assisted_run", return_value="RESULT: t")
    def test_hold_then_block_does_not_run_it(self, mock_run):
        self.fake.verdict_resp = {"decision": "block", "message": "Verifier stopped this call: golden cell"}
        res = server.virtuoso(action="assisted_run", command="ddDeleteObj(x)")
        mock_run.assert_not_called()
        self.assertTrue(res.startswith("Error: Blocked by the observer, the command was NOT executed."))
        self.assertIn("golden cell", res)
        self.assertEqual([p for p, _ in self.fake.calls], ["/v1/before", "/v1/verdict"])

    @patch.object(server.virtuoso_client, "assisted_run", return_value="RESULT: t")
    def test_no_usable_verdict_blocks(self, mock_run):
        cases = {"non-json": ("verdict_raw", b"not json"), "not-an-object": ("verdict_raw", b"[]"),
                 "unknown-decision": ("verdict_resp", {"decision": "maybe"}), "dropped": ("verdict_drop", True)}
        for name, (attr, value) in cases.items():
            with self.subTest(name):
                self.fake.verdict_raw, self.fake.verdict_resp, self.fake.verdict_drop = None, {"decision": "allow"}, False
                setattr(self.fake, attr, value)
                res = server.virtuoso(action="assisted_run", command="ddDeleteObj(x)")
                self.assertIn(VERDICT_UNAVAILABLE, res)
        mock_run.assert_not_called()

    @patch.object(server.virtuoso_client, "assisted_run", return_value="RESULT: t")
    def test_verdict_timeout_follows_hold_s(self, mock_run):
        self.fake.before_resp = dict(HOLD, hold_s=0.6)
        with patch.object(observer_mod, "VERDICT_MARGIN_S", 0.1):
            self.fake.verdict_delay = 0.55       # longer than the 0.5 s hook timeout, inside hold_s + margin
            server.virtuoso(action="assisted_run", command="ddDeleteObj(x)")
            mock_run.assert_called_once()
            self.fake.verdict_delay = 1.5        # past hold_s + margin: fails closed
            start = time.time()
            res = server.virtuoso(action="assisted_run", command="ddDeleteObj(x)")
        self.assertLess(time.time() - start, 1.2)
        self.assertIn(VERDICT_UNAVAILABLE, res)
        mock_run.assert_called_once()

    def test_hold_s_is_clamped(self):
        for hold_s, wait_s in ((1000, HOLD_MAX_S), (-3, 0.0), ("soon", 20.0), (None, 20.0)):
            with self.subTest(hold_s=hold_s):
                seen = []

                def request(path, payload, timeout):
                    seen.append((path, payload.get("wait_s"), timeout))
                    return dict(HOLD, hold_s=hold_s) if path == "/v1/before" else {"decision": "block", "message": "no"}
                with patch.object(server.observer, "_request", request):
                    server.observer.before("virtuoso", "assisted_run", {"command": "x"})
                self.assertEqual(seen, [("/v1/before", None, 0.5), ("/v1/verdict", wait_s, wait_s + 5.0)])


if __name__ == "__main__":
    unittest.main()
