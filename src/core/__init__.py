"""
Core transport and infrastructure layer for EDA_MCP.
Provides persistent SSH remote sessions and OpenSSH SCP file transfer.
"""
from .ssh_client import RemoteSession
from .scp_client import SCPClient

__all__ = ["RemoteSession", "SCPClient"]
