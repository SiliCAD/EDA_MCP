import inspect
import unittest
from unittest.mock import MagicMock, patch

from src import server
from src.clients.virtuoso_client import VirtuosoClient, DEFAULT_WORK_DIR


class TestVirtuosoWorkDir(unittest.TestCase):
    """Issue #76: the virtuoso tool has no work_dir argument; it always runs in the default session directory."""

    def test_tool_has_no_work_dir_argument(self):
        self.assertNotIn("work_dir", inspect.signature(server.virtuoso).parameters)

    @patch.object(server.virtuoso_client, "assisted_run", return_value="RESULT: 5")
    def test_assisted_run_uses_default_dir(self, mock_run):
        self.assertEqual(server.virtuoso(action="assisted_run", command="plus(2 3)"), "RESULT: 5")
        mock_run.assert_called_once_with(skill_code="plus(2 3)", work_dir=DEFAULT_WORK_DIR, timeout=30.0)

    @patch.object(server.virtuoso_client, "run_terminal_command", return_value="ok")
    def test_terminal_command_uses_default_dir(self, mock_run):
        server.virtuoso(action="run_terminal_command", command="ls")
        mock_run.assert_called_once_with(command="ls", work_dir=DEFAULT_WORK_DIR, timeout=30.0)

    def test_terminal_command_refuses_when_cd_fails(self):
        s = MagicMock()
        s.execute_command.side_effect = lambda cmd, timeout=60.0: (1, "", "") if cmd.startswith("cd ") else (0, "ok", "")
        res = VirtuosoClient(session=s).run_terminal_command("ls", work_dir="~/Desktop/missing")
        self.assertIn("NOT run", res)
        self.assertFalse(any(call.args[0].startswith("bash -c") for call in s.execute_command.call_args_list))


if __name__ == "__main__":
    unittest.main()
