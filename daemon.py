"""
EDA_MCP Local Background Daemon.

Provides a persistent HTTP REST endpoint for EDA_MCP tool operations, allowing
external Python scripts, automation flows, and multiple agent instances to share
a single active Cadence Virtuoso session without FIFO or cellview lock collisions.
"""
import os
import sys
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

# Ensure base_dir is in sys.path
base_dir = os.path.abspath(os.path.dirname(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# Import existing tool functions from EDA_MCP
from src.server import virtuoso, eldo, workboard, remote_control, logger

app = FastAPI(
    title="EDA_MCP Background Daemon",
    description="HTTP Gateway to persistent Cadence Virtuoso, Siemens Eldo, and WorkBoard sessions",
    version="1.0.0"
)

class ToolPayload(BaseModel):
    action: str
    command: Optional[str] = ""
    path: Optional[str] = ""
    content: Optional[str] = ""
    work_dir: Optional[str] = None
    local_path: Optional[str] = ""
    remote_path: Optional[str] = ""
    workboard_name: Optional[str] = "default"
    message: Optional[str] = "Daemon sync"
    overwrite: Optional[bool] = False
    timeout: Optional[float] = 60.0

@app.get("/health")
def health_check():
    """Health check probe for daemon and active process tracking."""
    return {"status": "ok", "pid": os.getpid(), "service": "eda_mcp_daemon"}

@app.post("/virtuoso")
def api_virtuoso(p: ToolPayload):
    """Executes Virtuoso actions (assisted_run, standalone, etc.)."""
    res = virtuoso(action=p.action, command=p.command, work_dir=p.work_dir or "~/Desktop/cmos65", timeout=p.timeout)
    return {"result": res}

@app.post("/eldo")
def api_eldo(p: ToolPayload):
    """Executes Eldo simulation actions (run_terminal_command, run_script, etc.)."""
    res = eldo(action=p.action, command=p.command, work_dir=p.work_dir or "~/Desktop/cmos65", timeout=p.timeout)
    return {"result": res}

@app.post("/workboard")
def api_workboard(p: ToolPayload):
    """Executes WorkBoard local-remote workspace synchronization actions."""
    res = workboard(
        action=p.action,
        local_path=p.local_path,
        remote_path=p.remote_path,
        workboard_name=p.workboard_name,
        message=p.message,
        overwrite=p.overwrite,
        timeout=p.timeout
    )
    return {"result": res}

@app.post("/remote_control")
def api_remote_control(p: ToolPayload):
    """Executes shell commands or direct file I/O on the remote server."""
    res = remote_control(action=p.action, command=p.command, path=p.path, content=p.content, timeout=p.timeout)
    return {"result": res}

def run_daemon(host: str = "127.0.0.1", port: int = 8765):
    logger.info(f"Starting EDA_MCP Daemon on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_daemon()
