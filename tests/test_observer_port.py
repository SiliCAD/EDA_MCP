import asyncio
import json
import socket
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import src.server as server
from src.core.observer import ObserverPort, NOTICE_HEADER


class FakeObserver:
    """Records every hook call and answers with canned responses."""
    def __init__(self):
        self.calls = []
        self.before_resp = {"decision": "allow"}
        self.after_resp = {"notices": []}
        self.delay = 0.0
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.calls.append((self.path, body))
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
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

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


if __name__ == "__main__":
    unittest.main()
