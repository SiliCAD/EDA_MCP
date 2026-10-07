# MCP_TOOLS_SPECIFICATION

## Tool 1: `remote_control`
**Description**: Remote Linux shell execution and direct text file I/O.

### Interface Schema
```typescript
type RemoteControlArgs = {
  action: "run_command" | "run_remote_command" | "run" | "exec" | "execute"
        | "read_file" | "read_remote_file" | "read"
        | "write_file" | "write_remote_file" | "write";
  command?: string; // Required when action is command execution
  path?: string;    // Required for read_file / write_file
  content?: string; // Required for write_file
  timeout?: number; // Default: 60.0s
  dry_run?: boolean; // Default: false. Report the command-guard verdict for run_command/write_file without executing.
};
```

### Command Guard (safety checks)
Every agent-supplied shell command (`remote_control` `run_command`, and `virtuoso` / `eldo` `run_terminal_command`) and every `write_file` path is checked BEFORE execution. Blocked commands are never sent to the server and return `Error: Blocked: <reason>` + `The command was NOT executed.`

| Rule | Examples blocked | Allowed |
| :--- | :--- | :--- |
| Always blocked | `mkfs`, `dd of=/dev/...`, `shutdown`/`reboot`, `kill -9 1`, `chmod 777`, fork bombs | — |
| Write/delete targets must be inside allowed dirs (default `~/Desktop/cmos65`, `~/Desktop/eldo`, `/tmp`) | `rm -rf ~`, `echo x > ~/.cshrc`, `mv lib ~/old`, `write_file ~/.cshrc` | `rm -rf ~/Desktop/cmos65/drc_run`, `echo x > /tmp/a.txt` |
| Never delete an allowed root or match everything in it | `rm -rf ~/Desktop/cmos65`, `rm -rf ~/Desktop/cmos65/*`, `find ~/Desktop/cmos65 -delete` | `rm -f ~/Desktop/eldo/*.chi`, `rm -rf ~/Desktop/cmos65/drc_run/*`, `find ~/Desktop/cmos65 -name '*.cdslck' -delete` |
| Other file writers are checked too | `sed -i ... ~/.cshrc`, `dd of=~/.cshrc`, `python3 -c "os.remove(...)"` / `perl -e "unlink ..."` | `sed -i ... ~/Desktop/eldo/tb.cir`, `python3 -c "print(1)"` |
| Targets must be verifiable | `rm -f tb.chi` (relative, unknown cwd), `rm -rf $(pwd)`, `rm -rf $VAR/x`, `ls \| xargs rm` | `cd ~/Desktop/eldo && rm -f tb.chi` |

- Read-only commands (`ls`, `cat`, `grep`, `ps`, tool launches) are never restricted by path.
- `virtuoso`/`eldo` `run_terminal_command` resolve relative paths against their `work_dir`, so `eldo tb.cir > tb.log` works.
- Checks also apply inside `bash -c "..."`, `eval`, and chains joined by `;`, `&&`, `||`, newlines.
- If a block is wrong for your task, do NOT try to rephrase around it; report it to the human user (they can edit `config/command_guard.json`).
- The guard is a seatbelt against hallucinated commands, not a sandbox: it can't see inside script files (`python3 script.py`, `./run.sh`) or SKILL `system()` calls. Keep destructive work in explicit `rm`/`mv` commands on absolute paths.
- Use `dry_run=true` to check a command first: returns `[DRY RUN] Command was NOT executed ... Guard verdict: Allowed (would run).`

### Action Behavior & Return Formats
- `run_command`: Executes `command` in persistent `csh` session.
  - *Returns*: `Exit Status: <code>\n--- STDOUT ---\n<out>\n--- STDERR ---\n<err>`
- `read_file`: Reads text from `path`.
  - *Returns*: Text content string.
- `write_file`: Encodes `content` as Base64 and writes to `path`. Prefer WorkBoard for reviewable simulation artifacts; use direct write only when explicitly appropriate to the task.
  - *Returns*: `"Successfully wrote <bytes> bytes to remote file '<path>'."`

---

## Tool 2: `virtuoso`
**Description**: Cadence Virtuoso lifecycle management and SKILL code execution.

### Interface Schema
```typescript
type VirtuosoArgs = {
  action: "start_standalone" | "start"
        | "standalone" | "run_standalone"
        | "stop_standalone" | "stop"
        | "assisted_run" | "assisted" | "run"
        | "run_terminal_command" | "terminal" | "shell"
        | "exit";
  command?: string;  // SKILL code string or terminal shell command
  work_dir?: string; // Default: "~/Desktop/cmos65"
  timeout?: number;  // Default: 30.0s
};
```

### Action Modes
- `start_standalone`: Launches non-graphical Virtuoso REPL (`virtuoso -nograph`).
- `standalone`: Sends SKILL statement to active `virtuoso -nograph` REPL stream.
- `stop_standalone`: Sends `exit()` to non-graphical REPL and closes session.
- `assisted_run`: Sends SKILL code to GUI Virtuoso via FIFO pipe (`MCP.command`) and polls `mcp_output.txt`. **Formatting Guarantee**: The server removes `;;` comments and normalizes newlines; use `;;` comments only. Do NOT write temporary `.il` files to disk. **GUI Window Display**: When asked to build or open a schematic/layout view, ALWAYS open the GUI window FIRST (for schematics: `win = geOpen(?lib ... ?cell ... ?view "schematic" ...)`; for Layout XL: `deOpen(list(nil ?lib ... ?cell ... ?view "layout") nil "a" "Layout XL")`), then perform all operations live in the visible window. Do not call `dbClose(cv)`. **Timeout Recovery**: A timeout leaves mutation state unknown; do not resend a mutating command. Inspect the cell/GUI and regain a `RESULT:` response with a read-only probe. **GUI Popups**: Form-dismissal calls are environment-specific and must only be used after confirming the form/dialog is present.
- `run_terminal_command`: Executes shell command in Virtuoso terminal environment.

---

## Tool 3: `eldo`
**Description**: Siemens Eldo analog simulation control, measurement retrieval, and waveform visualization.

### Interface Schema
```typescript
type EldoArgs = {
  action: "start_interactive" | "start"
        | "run_interactive" | "interactive"
        | "stop_interactive" | "stop"
        | "run_script" | "script"
        | "visualize_waveforms" | "visualize" | "plot"
        | "run_terminal_command" | "terminal" | "shell";
  command?: string;   // Netlist path, REPL command ('run', 'step'), SPICE output file path, or shell command
  file_path?: string; // Simulation output file path (.raw or .spi3) when action='visualize_waveforms'
  layout?: Array<{ pane_title: string; signals: string[] }>; // Signal layout config when action='visualize_waveforms'
  work_dir?: string;  // Default: "~/Desktop/eldo"
  timeout?: number;   // Default: 30.0s
};
```

### Action Modes
- `start_interactive`: Launches `eldo <netlist> -inter` interactive session.
- `run_interactive`: Sends simulation control command (`run`, `step`, `display`) to `eldo>` REPL.
- `stop_interactive`: Sends `quit` to active Eldo REPL session.
- `run_script`: Runs batch simulation deck.
- `visualize_waveforms` / `visualize` / `plot`: Spawns a multi-pane oscilloscope window to plot SPICE transient simulation outputs (`.raw` or `.spi3` files) using custom pane layout configurations.
- `run_terminal_command`: Executes shell command in Eldo terminal environment.

---

## Tool 4: `workboard`
**Description**: Git-backed local-remote workspace synchronization and version control.

### Interface Schema
```typescript
type WorkBoardArgs = {
  action: "initialize" | "add" | "export" | "pull" | "push" | "diff" | "status" | "history";
  workboard_name?: string; // Default: "default"
  remote_path?: string;    // Required for add/export
  local_path?: string;     // Relative local path in <workspace_root>/workboard/<name>/
  message?: string;        // Commit message for export/push (Default: "Agent sync")
  overwrite?: boolean;     // Default: false (protects existing remote file on export)
  timeout?: number;        // Default: 180.0s per SCP transfer (raise for large .chi/.spi3 files)
  workspace_root?: string; // Absolute project path; WorkBoards live in <workspace_root>/workboard/. Sticky per session.
};
```

### Action Modes & Auto-Advance Behavior
- Root resolution: `workspace_root` arg > `WORKBOARD_ROOT` env > MCP client root > EDA_MCP repo. See [`workboard_sync_guide.md`](workboard_sync_guide.md).
- `initialize`: Creates `<workspace_root>/workboard/<name>/` and runs `git init`.
- `add`: Downloads remote file via SCP, registers in `.workboard.json`, commits locally ($C_{\text{sync}} = \text{HEAD}$).
- `pull`: Re-fetches remote file, updates local WorkBoard, commits locally ($C_{\text{sync}} = \text{HEAD}$).
- `push`: Uploads local edits to remote server via SCP, commits locally ($C_{\text{sync}} = \text{HEAD}$).
- `diff`: Fetches remote bytes and compares with local file.
  - *If identical*: Updates `.workboard.json` sync baseline SHA to current local Git HEAD.
  - *If different*: Returns unified line-by-line diff.
- `status`: Returns tracked file table, sync baseline commit SHAs, and local git status.
- `history`: Returns local Git commit log (`git log`).

---

## Tool 5: `report_issue`
**Description**: Autonomous agent-to-agent GitHub issue & feature request reporting tool.

### Interface Schema
```typescript
type ReportIssueArgs = {
  title: string;           // Concise issue or feature request title
  body?: string;           // Freeform Markdown content (see issue_reporting_guide.md for suggestions)
  label?: string;          // Default: "bug" (e.g., "enhancement", "feature-request")
  agent_model?: string;    // Model identifier (e.g. "gemini-3.6-flash", "claude-3-5-sonnet")
  session_id?: string;     // Default: "unknown" (conversation turn ID)
};
```

### Auto-Behavior
- **Client Agent Auto-Detection**: Extracts `agent_name` (`Antigravity`, `claude-code`, `cursor`) from MCP `clientInfo` context via FastMCP `Context`.
- **Log Auto-Attachment**: Automatically references the active server log in `logs/eda_mcp_*.log`.
- **GitHub Label Auto-Creation**: Automatically matches existing labels (with typo/formatting tolerance) and creates missing labels on GitHub.
- **Form Suggestions**: For suggested Markdown body structure on bugs and enhancements, see [`issue_reporting_guide.md`](issue_reporting_guide.md).
