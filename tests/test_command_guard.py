import os
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
from src.core.command_guard import CommandGuard


class TestCommandGuardBlocks(unittest.TestCase):
    """Issue #55: destructive or unverifiable commands must be blocked before reaching the server."""
    def setUp(self):
        self.g = CommandGuard()

    def assertBlocked(self, cmd, cwd=None, contains=""):
        ok, reason = self.g.validate(cmd, cwd=cwd)
        self.assertFalse(ok, f"expected block: {cmd!r} ({reason})")
        self.assertTrue(reason.startswith("Blocked:"))
        if contains:
            self.assertIn(contains, reason)

    def test_always_blocked_patterns(self):
        for cmd in ["mkfs.ext4 /dev/sda1", "dd if=/dev/zero of=/dev/sda", "sudo reboot", "shutdown -h now",
                    "kill -9 1", "kill -1", "chmod 777 ~/Desktop/eldo/x", ":(){ :|:& };:", "cat x > /dev/sda"]:
            self.assertBlocked(cmd)

    def test_rm_outside_allowed_dirs(self):
        self.assertBlocked("rm -rf /", contains="outside the allowed directories")
        self.assertBlocked("rm -rf ~")
        self.assertBlocked("rm -rf $HOME")
        self.assertBlocked("rm -rf /etc/passwd")
        self.assertBlocked("rm -rf ~/Desktop/cmos65/../..")

    def test_cannot_delete_workspace_roots(self):
        self.assertBlocked("rm -rf ~/Desktop/cmos65", contains="allowed root directory")
        self.assertBlocked("rm -rf ~/Desktop/cmos65/")
        self.assertBlocked("rm -rf /tmp")
        self.assertBlocked("rm -rf ~/Desktop/cmos65/*", contains="matches everything at the top level")
        self.assertBlocked("cd ~/Desktop/eldo && rm -rf *")
        self.assertBlocked("mv ~/Desktop/cmos65 /tmp/x")

    def test_redirect_and_write_targets(self):
        self.assertBlocked("echo x > ~/.cshrc", contains="Redirect")
        self.assertBlocked("echo x >> /etc/hosts")
        self.assertBlocked("echo x | tee ~/.bashrc")
        self.assertBlocked("cp /tmp/x ~/.cshrc")
        self.assertBlocked("mv ~/Desktop/cmos65/lib ~/old")

    def test_unverifiable_targets(self):
        self.assertBlocked("rm -f tb.chi", contains="relative path")
        self.assertBlocked("rm -rf $(pwd)", contains="$(...)")
        self.assertBlocked("rm -rf `pwd`")
        self.assertBlocked("rm -rf $WORK/x", contains="shell expansion")
        self.assertBlocked("ls ~ | xargs rm -rf", contains="xargs")
        self.assertBlocked("find ~/Desktop -name '*.log' -delete")

    def test_hidden_inside_wrappers(self):
        self.assertBlocked("ls\nrm -rf ~")
        self.assertBlocked("ls; rm -rf ~")
        self.assertBlocked("true && rm -rf ~")
        self.assertBlocked('bash -c "rm -rf ~"', contains="inside bash")
        self.assertBlocked("eval rm -rf ~")
        self.assertBlocked("sudo rm -rf /")
        self.assertBlocked("FOO=1 rm -rf ~")


class TestCommandGuardPeerReviewFindings(unittest.TestCase):
    """Gaps found by the verification agent during live testing (issue #55 peer review)."""
    def setUp(self):
        self.g = CommandGuard()

    def test_extension_filtered_cleanup_allowed(self):
        for cmd in ["rm -f ~/Desktop/eldo/*.chi", "cd ~/Desktop/eldo && rm -f *.chi *.raw",
                    "find ~/Desktop/cmos65 -name '*.cdslck' -delete",
                    "find ~/Desktop/cmos65 -name '*.cdslck' -exec rm -f {} +",
                    "find ~ -name '*.cir' -exec cat {} \\;"]:
            self.assertTrue(self.g.validate(cmd)[0], cmd)

    def test_match_all_still_blocked(self):
        for cmd in ["rm -rf ~/Desktop/cmos65/*", "rm -rf ~/Desktop/cmos65/.*", "rm -rf ~/Desktop/cmos65/*.*",
                    "rm -rf ~/Desktop/cmos65/[a-z]*", "find ~/Desktop/cmos65 -delete",
                    "find ~/Desktop/cmos65 -name '*' -delete", "find ~ -name '*.log' -delete"]:
            self.assertFalse(self.g.validate(cmd)[0], cmd)

    def test_other_writers_checked(self):
        self.assertFalse(self.g.validate("sed -i 's/a/b/' ~/.cshrc")[0])
        self.assertFalse(self.g.validate("sed -i.bak -e 's/a/b/' ~/.cshrc")[0])
        self.assertTrue(self.g.validate("sed -i 's/a/b/' ~/Desktop/eldo/tb.cir")[0])
        self.assertTrue(self.g.validate("sed -n 's/a/b/p' ~/.cshrc")[0])
        self.assertFalse(self.g.validate("dd if=/dev/zero of=~/.cshrc")[0])
        self.assertTrue(self.g.validate("dd if=/tmp/a of=/tmp/b")[0])

    def test_inline_interpreter_code(self):
        self.assertFalse(self.g.validate('python3 -c "import os; os.remove(\'/home/x/.cshrc\')"')[0])
        self.assertFalse(self.g.validate('python3 -c "import shutil; shutil.rmtree(\'/x\')"')[0])
        self.assertFalse(self.g.validate('perl -e "unlink glob q{~/*}"')[0])
        self.assertTrue(self.g.validate('python3 -c "print(1+1)"')[0])


class TestCommandGuardAllows(unittest.TestCase):
    """Normal EDA workflows must keep working."""
    def setUp(self):
        self.g = CommandGuard()

    def assertAllowed(self, cmd, cwd=None):
        ok, reason = self.g.validate(cmd, cwd=cwd)
        self.assertTrue(ok, f"expected allow: {cmd!r} ({reason})")

    def test_read_only_commands(self):
        for cmd in ["ls -la ~/Desktop", "cat ~/.cshrc", "grep -r foo /etc", "pwd", "which eldo",
                    "cat halt.log", "ps aux | grep virtuoso", "kill -9 12345", "echo hi 2>&1"]:
            self.assertAllowed(cmd)

    def test_destructive_inside_workspace(self):
        self.assertAllowed("rm -rf ~/Desktop/cmos65/drc_run")
        self.assertAllowed("rm -f $HOME/Desktop/eldo/tb.chi")
        self.assertAllowed("rm -rf /tmp/wb63_1234")
        self.assertAllowed("rm -rf ~/Desktop/cmos65/drc_run/*")
        self.assertAllowed("mv ~/Desktop/eldo/a.cir ~/Desktop/eldo/b.cir")
        self.assertAllowed("cp ~/.cshrc /tmp/cshrc.bak")
        self.assertAllowed("echo x > /tmp/a.txt")
        self.assertAllowed("rm -f /tmp/a.txt 2>/dev/null")
        self.assertAllowed("find /tmp/calibre_run -name '*.log' -delete")

    def test_relative_paths_with_known_cwd(self):
        self.assertAllowed("cd ~/Desktop/eldo && rm -f tb.chi")
        self.assertAllowed("eldo tb.cir > tb.log", cwd="~/Desktop/eldo")
        self.assertAllowed("rm -f tb.chi", cwd="~/Desktop/eldo")
        ok, _ = self.g.validate("rm -rf ../../x", cwd="~/Desktop/eldo")
        self.assertFalse(ok)

    def test_tools_and_background_jobs(self):
        self.assertAllowed("virtuoso -nograph &")
        self.assertAllowed("strmout -library MCP -outFile /tmp/x.gds")
        self.assertAllowed('echo "$(date)" > /tmp/d.txt')


class TestCommandGuardConfigAndAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="test_guard_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_config_file_allowed_dirs(self):
        cfg = os.path.join(self.tmp, "command_guard.json")
        with open(cfg, "w") as f:
            json.dump({"enabled": True, "allowed_dirs": ["~/work"]}, f)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EDA_MCP_GUARD_ALLOWED_DIRS", None)
            os.environ.pop("EDA_MCP_COMMAND_GUARD", None)
            g = CommandGuard.from_config(cfg)
        self.assertTrue(g.validate("rm -rf ~/work/x")[0])
        self.assertFalse(g.validate("rm -rf /tmp/x")[0])

    def test_env_overrides(self):
        with patch.dict(os.environ, {"EDA_MCP_GUARD_ALLOWED_DIRS": "/scratch:~/proj", "EDA_MCP_COMMAND_GUARD": ""}):
            g = CommandGuard.from_config()
        self.assertEqual(g.allowed_dirs, ["/scratch", "~/proj"])
        with patch.dict(os.environ, {"EDA_MCP_COMMAND_GUARD": "off"}):
            g = CommandGuard.from_config()
        self.assertTrue(g.validate("rm -rf ~")[0])

    def test_write_path_check(self):
        g = CommandGuard()
        self.assertTrue(g.check_write_path("~/Desktop/eldo/tb.cir")[0])
        self.assertFalse(g.check_write_path("~/.cshrc")[0])
        self.assertFalse(g.check_write_path("tb.cir")[0])

    def test_audit_log_lines(self):
        log = os.path.join(self.tmp, "audit.jsonl")
        g = CommandGuard(audit_log_path=log)
        g.audit("remote_control", "rm -rf ~", False, "Blocked: x")
        g.audit("remote_control", "ls", True, "Allowed", dry_run=True)
        with open(log) as f:
            rows = [json.loads(line) for line in f]
        self.assertEqual([(r["decision"], r["dry_run"]) for r in rows], [("blocked", False), ("allowed", True)])
        self.assertEqual(rows[0]["command"], "rm -rf ~")


if __name__ == "__main__":
    unittest.main()
