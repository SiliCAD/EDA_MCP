"""
EDA Daemon Client SDK.

Allows external Python automation scripts, test suites, and custom agents to
communicate seamlessly with the running EDA_MCP Daemon over HTTP without
managing raw SSH connections or conflicting with the Cadence Virtuoso FIFO.
"""
from typing import Optional, Dict, Any
import httpx

class EDADaemonClient:
    """
    HTTP client for interacting with the EDA_MCP background daemon.
    Provides methods mirroring the standard EDA_MCP tool interfaces.
    """
    def __init__(self, base_url: str = "http://127.0.0.1:8765", default_timeout: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self.default_timeout = default_timeout
        self._client = httpx.Client(base_url=self.base_url, timeout=self.default_timeout)

    def health(self) -> Dict[str, Any]:
        """Checks if the background daemon is alive and responding."""
        resp = self._client.get("/health")
        resp.raise_for_status()
        return resp.json()

    def virtuoso(
        self,
        action: str = "assisted_run",
        command: str = "",
        work_dir: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> str:
        """
        Executes a Virtuoso action (e.g. assisted_run, standalone) via the daemon.
        """
        payload = {
            "action": action,
            "command": command,
            "work_dir": work_dir,
            "timeout": timeout or 30.0
        }
        resp = self._client.post("/virtuoso", json=payload)
        resp.raise_for_status()
        return resp.json()["result"]

    def eldo(
        self,
        action: str,
        command: str = "",
        work_dir: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> str:
        """
        Executes an Eldo action (e.g. run_terminal_command, run_script) via the daemon.
        """
        payload = {
            "action": action,
            "command": command,
            "work_dir": work_dir,
            "timeout": timeout or 30.0
        }
        resp = self._client.post("/eldo", json=payload)
        resp.raise_for_status()
        return resp.json()["result"]

    def workboard(
        self,
        action: str,
        local_path: str = "",
        remote_path: str = "",
        workboard_name: str = "default",
        message: str = "Client sync",
        overwrite: bool = False,
        timeout: Optional[float] = None
    ) -> str:
        """
        Executes WorkBoard local-remote workspace sync actions via the daemon.
        """
        payload = {
            "action": action,
            "local_path": local_path,
            "remote_path": remote_path,
            "workboard_name": workboard_name,
            "message": message,
            "overwrite": overwrite,
            "timeout": timeout or 60.0
        }
        resp = self._client.post("/workboard", json=payload)
        resp.raise_for_status()
        return resp.json()["result"]

    def remote_control(
        self,
        action: str,
        command: str = "",
        path: str = "",
        content: str = "",
        timeout: Optional[float] = None
    ) -> str:
        """
        Executes remote shell commands or file operations via the daemon.
        """
        payload = {
            "action": action,
            "command": command,
            "path": path,
            "content": content,
            "timeout": timeout or 60.0
        }
        resp = self._client.post("/remote_control", json=payload)
        resp.raise_for_status()
        return resp.json()["result"]
