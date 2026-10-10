import unittest
import os
import shutil
import tempfile


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


if __name__ == "__main__":
    unittest.main()
