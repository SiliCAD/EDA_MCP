import unittest
from unittest.mock import MagicMock, patch

import src.server as server
from src.clients.virtuoso_client import VirtuosoClient
from src.core.command_guard import CommandGuard, history_bang


class TestHistoryBang(unittest.TestCase):
    """#69: '!word' hangs the server shell (tcsh history expansion), so it is refused before sending."""

    def test_detection(self):
        for bad in ("when(!x 1)", "grep -v '!foo' f", "echo hi!there", "!pcreMatchp(\"^C\" n)"):
            self.assertTrue(history_bang(bad), bad)
        for ok in ("x != 1", "[ ! -f a ] && echo y", "when(!(a && b) 1)", "echo done!", "plain"):
            self.assertEqual(history_bang(ok), "", ok)

    def test_guard_blocks_even_when_disabled(self):
        ok, reason = CommandGuard(enabled=False).validate("ls !foo")
        self.assertFalse(ok)
        self.assertIn("history expansion", reason)
        msg = CommandGuard().blocked_message(reason)
        self.assertIn("NOT executed", msg)
        self.assertNotIn("Destructive", msg)

    @patch.object(server.remote_session, "execute_command")
    def test_remote_control_never_sends_it(self, mock_exec):
        res = server.remote_control(action="run_command", command="find . ! -name x -o -name !y")
        self.assertIn("'!y'", res)
        mock_exec.assert_not_called()

    def test_assisted_run_never_sends_it(self):
        s = MagicMock()
        c = VirtuosoClient(session=s)
        res = c.assisted_run('setof(i cv~>instances !pcreMatchp("^CDEC" i~>name))')
        self.assertIn("NOT sent to Virtuoso", res)
        self.assertIn("null(x)", res)
        s.execute_command.assert_not_called()
        s.connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
