import unittest
from unittest.mock import MagicMock
from src.clients.virtuoso_client import VirtuosoClient

class TestVirtuosoAutoInit(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.mock_session.connect.return_value = None
        self.mock_session.execute_command.return_value = (0, "Success", "")
        self.mock_session.read_file.return_value = "RESULT: 5"
        self.client = VirtuosoClient(session=self.mock_session)

    def test_assisted_run_auto_initializes_when_workdir_is_none(self):
        self.assertIsNone(self.client.workdir)
        
        # Calling assisted_run without calling initialize() first
        res = self.client.assisted_run(skill_code="plus(2 3)", work_dir="~/Desktop/cmos65")
        
        # Verify self.workdir is now set to ~/Desktop/cmos65
        self.assertEqual(self.client.workdir, "~/Desktop/cmos65")
        self.assertEqual(res, "RESULT: 5")
        
        # Verify connect and cd command execution occurred
        self.mock_session.connect.assert_called()

    def test_assisted_run_uses_existing_workdir_if_already_initialized(self):
        self.client._initialize(work_dir="~/Desktop/custom_dir")
        self.assertEqual(self.client.workdir, "~/Desktop/custom_dir")
        
        res = self.client.assisted_run(skill_code="plus(3 4)")
        self.assertEqual(self.client.workdir, "~/Desktop/custom_dir")
        self.assertEqual(res, "RESULT: 5")

    def test_assisted_run_large_payload_via_scp(self):
        mock_scp = MagicMock()
        self.client.scp = mock_scp
        
        # Payload > 32KB
        large_skill = "plus(1 1) " * 5000
        res = self.client.assisted_run(skill_code=large_skill, work_dir="~/Desktop/cmos65")
        
        self.assertEqual(res, "RESULT: 5")
        mock_scp.upload.assert_called_once()
        # Ensure cat command was sent to FIFO pipe
        exec_cmds = [call[0][0] for call in self.mock_session.execute_command.call_args_list]
        self.assertTrue(any("cat /tmp/mcp_skill_" in cmd and "> MCP.command" in cmd for cmd in exec_cmds))

if __name__ == "__main__":
    unittest.main()
