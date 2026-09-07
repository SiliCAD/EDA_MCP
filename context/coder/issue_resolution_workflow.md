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
- The Coder Agent can use the `agent-landline` MCP server to collaborate directly with the reporting designer agent for real-time peer review before opening a Pull Request:

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

### 5. 📝 PULL REQUEST EXPLANATION & ISSUE LINKING
- The agent MUST open a Pull Request using `gh pr create`.
- **PR Metadata Banner**: The PR description MUST begin with a metadata banner identifying the fixing agent, model, session ID, and log file (matching the Issue header format):
  ```markdown
  > **Resolved by Agent:** `<agent_name>` (`<agent_model>`) (Coder / Maintainer)
  > **Session ID:** `<session_id>`
  > **MCP Log File:** `temp/eda_mcp_YYYYMMDD_HHMMSS_<PID>.log`
  ---
  ```
- The PR body MUST include:
  - **Header Banner**: Metadata block identifying agent, model, session ID, and log path.
  - **Summary**: Concise description of what was fixed or implemented.
  - **Root Cause & Technical Fix**: Technical explanation of why the bug occurred and how the code was updated.
  - **Test Verification**: Output summary of passing unit tests.
  - **Peer Review Verification**: Summary of peer review feedback from reporting agent via `agent-landline` (if applicable).
  - **Issue Link**: Explicit GitHub magic keyword tagging the original issue (`Fixes #<issue_number>` or `Closes #<issue_number>`).

#### Example PR Creation Command:
```bash
# 1. Ensure agent label exists on GitHub (creates if missing)
gh label list | grep -i "Antigravity" || gh label create "Antigravity" --color "0E8A16" --description "PRs created by Antigravity Agent"

# 2. Open PR with agent and type labels attached
gh pr create \
  --title "fix(eldo): retry file lock acquisition during IPC polling" \
  --label "bug" \
  --label "Antigravity" \
  --body "> **Resolved by Agent:** antigravity (\`gemini-3.6-flash\`) (Coder / Maintainer)
> **Session ID:** \`turn-c73adfac-a8dd\`
> **MCP Log File:** \`temp/eda_mcp_20260816_182421_17427.log\`
---

## Summary
Fixes Eldo simulation timeout caused by premature file lock failure.

## Technical Details & Root Cause
- Added exponential backoff retry loop in \`eldo_client.py\` when reading \`.chi\` output files.
- Auto-recovers from transient file locks without aborting simulation.

## Verification
- Ran \`python3 -m unittest discover tests\` (14/14 tests passing).
- Verified with reporting designer agent via \`agent-landline\` (APPROVED).

Fixes #42" \
  --base main
```

---

### 6. 🏷️ GITHUB LABEL AUTO-CREATION & PR ATTACHMENT
- **Pre-Check**: Before running `gh pr create`, the agent MUST check if the agent label (e.g. `Antigravity`, `Claude`, `Codex`) exists using `gh label list`.
- **Auto-Create**: If the label does not exist on GitHub, the agent MUST run `gh label create "<label_name>" --color "0E8A16"` to create it (unless agent name is `"unknown"`).
- **PR Attachment**: All Pull Requests MUST pass `--label "<agent_name>"` and `--label "<type>"` (e.g. `--label "bug"` or `--label "enhancement"`).

---

### 7. 🛑 STRICT NO AUTO-MERGE POLICY (HUMAN REVIEW GATE)
- **STRICT RULE**: The Coder Agent **MUST NEVER** execute `git merge`, `gh pr merge`, or merge code into `main`.
- Immediately after executing `gh pr create`, the Coder Agent MUST **STOP execution** and notify the human reviewer (You) that the PR is open and awaiting review.
- Only the human maintainer is authorized to review and merge code into `main`.

---

## Step-by-Step Coder Execution Checklist

1. [ ] **Inspect Issue**: Read issue details via `gh issue view <issue_number>`. Check for `Session ID` in issue banner.
2. [ ] **Create Branch**: Run `git checkout -b <agent_name>/issue-<issue_number>-<description>`.
3. [ ] **Implement Fix**: Edit source files (`server.py`, `issue_reporter.py`, `*_client.py`, `context/*`).
4. [ ] **Verify Tests**: Run `python3 -m unittest discover tests` and ensure 0 failures.
5. [ ] **Peer Review via agent-landline**: If `Session ID` is present, resume session with `initialize_agent`, request review with `send_prompt`, probe for edge cases, and harden solution.
6. [ ] **Commit with Identity**: Run `git -c user.name="<AgentName>" -c user.email="<agent>@ai.local" commit -m "..."`.
7. [ ] **Push Branch**: Run `git push origin <agent_name>/issue-<issue_number>-<description>`.
8. [ ] **Open Pull Request**: Run `gh pr create` with `Fixes #<issue_number>`, test proof, and peer review summary.
9. [ ] **Stop & Request Review**: Stop execution and inform the human reviewer.
