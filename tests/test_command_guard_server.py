import os
import shutil
import tempfile
import unittest
from unittest.mock import patch
import src.server as server
from src.core.command_guard import CommandGuard


class TestServerCommandGuard(unittest.TestCase):
    """Issue #55: the guard runs in the MCP tools before anything reaches the SSH session."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="test_guard_srv_")
        self.audit = os.path.join(self.tmp, "audit.jsonl")
        self._saved = server.command_guard
        server.command_guard = CommandGuard(audit_log_path=self.audit)

    def tearDown(self):
        server.command_guard = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _audit_decisions(self):
        if not os.path.exists(self.audit):
            return []
        import json
        with open(self.audit) as f:
            return [json.loads(line)["decision"] + ("/dry" if json.loads(line)["dry_run"] else "") for line in f]

    @patch.object(server.remote_session, "execute_command")
    def test_blocked_command_never_executes(self, mock_exec):
        res = server.remote_control(action="run_command", command="rm -rf ~/Desktop/cmos65")
        self.assertIn("Error: Blocked", res)
        self.assertIn("NOT executed", res)
        mock_exec.assert_not_called()
        self.assertEqual(self._audit_decisions(), ["blocked"])

    @patch.object(server.remote_session, "execute_command", return_value=(0, "ok\n", ""))
    def test_allowed_command_executes(self, mock_exec):
        res = server.remote_control(action="run_command", command="ls -la ~/Desktop")
        self.assertIn("Exit Status: 0", res)
        mock_exec.assert_called_once()
        self.assertEqual(self._audit_decisions(), ["allowed"])

    @patch.object(server.remote_session, "execute_command")
    def test_dry_run_does_not_execute(self, mock_exec):
        res = server.remote_control(action="run_command", command="rm -rf /tmp/scratch", dry_run=True)
        self.assertIn("[DRY RUN]", res)
        self.assertIn("would run", res)
        mock_exec.assert_not_called()
        res = server.remote_control(action="run_command", command="rm -rf ~", dry_run=True)
        self.assertIn("Error: Blocked", res)
        self.assertEqual(self._audit_decisions(), ["allowed/dry", "blocked/dry"])

    @patch.object(server.remote_session, "write_file")
    def test_write_file_outside_allowed_dirs_blocked(self, mock_write):
        res = server.remote_control(action="write_file", path="~/.cshrc", content="x")
        self.assertIn("Error: Blocked", res)
        mock_write.assert_not_called()

    @patch.object(server.remote_session, "write_file", return_value="")
    def test_write_file_inside_allowed_dirs(self, mock_write):
        res = server.remote_control(action="write_file", path="~/Desktop/eldo/tb.cir", content="* t\n.end\n")
        self.assertIn("Successfully wrote", res)
        mock_write.assert_called_once()

    @patch.object(server.eldo_client, "run_terminal_command", return_value="ran")
    def test_eldo_terminal_uses_work_dir_for_relative_paths(self, mock_run):
        self.assertEqual(server.eldo(action="run_terminal_command", command="eldo tb.cir > tb.log"), "ran")
        res = server.eldo(action="run_terminal_command", command="rm -rf ../../", work_dir="~/Desktop/eldo")
        self.assertIn("Error: Blocked", res)
        mock_run.assert_called_once()

    @patch.object(server.virtuoso_client, "run_terminal_command", return_value="ran")
    def test_virtuoso_terminal_guarded(self, mock_run):
        res = server.virtuoso(action="run_terminal_command", command="rm -rf ~")
        self.assertIn("Error: Blocked", res)
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
