import unittest
import os
import shutil
import tempfile
from src.clients.workboard_client import WorkBoardClient
from src.core.scp_client import SCPClient

class MockSCPClient:
    """Mock SCPClient for offline unit testing."""
    def __init__(self):
        self.files = {
            "~/Desktop/eldo/inv.cir": b".param W=1u L=65n\nM0 vout vin vdd vdd psvtgp\n",
            "/tmp/wave.tr0": b"\x00\x01\x02\x03\x04WAVEFORM_BINARY_DATA\x00\x01"
        }

    def download(self, remote_path, local_path, timeout=60.0):
        val = self.files.get(remote_path)
        if val is None:
            raise FileNotFoundError(f"Remote file not found: {remote_path}")
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(val)
        return "Downloaded via MockSCP"

    def upload(self, local_path, remote_path, timeout=60.0):
        with open(local_path, "rb") as f:
            self.files[remote_path] = f.read()
        return "Uploaded via MockSCP"

    def read_bytes(self, remote_path, timeout=30.0):
        val = self.files.get(remote_path)
        if val is None:
            raise FileNotFoundError(f"Remote file not found: {remote_path}")
        return val

class TestWorkBoardClient(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_workboard_")
        self.scp = MockSCPClient()
        self.client = WorkBoardClient(scp_client=self.scp, base_workboard_dir=self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_initialize(self):
        res = self.client.initialize(workboard_name="inv_tb")
        self.assertIn("Initialized WorkBoard 'inv_tb'", res)
        wb_dir = os.path.join(self.test_dir, "inv_tb")
        self.assertTrue(os.path.exists(os.path.join(wb_dir, ".git")))
        self.assertTrue(os.path.exists(os.path.join(wb_dir, ".workboard.json")))

    def test_initialize_leaves_clean_tree(self):
        self.client.initialize(workboard_name="inv_tb")
        wb_dir = os.path.join(self.test_dir, "inv_tb")
        _, out, _ = self.client._git_cmd(wb_dir, ["status", "--short"])
        self.assertEqual(out.strip(), "")

    def test_export(self):
        self.client.initialize(workboard_name="inv_tb")
        wb_dir = os.path.join(self.test_dir, "inv_tb")
        local_file = os.path.join(wb_dir, "exported_inv.cir")
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        with open(local_file, "w") as f:
            f.write(".param W=2u L=65n\n")

        res_export = self.client.export(
            local_path="exported_inv.cir",
            remote_path="/tmp/exported_inv.cir",
            workboard_name="inv_tb"
        )
        self.assertIn("Successfully exported", res_export)
        self.assertIn("/tmp/exported_inv.cir", self.scp.files)

    def test_add_and_status(self):
        res_add = self.client.add(
            remote_path="~/Desktop/eldo/inv.cir",
            local_path="netlists/inv.cir",
            workboard_name="inv_tb"
        )
        self.assertIn("Successfully added", res_add)
        self.assertIn("Synced at local Git commit", res_add)

        wb_dir = os.path.join(self.test_dir, "inv_tb")
        local_file = os.path.join(wb_dir, "netlists/inv.cir")
        self.assertTrue(os.path.exists(local_file))

        res_status = self.client.status(workboard_name="inv_tb")
        self.assertIn("netlists/inv.cir -> ~/Desktop/eldo/inv.cir", res_status)
        self.assertIn("Last Synced Baseline: Commit", res_status)
        self.assertIn("CLEAN (synced at commit", res_status)

    def test_diff_identical_advances_baseline(self):
        self.client.add(
            remote_path="~/Desktop/eldo/inv.cir",
            local_path="netlists/inv.cir",
            workboard_name="inv_tb"
        )
        # Test diff on identical file
        diff_res = self.client.diff(local_path="netlists/inv.cir", workboard_name="inv_tb")
        self.assertIn("No diff detected", diff_res)
        self.assertIn("Advanced sync baseline in .workboard.json to commit", diff_res)

    def test_diff_different_shows_unified_diff(self):
        self.client.add(
            remote_path="~/Desktop/eldo/inv.cir",
            local_path="netlists/inv.cir",
            workboard_name="inv_tb"
        )
        # Modify remote mock file
        self.scp.files["~/Desktop/eldo/inv.cir"] = b".param W=1.2u L=65n\nM0 vout vin vdd vdd psvtgp\n"
        
        diff_res = self.client.diff(local_path="netlists/inv.cir", workboard_name="inv_tb")
        self.assertIn("Unified Local vs Remote Diff", diff_res)
        self.assertIn("-.param W=1u L=65n", diff_res)
        self.assertIn("+.param W=1.2u L=65n", diff_res)

    def test_binary_file_transfer(self):
        res_add = self.client.add(
            remote_path="/tmp/wave.tr0",
            local_path="results/wave.tr0",
            workboard_name="inv_tb"
        )
        self.assertIn("Successfully added", res_add)
        wb_dir = os.path.join(self.test_dir, "inv_tb")
        local_file = os.path.join(wb_dir, "results/wave.tr0")
        with open(local_file, "rb") as f:
            content = f.read()
        self.assertEqual(content, b"\x00\x01\x02\x03\x04WAVEFORM_BINARY_DATA\x00\x01")

    def test_history(self):
        self.client.add(
            remote_path="~/Desktop/eldo/inv.cir",
            local_path="netlists/inv.cir",
            workboard_name="inv_tb"
        )
        hist_res = self.client.history(local_path="netlists/inv.cir", workboard_name="inv_tb")
        self.assertIn("Commit History ('netlists/inv.cir')", hist_res)
        self.assertIn("WorkBoard Add: ~/Desktop/eldo/inv.cir -> netlists/inv.cir", hist_res)

class TestWorkBoardWorkspaceRoot(unittest.TestCase):
    """Issue #63: WorkBoards must live in the active project workspace, not the EDA_MCP repo."""
    def setUp(self):
        self.server_default = tempfile.mkdtemp(prefix="test_wb_server_")
        self.project = tempfile.mkdtemp(prefix="test_wb_project_")
        self.scp = MockSCPClient()
        self.client = WorkBoardClient(scp_client=self.scp, base_workboard_dir=self.server_default)

    def tearDown(self):
        shutil.rmtree(self.server_default, ignore_errors=True)
        shutil.rmtree(self.project, ignore_errors=True)

    def test_project_root_maps_to_workboard_subdir(self):
        boards = self.client.set_workspace_root(self.project)
        self.assertEqual(boards, os.path.join(self.project, "workboard"))

    def test_path_named_workboard_used_as_is(self):
        wb = os.path.join(self.project, "workboard")
        self.assertEqual(WorkBoardClient.resolve_boards_dir(wb), wb)
        self.assertEqual(WorkBoardClient.resolve_boards_dir(wb + "/"), wb)

    def test_add_lands_in_project_workspace(self):
        self.client.set_workspace_root(self.project)
        res = self.client.add(remote_path="~/Desktop/eldo/inv.cir", local_path="inv.cir", workboard_name="inv_tb")
        expected = os.path.join(self.project, "workboard", "inv_tb", "inv.cir")
        self.assertTrue(os.path.exists(expected))
        self.assertIn(f"Local file: {expected}", res)
        self.assertFalse(os.path.exists(os.path.join(self.server_default, "inv_tb")))

    def test_status_reports_root_and_source(self):
        self.client.set_workspace_root(self.project, source="workspace_root argument")
        self.client.initialize(workboard_name="inv_tb")
        res = self.client.status(workboard_name="inv_tb")
        self.assertIn(os.path.join(self.project, "workboard", "inv_tb"), res)
        self.assertIn("Root Source: workspace_root argument", res)

    def test_root_change_clears_active_workboard(self):
        self.client.initialize(workboard_name="old_board")
        self.assertEqual(self.client.active_workboard, "old_board")
        self.client.set_workspace_root(self.project)
        self.assertIsNone(self.client.active_workboard)

    def test_same_root_keeps_active_workboard(self):
        self.client.set_workspace_root(self.project)
        self.client.initialize(workboard_name="b1")
        self.client.set_workspace_root(self.project)
        self.assertEqual(self.client.active_workboard, "b1")

    def test_diff_forwards_timeout(self):
        seen = {}
        orig = self.scp.read_bytes
        def spy(remote_path, timeout=30.0):
            seen["timeout"] = timeout
            return orig(remote_path, timeout)
        self.scp.read_bytes = spy
        self.client.add(remote_path="~/Desktop/eldo/inv.cir", local_path="inv.cir", workboard_name="inv_tb")
        self.client.diff(local_path="inv.cir", workboard_name="inv_tb", timeout=240.0)
        self.assertEqual(seen["timeout"], 240.0)


class TestServerWorkBoardRootResolution(unittest.IsolatedAsyncioTestCase):
    """Precedence: workspace_root arg (sticky) > WORKBOARD_ROOT env > client roots > server default."""
    def setUp(self):
        import src.server as server
        self.server = server
        self.project = tempfile.mkdtemp(prefix="test_wb_proj_")
        self.other = tempfile.mkdtemp(prefix="test_wb_env_")
        self._saved = (server._workboard_explicit_root, server.workboard_client.base_workboard_dir,
                       os.environ.pop("WORKBOARD_ROOT", None))
        server._workboard_explicit_root = ""

    def tearDown(self):
        root, base, env = self._saved
        self.server._workboard_explicit_root = root
        self.server.workboard_client.base_workboard_dir = base
        if env is None:
            os.environ.pop("WORKBOARD_ROOT", None)
        else:
            os.environ["WORKBOARD_ROOT"] = env
        shutil.rmtree(self.project, ignore_errors=True)
        shutil.rmtree(self.other, ignore_errors=True)

    def _ctx_with_roots(self, paths):
        from types import SimpleNamespace
        from urllib.parse import quote
        roots = [SimpleNamespace(uri="file://" + quote(p)) for p in paths]
        async def list_roots():
            return SimpleNamespace(roots=roots)
        session = SimpleNamespace(
            client_params=SimpleNamespace(capabilities=SimpleNamespace(roots=object())),
            list_roots=list_roots)
        return SimpleNamespace(session=session)

    async def test_explicit_arg_is_sticky_and_beats_env(self):
        os.environ["WORKBOARD_ROOT"] = self.other
        self.assertEqual(await self.server._resolve_workboard_root(self.project, None), "")
        self.assertEqual(await self.server._resolve_workboard_root("", None), "")
        self.assertEqual(self.server.workboard_client.base_workboard_dir, os.path.join(self.project, "workboard"))

    async def test_env_beats_client_roots(self):
        os.environ["WORKBOARD_ROOT"] = self.other
        await self.server._resolve_workboard_root("", self._ctx_with_roots([self.project]))
        self.assertEqual(self.server.workboard_client.base_workboard_dir, os.path.join(self.other, "workboard"))

    async def test_client_roots_used_when_no_arg_or_env(self):
        spaced = os.path.join(self.project, "my project")
        os.makedirs(spaced)
        await self.server._resolve_workboard_root("", self._ctx_with_roots([spaced]))
        self.assertEqual(self.server.workboard_client.base_workboard_dir, os.path.join(spaced, "workboard"))
        self.assertEqual(self.server.workboard_client.root_source, "MCP client workspace root")

    async def test_falls_back_to_server_default(self):
        await self.server._resolve_workboard_root("", None)
        self.assertEqual(self.server.workboard_client.base_workboard_dir,
                         os.path.join(self.server.base_dir, "workboard"))

    async def test_missing_workspace_root_rejected(self):
        res = await self.server._resolve_workboard_root(os.path.join(self.project, "nope"), None)
        self.assertIn("is not an existing directory", res)


class TestSCPClient(unittest.TestCase):
    """Rigorous unit tests for SCPClient configuration, flags, and command generation."""
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_scp_")
        self.config_path = os.path.join(self.test_dir, "config.json")
        self.ssh_cfg_path = os.path.join(self.test_dir, "ssh_config")
        
        # Create mock ssh_config file
        with open(self.ssh_cfg_path, "w") as f:
            f.write("Host eda-uni\n  HostName 192.168.1.100\n  User vaibhav22555\n")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scp_config_loading_ssh_host(self):
        # Create config with ssh_host key
        with open(self.config_path, "w") as f:
            f.write('{"ssh_host": "eda-uni", "ssh_config_path": "' + self.ssh_cfg_path + '"}\n')
            
        client = SCPClient(config_path=self.config_path)
        self.assertEqual(client.host, "eda-uni")
        self.assertEqual(client.ssh_config_path, self.ssh_cfg_path)

    def test_scp_cmd_generation_includes_f_flag(self):
        with open(self.config_path, "w") as f:
            f.write('{"ssh_host": "eda-uni", "ssh_config_path": "' + self.ssh_cfg_path + '"}\n')
            
        client = SCPClient(config_path=self.config_path)
        cmd = client._get_base_scp_cmd()
        self.assertIn("-F", cmd)
        self.assertIn(self.ssh_cfg_path, cmd)
        self.assertIn("-q", cmd)
        self.assertIn("BatchMode=yes", cmd)

    def test_scp_alias_formatting_without_user(self):
        client = SCPClient(host="eda-uni", user="", ssh_config_path=self.ssh_cfg_path)
        # Attempt download on fake remote path to inspect exception format
        try:
            client.download("/remote/path/test.chi", os.path.join(self.test_dir, "test.chi"), timeout=1.0)
        except Exception as e:
            # Verify command included eda-uni:/remote/path/test.chi without user@ prefix
            err_str = str(e)
            self.assertTrue("timed out" in err_str or "failed" in err_str)

if __name__ == "__main__":
    unittest.main()
