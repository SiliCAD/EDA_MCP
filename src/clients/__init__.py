"""
Domain tool client layer for EDA_MCP.
Provides interfaces for Cadence Virtuoso, Siemens Eldo, SPICE plotting, and WorkBoard workspace sync.
"""
from .virtuoso_client import VirtuosoClient
from .eldo_client import EldoClient
from .workboard_client import WorkBoardClient

__all__ = ["VirtuosoClient", "EldoClient", "WorkBoardClient"]
