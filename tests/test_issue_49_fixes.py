import os
import sys
import unittest
from unittest.mock import MagicMock, patch

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from workboard_client import WorkBoardClient
from virtuoso_client import VirtuosoClient
from eldo_client import EldoClient
from ssh_client import RemoteSession

class TestIssue49Fixes(unittest.TestCase):
    def test_workboard_status_multiple_workboards(self):
        mock_scp = MagicMock()
        client = WorkBoardClient(scp_client=mock_scp, base_workboard_dir=os.path.join(base_dir, "workboard"))
        # Run status with empty workboard_name when multiple exist
        res = client.status(workboard_name="")
        self.assertIn("Multiple WorkBoards exist", res)
        self.assertIn("sram_sim", res)
        self.assertIn("inv_sim", res)

    def test_virtuoso_terminal_command_uses_bash(self):
        mock_session = MagicMock(spec=RemoteSession)
        mock_session.execute_command.return_value = (0, "output", "")
        client = VirtuosoClient(session=mock_session)
        client.run_terminal_command("echo hello 2>/dev/null", use_bash=True)
        
        # Verify execute_command was called with bash -c wrapper
        mock_session.execute_command.assert_called_with("bash -c 'echo hello 2>/dev/null'", timeout=60.0)

    def test_eldo_terminal_command_uses_bash(self):
        mock_session = MagicMock(spec=RemoteSession)
        mock_session.execute_command.return_value = (0, "output", "")
        client = EldoClient(session=mock_session)
        client.run_terminal_command("echo hello 2>/dev/null", use_bash=True)
        
        # Verify execute_command was called with bash -c wrapper
        mock_session.execute_command.assert_called_with("bash -c 'echo hello 2>/dev/null'", timeout=60.0)

if __name__ == "__main__":
    unittest.main()
