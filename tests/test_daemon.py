import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from daemon import app
from src.clients.eda_client import EDADaemonClient

class TestDaemon(unittest.TestCase):
    def setUp(self):
        self.test_client = TestClient(app)

    def test_health_check(self):
        resp = self.test_client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "eda_mcp_daemon")

    @patch("daemon.virtuoso")
    def test_virtuoso_endpoint(self, mock_virtuoso):
        mock_virtuoso.return_value = "RESULT: 100"
        resp = self.test_client.post("/virtuoso", json={"action": "assisted_run", "command": "plus(50 50)"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"result": "RESULT: 100"})
        mock_virtuoso.assert_called_once_with(
            action="assisted_run",
            command="plus(50 50)",
            work_dir="~/Desktop/cmos65",
            timeout=60.0
        )

    @patch("daemon.eldo")
    def test_eldo_endpoint(self, mock_eldo):
        mock_eldo.return_value = "Simulation completed successfully"
        resp = self.test_client.post("/eldo", json={"action": "run_terminal_command", "command": "eldo -i tb.cir"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"result": "Simulation completed successfully"})
        mock_eldo.assert_called_once()

    @patch("daemon.workboard")
    def test_workboard_endpoint(self, mock_workboard):
        mock_workboard.return_value = "WorkBoard status ok"
        resp = self.test_client.post("/workboard", json={"action": "status", "workboard_name": "default"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"result": "WorkBoard status ok"})
        mock_workboard.assert_called_once()

    @patch("daemon.remote_control")
    def test_remote_control_endpoint(self, mock_remote):
        mock_remote.return_value = "Linux stdout"
        resp = self.test_client.post("/remote_control", json={"action": "run_command", "command": "uname -a"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"result": "Linux stdout"})
        mock_remote.assert_called_once()

if __name__ == "__main__":
    unittest.main()
