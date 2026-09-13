# ISSUE_RESOLUTION_WORKFLOW (Coder Agent Guidelines)

This document establishes the **standard operating workflow** for Coder / Maintainer AI Agents (Agent B) when resolving GitHub issues, fixing bugs, or implementing requested tool enhancements in the `EDA_MCP` repository.

---

## Operational Invariants & Policies

### 1. 🌿 AGENT_IDENTITY_BRANCHING
- Every issue fix or enhancement MUST be implemented on a **dedicated feature branch** named after the active agent and issue ID:
  ```bash
  git checkout -b <agent_name>/issue-<issue_number>-<short-description>
  ```
- **Examples**:
  - `antigravity/issue-42-eldo-timeout-fix`
  - `codex/feature-spectre-parser`
  - `claude/issue-15-ssh-retry-logic`

---

### 2. ✍️ AGENT_IDENTITY_COMMITS
- All Git commits MUST explicitly declare author metadata corresponding to the active agent:
  ```bash
  git -c user.name="<AgentName>" -c user.email="<agent_name>@ai.local" commit -m "<type>: <concise description>"
  ```
- **Commit Types**:
  - `fix:` Bug fixes
  - `feat:` New features / tool enhancements
  - `refactor:` Code restructuring without functional changes
  - `test:` Unit test updates
  - `docs:` Documentation updates

---

### 3. 🔍 VERIFICATION BEFORE PR CREATION
- Before pushing changes or creating a Pull Request, the agent MUST run the full unit test suite and ensure all tests pass cleanly:
  ```bash
  python3 -m unittest discover tests
  ```

---

### 4. 🤝 AGENT_LANDLINE_PEER_REVIEW (Autonomous Inter-Agent Peer Review)
- When a GitHub issue is submitted by another AI agent (such as a Chip Design Consumer / Virtuoso & Eldo designer agent), the issue header banner explicitly includes their session ID:
  ```markdown
  > **Reported by Agent:** antigravity-client (`gemini-3.6-flash`) (Chip Design Consumer)
  > **Session ID:** `5728b34e-d49b-4465-8d3a-f600182d8fc3`
  ```
- The Coder Agent can use the `agent-landline` MCP server to collaborate directly with the reporting designer agent for real-time peer review before opening a Pull Request.

> [!IMPORTANT]
> **Working Directory & Source Code Access Caveats**:
> - **Different Working Directory (`cwd`)**: The reporting designer agent may be executing in a different workspace or project folder (e.g., dedicated to circuit layouts or simulations). When calling `initialize_agent`, you can explicitly set `cwd` to the `EDA_MCP` repository root (or keep their existing directory if verifying external artifacts).
> - **No Python Source Code Access**: The designer agent may not have access to the `EDA_MCP` repository source code, and even when present, designer agents are strictly prohibited by their system directives from inspecting Python (`.py`) codebase files.
> - **Review Scope**: Designer peer reviews must focus on `.md` operational documentation (`context/designer/`), SKILL scripts, SPICE decks, SVRF rules, and tool input/output behavioral contracts—**never** on internal Python implementation details.

#### Step 1: Connect to Reporting Agent Session
```json
// Call agent-landline:initialize_agent
{
  "conversation_id": "<session_id_from_issue>",
  "cwd": "/Users/vs/function/EDA_MCP"
}
```

#### Step 2: Confirm Process Health
```json
// Call agent-landline:agent_status
{
  "mode": "process"
}
```

#### Step 3: Request Detailed Peer Review
Send a prompt summarizing the implementation branch, files changed, and test results:
```json
// Call agent-landline:send_prompt
{
  "prompt": "Hello! I am the Coder Agent resolving Issue #<id> on branch <branch>. I have implemented the requested fixes: <summary_of_changes>. All unit tests pass cleanly. Please review these changes directly from the repository on the basis of: 1. Correctness, 2. Understandability, 3. Reliability for other agents. Please provide your critique and feedback.",
  "timeout": 300
}
```

#### Step 4: Solicit Critical Edge Cases & Subtleties
Ask the reporting agent to actively probe for subtle runtime traps or edge cases:
```json
// Call agent-landline:send_prompt
{
  "prompt": "As a critical peer review: What mistakes, subtleties, edge cases, or gaps might still exist in these changes? What could be done even better so another agent executing in this environment never encounters unexpected errors or silent failures?",
  "timeout": 300
}
```

#### Step 5: Incorporate Hardening & Final Approval
- Implement recommended fixes, re-run unit tests, commit changes with agent identity, and confirm resolution with the peer agent.
- Document the peer review verdict (**APPROVED & PRODUCTION-READY**) in the PR body.

---

### 5. 🤖 CROSS-AGENT COLLABORATION & ITERATIVE CHANGE WORKFLOW
When collaborating with another coding or designer agent (via a meta-harness, `agent-landline`, or chat directives) who is requesting changes or improvements:

1. **Dedicated Feature Branch**:
   - Never implement cross-agent changes on `main` or leave uncommitted modifications in the working tree.
   - Always create a dedicated branch immediately:
     ```bash
     git checkout -b <agent_name>/<task-or-feature-description>
     ```
2. **Commit Each Change Incrementally (Atomic Commits)**:
   - Commit each change as you are doing it (`git commit -m "..."`), rather than batching all changes at the end.
   - Every commit must declare explicit agent author identity:
     ```bash
     git -c user.name="<AgentName>" -c user.email="<agent>@ai.local" commit -m "<type>: <concise description>"
     ```
3. **Collaborator Satisfaction Gate**:
   - Continuously coordinate with the collaborating agent, iterate on changes, and incorporate their feedback.
   - **Do NOT open a PR prematurely**: Open the Pull Request only after the changes are completed, tested, and the collaborating agent has explicitly verified and confirmed full satisfaction with the implementation.
4. **Pull Request Header with Both Session IDs**:
   - The PR description MUST begin with a prominent metadata header containing both your Coder Agent session ID and the collaborating/Designer Agent session ID:
     ```markdown
     > [!NOTE]
     > **Automated Meta-Harness PR / Cross-Agent Collaboration PR**
     > This pull request was generated via an autonomous cross-agent collaboration harness:
     > - **Coder Agent Session ID:** `agy --conversation=<coder_session_id>`
     > - **Designer / Collaborating Agent Session ID:** `agy --conversation=<designer_session_id>`
     ```
5. **Mandatory PR Description Structure**:
   The PR body MUST include these four essential sections:
   - `## Motivation & Problem Statement`: The core reason for the PR, user intent, failure modes or bottlenecks encountered.
   - `## How We Are Solving It (Technical Solution)`: Clear technical breakdown of the changes, architectural decisions, and files modified.
   - `## Verification & Proof`: Concrete evidence and exact commands used to verify the solution (unit tests passing, simulation logs, DRC/LVS clean reports, POC cellviews).
   - `## Other Useful Information`: Key discoveries, operational rules, PDK/tool quirks, environment traps, or summary table of modified files.

---

### 6. 📝 PULL REQUEST EXPLANATION & ISSUE LINKING
- The agent MUST open a Pull Request using `gh pr create`.
- **Single-Agent Issue PR Banner**: For PRs resolving standalone GitHub issues, begin with the standard agent metadata banner:
  ```markdown
  > **Resolved by Agent:** `<agent_name>` (`<agent_model>`) (Coder / Maintainer)
  > **Session ID:** `<session_id>`
  > **MCP Log File:** `temp/eda_mcp_YYYYMMDD_HHMMSS_<PID>.log`
  ---
  ```
- **Cross-Agent / Meta-Harness PR Banner**: Use the dual-session banner documented in Section 5 above.
- The PR body MUST include:
  - **Header Banner**: Metadata block identifying agent session(s).
  - **Motivation / Problem Statement**: Why the change is being made.
  - **Technical Fix / Implementation**: What code or documentation was altered.
  - **Verification**: Output summary of passing tests and validation steps.
  - **Other Useful Information**: Caveats, discoveries, or instructions for other agents.
  - **Issue Link**: GitHub magic keyword tagging the original issue (`Fixes #<issue_number>` or `Closes #<issue_number>`), if applicable.

#### Example Cross-Agent PR Creation Command:
```bash
gh pr create \
  --title "feat(designer): headless Layout XL batch flow via lxGenFromSource" \
  --label "enhancement" \
  --label "Antigravity" \
  --body "> [!NOTE]
> **Automated Meta-Harness PR**
> - **Coder Agent Session ID:** \`agy --conversation=c76d1778-22a8-480c-aa8d-ff24f29bbbeb\`
> - **Designer Agent Session ID:** \`agy --conversation=06bccc54-66cb-44dd-a3d7-3db1906071de\`

---

## Motivation & Problem Statement
Layout XL previously assumed an active GUI session (assisted_run). Autonomous workflows require headless batch generation without graphic windows.

## How We Are Solving It
- Implemented lxGenFromSource API in documentation and execution flows.
- Added post-generation M1 drawing rectangle binding for M1.PIN.CAD.1 foundry rule.

## Verification
- Designed, placed, routed, and verified CMOS Transmission Gate.
- Calibre DRC passed cleanly with 0 errors across 1,581 checks.

## Other Useful Information
- Requires passing PDK layer map cmos065.layermap to strmout to avoid R_forbidden.1 trap." \
  --base main
```

---

### 7. 🏷️ GITHUB LABEL AUTO-CREATION & PR ATTACHMENT
- **Pre-Check**: Before running `gh pr create`, the agent MUST check if the agent label (e.g. `Antigravity`, `Claude`, `Codex`) exists using `gh label list`.
- **Auto-Create**: If the label does not exist on GitHub, the agent MUST run `gh label create "<label_name>" --color "0E8A16"` to create it (unless agent name is `"unknown"`).
- **PR Attachment**: All Pull Requests MUST pass `--label "<agent_name>"` and `--label "<type>"` (e.g. `--label "bug"` or `--label "enhancement"`).

---

### 8. 🔄 MCP SERVER RELOADING
- When code changes in `src/server.py`, `src/clients/*`, or `src/core/*` are completed, the running Python MCP process must be reloaded for changes to take effect in active environments.
- Consult [`context/coder/mcp_reload_guide.md`](mcp_reload_guide.md) for step-by-step instructions on process termination (`pkill`), IDE reload, CLI session restart, and remote SKILL reloading.

---

### 9. 🛑 STRICT NO AUTO-MERGE POLICY (HUMAN REVIEW GATE)
- **STRICT RULE**: The Coder Agent **MUST NEVER** execute `git merge`, `gh pr merge`, or merge code into `main`.
- Immediately after executing `gh pr create`, the Coder Agent MUST **STOP execution** and notify the human reviewer (You) that the PR is open and awaiting review.
- Only the human maintainer is authorized to review and merge code into `main`.

---

## Step-by-Step Coder Execution Checklist

1. [ ] **Inspect Task/Issue**: Read issue or collaborator instructions. Extract peer `Session ID` if present.
2. [ ] **Create Dedicated Branch**: Run `git checkout -b <agent_name>/<task-description>`.
3. [ ] **Implement Changes Incrementally**: Edit source or docs, committing each change as you go with custom agent author identity (`git commit -m "..."`).
4. [ ] **Verify Tests**: Run `python3 -m unittest discover tests` and any domain-specific verifications (DRC/LVS/simulation).
5. [ ] **Collaborator Satisfaction**: Ensure the collaborating agent has reviewed and confirmed complete satisfaction.
6. [ ] **Reload MCP Server (if backend changed)**: Follow [`mcp_reload_guide.md`](mcp_reload_guide.md) to restart the server and run sanity checks.
7. [ ] **Push Branch**: Run `git push origin <agent_name>/<task-description>`.
8. [ ] **Open Pull Request**: Run `gh pr create` with dual-session header, Motivation/Problem, Solution, Verification, and Other Useful Info.
9. [ ] **Stop & Request Human Review**: Stop execution and inform the human reviewer. Never auto-merge.
