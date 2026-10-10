import os
import json
import time
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch
import anyio
import src.server as server
from src.core.command_guard import CommandGuard


class SlowSCP:
    """Offline SCP with network-like latency so concurrent calls genuinely overlap."""
    def __init__(self):
        self.uploads = {}

    def download(self, remote_path, local_path, timeout=60.0):
        time.sleep(0.1)
        with open(local_path, "w") as f:
            f.write(remote_path)

    def upload(self, local_path, remote_path, timeout=60.0):
        with open(local_path, "rb") as f:
            self.uploads[remote_path] = f.read()


class TestWorkBoardServerHardening(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp(prefix="test_wb_conc_")
        self.audit = os.path.join(self.project, "audit.jsonl")
        self.scp = SlowSCP()
        self._saved = (server._workboard_explicit_root, server.workboard_client.base_workboard_dir,
                       server.workboard_client.scp_client, server.command_guard,
                       os.environ.pop("WORKBOARD_ROOT", None))
        server._workboard_explicit_root = ""
        server.workboard_client.scp_client = self.scp
        server.command_guard = CommandGuard(audit_log_path=self.audit)

    def tearDown(self):
        root, base, scp, guard, env = self._saved
        server._workboard_explicit_root = root
        server.workboard_client.base_workboard_dir = base
        server.workboard_client.scp_client = scp
        server.command_guard = guard
        if env is None:
            os.environ.pop("WORKBOARD_ROOT", None)
        else:
            os.environ["WORKBOARD_ROOT"] = env
        shutil.rmtree(self.project, ignore_errors=True)

    def _board(self, name="b"):
        return os.path.join(self.project, "workboard", name)

    async def test_parallel_adds_all_registered(self):
        results = []
        async def one(i):
            results.append(await server.workboard(action="add", workboard_name="b", remote_path=f"/r/f{i}.chi",
                                                  local_path=f"f{i}.chi", workspace_root=self.project))
        async with anyio.create_task_group() as tg:
            for i in range(6):
                tg.start_soon(one, i)
        self.assertTrue(all("Successfully added" in r for r in results), results)
        with open(os.path.join(self._board(), ".workboard.json")) as f:
            registered = sorted(json.load(f)["files"])
        self.assertEqual(registered, [f"f{i}.chi" for i in range(6)])

    async def _write_local(self, rel, text="* deck\n.end\n"):
        await server.workboard(action="initialize", workboard_name="b", workspace_root=self.project)
        with open(os.path.join(self._board(), rel), "w") as f:
            f.write(text)

    async def test_export_outside_allowed_dirs_blocked_before_upload(self):
        await self._write_local("tb.cir")
        with patch.object(server.remote_session, "execute_command") as ex:
            res = await server.workboard(action="export", workboard_name="b", local_path="tb.cir",
                                         remote_path="~/.cshrc")
        self.assertIn("Error: Blocked", res)
        self.assertEqual(self.scp.uploads, {})
        ex.assert_not_called()

    async def test_export_unsafe_remote_path_rejected(self):
        await self._write_local("tb.cir")
        res = await server.workboard(action="export", workboard_name="b", local_path="tb.cir",
                                     remote_path="/tmp/x;rm -rf ~")
        self.assertIn("characters the remote shell would interpret", res)
        self.assertEqual(self.scp.uploads, {})

    async def test_export_existence_check_runs_on_event_loop_thread(self):
        await self._write_local("tb.cir")
        seen = {}
        def fake_exec(cmd, timeout=60.0):
            seen["thread"] = threading.current_thread() is threading.main_thread()
            seen["cmd"] = cmd
            return 1, "", ""  # does not exist yet
        with patch.object(server.remote_session, "execute_command", side_effect=fake_exec):
            res = await server.workboard(action="export", workboard_name="b", local_path="tb.cir",
                                         remote_path="/tmp/wb_tb.cir")
        self.assertIn("Successfully exported", res)
        self.assertTrue(seen["thread"], "remote_session must not be used from a worker thread")
        self.assertEqual(seen["cmd"], "test -e /tmp/wb_tb.cir")

    async def test_push_to_registered_path_outside_allowed_dirs_blocked(self):
        await self._write_local("ref.cir")
        reg_path = os.path.join(self._board(), ".workboard.json")
        with open(reg_path) as f:
            reg = json.load(f)
        reg["files"]["ref.cir"] = {"remote_path": "/modelfile_65nm/typNtypP.cir", "local_checksum": ""}
        with open(reg_path, "w") as f:
            json.dump(reg, f)
        res = await server.workboard(action="push", workboard_name="b", local_path="ref.cir")
        self.assertIn("Error: Blocked", res)
        self.assertEqual(self.scp.uploads, {})

    async def test_invalid_env_root_is_an_error(self):
        os.environ["WORKBOARD_ROOT"] = os.path.join(self.project, "typo")
        res = await server._resolve_workboard_root("", None)
        self.assertIn("WORKBOARD_ROOT", res)
        self.assertFalse(os.path.exists(os.path.join(self.project, "typo")))


if __name__ == "__main__":
    unittest.main()
