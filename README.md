# EDA_MCP: Agentic EDA Control Plane & Intelligent Chip Design Workspace

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Protocol: FastMCP](https://img.shields.io/badge/Protocol-FastMCP-8A2BE2.svg)](https://modelcontextprotocol.io/)
[![Latency: <10ms](https://img.shields.io/badge/Latency-%3C10ms%20SSH-brightgreen.svg)]()
[![PDK: cmos065](https://img.shields.io/badge/PDK-cmos065%2065nm-blue.svg)]()
[![Autonomous Agents Ready](https://img.shields.io/badge/Agents-Antigravity%20%7C%20Cursor%20%7C%20Windsurf%20%7C%20Claude-orange.svg)]()

> **Transforming AI Coding Agents into Autonomous IC Design Engineers.**  
> `EDA_MCP` is a high-performance Model Context Protocol (MCP) server that connects local AI IDEs and agents (Antigravity, Cursor, Windsurf, Claude Desktop, Claude Code) directly to remote Linux EDA compute clusters executing Cadence Virtuoso and Siemens Eldo.

---

## 📹 Demo Video

<video src="https://raw.githubusercontent.com/SiliCAD/EDA_MCP/main/doc/media/demo.mp4" autoplay loop muted playsinline controls width="100%"></video>

<p>
  If your browser or this renderer blocks embedded video, open/download the file directly:
  <a href="https://github.com/SiliCAD/EDA_MCP/raw/main/doc/media/demo.mp4">View / Download demo.mp4 (raw)</a>
</p>

*(Video Source: [`doc/media/demo.mp4`](https://github.com/SiliCAD/EDA_MCP/blob/main/doc/media/demo.mp4))*

💡 **Experiment & Solve Interview Problems**: Use `EDA_MCP` to experiment with custom circuits, run SPICE simulations, and solve real-world IC design interview questions.  
🎓 **Classic Interview Demo**: The demonstration video above showcases a classic hardware/IC design interview problem — constructing, CDL netlisting, and simulating a **depletion-load inverter** live inside Cadence Virtuoso and Siemens Eldo.

---

## 💡 Why EDA_MCP? Thoughtful Workspace Technology

Modern Integrated Circuit (IC) design demands high-performance Linux compute clusters hosting multi-gigabyte EDA tool suites (Cadence Virtuoso, Siemens Eldo) and proprietary PDKs (e.g. `cmos065`). However, AI developer tools and LLM agents operate locally inside modern IDEs.

`EDA_MCP` bridges this divide with an ultra-lightweight, resilient architecture built on 6 foundational pillars:

1. ⚡ **Sub-10ms SSH Multiplexing Engine**: Eliminates SSH handshake overhead by using persistent OpenSSH `ControlMaster` unix domain sockets and streaming file transport ([`ssh_client.py`](file:///Users/vs/function/EDA_MCP/ssh_client.py) & [`scp_client.py`](file:///Users/vs/function/EDA_MCP/scp_client.py)).
2. 🗂️ **Git-Backed WorkBoard Workspace (`workboard`)**: Local-remote workspace synchronizer that mirrors, tracks, versions, and computes unified line-by-line diffs for remote EDA files locally before pushing edits back to the cluster ([`workboard_client.py`](file:///Users/vs/function/EDA_MCP/workboard_client.py)).
