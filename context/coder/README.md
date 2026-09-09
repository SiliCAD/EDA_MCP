# CODER_CONTEXT_SPEC (Python MCP Server Implementation)

## Component Map & File References

| Component | Source File | Class / Function | Description |
| :--- | :--- | :--- | :--- |
| **MCP Entrypoint** | [`server.py`](../../src/server.py) | `FastMCP("EDA_MCP")` | Registers 4 MCP tools, initializes per-tool SSH sessions, configures logger (`logs/eda_mcp_*.log`). |
| **SSH Transport** | [`ssh_client.py`](../../src/core/ssh_client.py) | `RemoteSession` | Manages persistent `csh` subshell over SSH, sentinel execution (`_read_until_sentinel`), and interactive stream reading (`execute_interactive_stream`). |
| **SCP Transport** | [`scp_client.py`](../../src/core/scp_client.py) | `SCPClient` | Executes OpenSSH `scp -O` for direct binary/folder transfer without shell escaping overhead. |
| **Virtuoso Interface** | [`virtuoso_client.py`](../../src/clients/virtuoso_client.py) | `VirtuosoClient` | Manages SKILL FIFO pipe (`MCP.command`) IPC polling (`mcp_output.txt`) and `virtuoso -nograph` REPL streaming. |
| **Eldo Interface** | [`eldo_client.py`](../../src/clients/eldo_client.py) | `EldoClient` | Manages `eldo -inter` REPL streaming and `.extract` measurement summary parsing. |
| **WorkBoard Engine** | [`workboard_client.py`](../../src/clients/workboard_client.py) | `WorkBoardClient` | Manages `./workboard/<name>/` local Git repositories, `.workboard.json` manifests, SHA-256 checksums, and unified diffs. |
| **Issue Reporter** | [`issue_reporter.py`](../../src/issue_reporter.py) | `IssueReporter` | Autonomous GitHub issue reporting with smart label normalization, random-color creation, and fallback recovery. |

---

## Repository Architecture (`src/` Modular Layout)

```text
EDA_MCP/
├── server.py                   # Backward-compatible entrypoint shim for MCP runners
├── src/
│   ├── __init__.py             # Exports IssueReporter
│   ├── server.py               # FastMCP server definition & tool registration
│   ├── issue_reporter.py       # Autonomous GitHub issue & smart label reporter
│   │
│   ├── core/                   # Infrastructure & Transport Layer
│   │   ├── __init__.py         # Exports RemoteSession, SCPClient
│   │   ├── ssh_client.py       # Persistent CSH subshell, sentinels, interactive streams
│   │   └── scp_client.py       # OpenSSH SCP direct transfer engine
│   │
│   └── clients/                # High-Level Domain Tool Clients
│       ├── __init__.py         # Exports VirtuosoClient, EldoClient, WorkBoardClient
│       ├── virtuoso_client.py  # Cadence Virtuoso SKILL FIFO / REPL controller
│       ├── eldo_client.py      # Siemens Eldo simulation engine
│       ├── eldo_plotter.py     # Waveform viewer / PyQtGraph plotting engine
│       └── workboard_client.py # Local-remote Git workspace synchronizer
│
├── tests/                      # Unit and integration test suites
├── config/                     # Remote SSH / tool JSON configs
└── context/                    # Dual-track agent directives (designer & coder)
```

---

## Agent Operational Invariants (Suggestion)

1. **AGENT_IDENTITY_BRANCHING**: Every issue fix or enhancement MUST be created on a feature branch named `<agent_name>/issue-<issue_number>-<description>` (e.g., `antigravity/issue-42-eldo-timeout-fix`).
2. **AGENT_IDENTITY_COMMITS**: All commits MUST explicitly declare custom agent author metadata: `git -c user.name="<AgentName>" -c user.email="<agent>@ai.local" commit -m "..."`.
3. **PULL_REQUEST_EXPLANATION**: Pull Requests MUST be created via `gh pr create` with Metadata Header Banner (`Resolved by Agent`, `agent_model`, `session_id`, `log_file`), PR label auto-creation (`gh label create`), attached `--label "<agent_name>"`, root cause explanation, fix details, test verification, and issue linkage (`Fixes #<issue_number>`).
4. **STRICT_NO_AUTOMERGE_POLICY**: Coder Agents MUST NEVER merge PRs or push directly to `main`. Stop execution immediately after `gh pr create` and request Human Code Review.
5. **PEER_REVIEW_VIA_AGENT_LANDLINE**: When an issue is reported by another AI agent (such as a Chip Design Consumer / Virtuoso & Eldo designer agent), extract the `Session ID` from the issue header banner. Use the `agent-landline` MCP server to initialize that session, prompt the reporting agent to review the changes (for correctness, understandability, and reliability), solicit edge-case critiques, and harden the solution before opening a PR. Note that the designer agent's working directory may be different and they may not have source code access to `EDA_MCP` (and are prohibited from inspecting Python code); review should focus on `.md` operational context, SKILL/SPICE scripts, and tool interface contracts rather than Python implementation files.

---

## 🤖 MANDATORY_AGENT_PRE_TASK_HOOKS (Machine Directives)

> **STRICT AGENT INSTRUCTION**: Before executing code edits, git operations, or server maintenance listed below, the AI Agent MUST execute `view_file` on the linked specification file to load system constraints into active memory.

| Action Trigger / Task Intent | Mandatory Target Spec File | Required Pre-Execution Context Inspection |
| :--- | :--- | :--- |
| **GitHub Issue Fixing / Branching / PR Creation** | [`context/coder/issue_resolution_workflow.md`](issue_resolution_workflow.md) | Agent branch naming (`<agent>/issue-<id>-<desc>`), custom author commits, PR label auto-creation (`gh label create`), PR templates, **STRICT NO-AUTOMERGE RULE**. |
| **Server Architecture / MCP Handler Edits** | [`context/coder/server_and_mcp.md`](server_and_mcp.md) | `FastMCP` session allocations (`RemoteSession`), tool dispatch table, logger setup (`logs/eda_mcp_*.log`). |
| **SSH / SCP Transport Layer Edits** | [`context/coder/transport_layer.md`](transport_layer.md) | Subshell `csh` sentinel tokens, regex REPL stream matching, OpenSSH `scp -O` parameters. |
| **Virtuoso / Eldo Tool Client Edits** | [`context/coder/eda_tool_clients.md`](eda_tool_clients.md) | `MCP.command` FIFO pipe IPC state machine, `MCP_setup.il` error trapping, REPL interactive loops. |
| **WorkBoard Engine Edits** | [`context/coder/workboard_backend.md`](workboard_backend.md) | `.workboard.json` registry schema, `_git_cmd` subprocess wrapper, SHA-256 checksum tracking. |
| **Debugging / Running Test Suites** | [`context/coder/known_issues_and_maintenance.md`](known_issues_and_maintenance.md) | Bug audit matrices, test suite discovery commands (`python3 -m unittest discover tests`). |

---

## Coder Context Index

- [`context/coder/issue_resolution_workflow.md`](issue_resolution_workflow.md): Standard operating procedure for Coder agents resolving issues, creating agent branches, PR formatting, and human review gates.
- [`context/coder/server_and_mcp.md`](server_and_mcp.md): FastMCP tool signatures, tool action dispatching, session isolation logic.
- [`context/coder/transport_layer.md`](transport_layer.md): Subshell IO pipes, sentinel token format, regex prompt match loop, SCP command generation.
- [`context/coder/eda_tool_clients.md`](eda_tool_clients.md): FIFO pipe write/read contract, REPL interactive streaming state machine.
- [`context/coder/workboard_backend.md`](workboard_backend.md): `.workboard.json` schema, Git subprocess wrapper (`_git_cmd`), `diff` auto-advance algorithm.
- [`context/coder/known_issues_and_maintenance.md`](known_issues_and_maintenance.md): Bug audit list (missing `run_script`), test discovery commands.
