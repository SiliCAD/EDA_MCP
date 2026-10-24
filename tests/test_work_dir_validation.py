import unittest
from unittest.mock import MagicMock

from src.clients.virtuoso_client import VirtuosoClient


def session(fifo_dirs=("$HOME/Desktop/cmos65",), existing_dirs=("$HOME/Desktop/cmos65", "$HOME/Desktop/eldo")):
    """Fake persistent shell: `test -p <dir>/MCP.command` and `cd <dir>` succeed only for the given dirs."""
    s = MagicMock()
    s.connect.return_value = None
    s.read_file.return_value = "RESULT: 5"

    def execute(cmd, timeout=60.0):
        if cmd.startswith("test -p "):
            d = cmd[len("test -p "):].rsplit("/MCP.command", 1)[0]
            return (0 if d in fifo_dirs else 1), "", ""
        if cmd.startswith("cd "):
            return (0 if cmd[3:] in existing_dirs else 1), "", ""
        return 0, "ok", ""
    s.execute_command.side_effect = execute
    return s


class TestWorkDirValidation(unittest.TestCase):
    """Issue #76: a wrong work_dir is rejected with a clear error instead of hanging every later call."""

    def test_default_work_dir_initializes(self):
        c = VirtuosoClient(session=session())
        self.assertEqual(c.assisted_run("plus(2 3)", work_dir="~/Desktop/cmos65"), "RESULT: 5")
        self.assertEqual(c.workdir, "~/Desktop/cmos65")

    def test_dir_without_fifo_is_rejected_and_not_sticky(self):
        s = session(existing_dirs=("$HOME/Desktop/cmos65", "/home/u/CDS"))
        c = VirtuosoClient(session=s)
        res = c.assisted_run("plus(2 3)", work_dir="/home/u/CDS")
        self.assertIn("work_dir '/home/u/CDS' has no Virtuoso session", res)
        self.assertIn("Nothing was sent", res)
        self.assertIsNone(c.workdir)
        self.assertFalse(any("MCP.command" in call.args[0] and call.args[0].startswith("printf")
                             for call in s.execute_command.call_args_list))
        # the next call with the default works: the bad directory didn't stick
        self.assertEqual(c.assisted_run("plus(2 3)", work_dir="~/Desktop/cmos65"), "RESULT: 5")

    def test_local_path_gets_a_hint(self):
        c = VirtuosoClient(session=session())
        res = c.assisted_run("t", work_dir="/Users/someone/hqc_runs/luna/SC-005")
        self.assertIn("path on this machine, not on the EDA server", res)

    def test_validation_runs_only_at_init(self):
        s = session()
        c = VirtuosoClient(session=s)
        for _ in range(3):
            c.assisted_run("t", work_dir="~/Desktop/cmos65")
        checks = [call for call in s.execute_command.call_args_list if call.args[0].startswith("test -p")]
        self.assertEqual(len(checks), 1)

    def test_terminal_command_refuses_missing_dir(self):
        s = session()
        c = VirtuosoClient(session=s)
        res = c.run_terminal_command("ls", work_dir="/Users/someone/project")
        self.assertIn("does not exist on the EDA server", res)
        self.assertIn("NOT run", res)
        self.assertFalse(any(call.args[0].startswith("bash -c") for call in s.execute_command.call_args_list))
        self.assertIn("Exit Status: 0", c.run_terminal_command("ls", work_dir="~/Desktop/eldo"))


if __name__ == "__main__":
    unittest.main()
