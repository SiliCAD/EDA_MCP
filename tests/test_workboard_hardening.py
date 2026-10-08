import os
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
from src.clients.workboard_client import WorkBoardClient
from src.core.scp_client import SCPClient, validate_remote_path


class FakeSCP:
    """Offline SCP stand-in; 'remote' files live in a dict."""
    def __init__(self):
        self.files = {"/r/a.cir": b"v1\n"}
        self.fail_next_download = False

    def download(self, remote_path, local_path, timeout=60.0):
        if self.fail_next_download:
            self.fail_next_download = False
            with open(local_path, "wb") as f:
                f.write(b"PARTIAL")  # simulate a transfer that dies halfway
            raise TimeoutError("SCP download timed out")
        with open(local_path, "wb") as f:
            f.write(self.files[remote_path])

    def upload(self, local_path, remote_path, timeout=60.0):
        with open(local_path, "rb") as f:
            self.files[remote_path] = f.read()

    def read_bytes(self, remote_path, timeout=30.0):
        return self.files[remote_path]


class TestWorkBoardGitBaselines(unittest.TestCase):
    """Recorded last_sync_commit must be a real commit on the branch (no --amend rewrite)."""
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="test_wb_hard_")
        self.scp = FakeSCP()
        self.c = WorkBoardClient(scp_client=self.scp, base_workboard_dir=self.dir)
        self.wb = os.path.join(self.dir, "b")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _baseline(self, rel):
        with open(os.path.join(self.wb, ".workboard.json")) as f:
            return json.load(f)["files"][rel]["last_sync_commit"]

    def _on_branch(self, sha):
        ret, _, _ = self.c._git_cmd(self.wb, ["merge-base", "--is-ancestor", sha, "HEAD"])
        return ret == 0

    def _file_at(self, sha, rel):
        return self.c._git_cmd(self.wb, ["show", f"{sha}:{rel}"])[1]

    def test_add_pull_push_baselines_stay_on_branch(self):
        self.c.add(remote_path="/r/a.cir", local_path="a.cir", workboard_name="b")
        sha = self._baseline("a.cir")
        self.assertTrue(self._on_branch(sha))
        self.assertEqual(self._file_at(sha, "a.cir"), "v1\n")

        self.scp.files["/r/a.cir"] = b"v2\n"
        self.c.pull(local_path="a.cir", workboard_name="b")
        sha = self._baseline("a.cir")
        self.assertTrue(self._on_branch(sha))
        self.assertEqual(self._file_at(sha, "a.cir"), "v2\n")

        with open(os.path.join(self.wb, "a.cir"), "w") as f:
            f.write("v3\n")
        self.c.push(local_path="a.cir", workboard_name="b")
        sha = self._baseline("a.cir")
        self.assertTrue(self._on_branch(sha))
        self.assertEqual(self._file_at(sha, "a.cir"), "v3\n")

    def test_pull_with_unchanged_content_succeeds(self):
        self.c.add(remote_path="/r/a.cir", local_path="a.cir", workboard_name="b")
        res = self.c.pull(local_path="a.cir", workboard_name="b")
        self.assertIn("Successfully pulled", res)
        self.assertTrue(self._on_branch(self._baseline("a.cir")))

    def test_git_failure_is_reported_not_hidden(self):
        self.c.initialize(workboard_name="b")
        open(os.path.join(self.wb, ".git", "index.lock"), "w").close()  # simulate a concurrent git process
        res = self.c.add(remote_path="/r/a.cir", local_path="a.cir", workboard_name="b")
        self.assertIn("Failed to add", res)
        self.assertIn("git", res)
        self.assertNotIn("Successfully", res)


class TestWorkBoardAtomicDownload(unittest.TestCase):
    """A failed or timed-out pull must not truncate the existing local copy."""
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="test_wb_atomic_")
        self.scp = FakeSCP()
        self.c = WorkBoardClient(scp_client=self.scp, base_workboard_dir=self.dir)
        self.c.add(remote_path="/r/a.cir", local_path="a.cir", workboard_name="b")
        self.local = os.path.join(self.dir, "b", "a.cir")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_failed_pull_keeps_old_file_and_cleans_temp(self):
        self.scp.fail_next_download = True
        res = self.c.pull(local_path="a.cir", workboard_name="b")
        self.assertIn("Failed to pull", res)
        with open(self.local, "rb") as f:
            self.assertEqual(f.read(), b"v1\n")
        leftovers = [n for n in os.listdir(os.path.dirname(self.local)) if ".wbtmp-" in n]
        self.assertEqual(leftovers, [])

    def test_successful_pull_replaces_file(self):
        self.scp.files["/r/a.cir"] = b"v2\n"
        self.c.pull(local_path="a.cir", workboard_name="b")
        with open(self.local, "rb") as f:
            self.assertEqual(f.read(), b"v2\n")


class TestSCPHardening(unittest.TestCase):
    def test_safe_paths_accepted(self):
        for p in ["~/Desktop/eldo/tb_inv.chi", "/tmp/wb55_1/a.txt", "~/Desktop/cmos65/drc_run/drc_summary",
                  "/modelfile_65nm/typNtypP.cir", "~/x/a-b+c=d,e@f%g:h.cir"]:
            self.assertEqual(validate_remote_path(p), p)

    def test_shell_metacharacters_rejected(self):
        for p in ["/tmp/x;rm -rf ~", "~/a b.cir", "$(id)", "`id`", "/tmp/a|b", "/tmp/a&b", "/tmp/*.chi",
                  "/tmp/a'b", '/tmp/a"b', "/tmp/a\nb", "-oProxyCommand=x", ""]:
            with self.assertRaises(ValueError, msg=p):
                validate_remote_path(p)

    def test_download_and_upload_reject_before_running_scp(self):
        scp = SCPClient(config_path="/nonexistent", host="eda-uni")
        with patch("src.core.scp_client.subprocess.run") as run:
            with self.assertRaises(ValueError):
                scp.download("/tmp/x;rm -rf ~", "/tmp/local_x")
            with tempfile.NamedTemporaryFile() as tmp:
                with self.assertRaises(ValueError):
                    scp.upload(tmp.name, "/tmp/$(id)")
            run.assert_not_called()

    def test_host_key_option_and_no_control_path_override(self):
        cmd = SCPClient(config_path="/nonexistent", host="eda-uni")._get_base_scp_cmd()
        self.assertIn("StrictHostKeyChecking=accept-new", cmd)
        self.assertNotIn("StrictHostKeyChecking=no", cmd)
        # scp forces ControlMaster=no, so it must keep the user's ControlPath to reuse an existing master.
        self.assertFalse(any(o.startswith(("ControlPath=", "ControlMaster=")) for o in cmd))


if __name__ == "__main__":
    unittest.main()
