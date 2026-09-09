"""
Root entrypoint shim for EDA_MCP.
Delegates execution to the modular FastMCP server inside src/server.py.
Maintains full backward compatibility for existing MCP client configurations.
"""
import os
import sys

# Ensure the project root is in sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Re-export MCP instance and tool endpoints
from src.server import (
    mcp,
    remote_control,
    virtuoso,
    eldo,
    workboard,
    report_issue,
    remote_session,
    virtuoso_client,
    eldo_client,
    workboard_client,
    base_dir,
)

if __name__ == "__main__":
    mcp.run()
