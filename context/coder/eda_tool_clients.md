# EDA_TOOL_CLIENTS_SPEC

## 1. Cadence Virtuoso Client ([`virtuoso_client.py`](../../src/clients/virtuoso_client.py))

### Assisted Run FIFO Pipe IPC State Machine
```
   [Agent SKILL Code]
          │
          ▼
   _clean_skill_command() (Strips ';;' comments)
          │
          ▼
   rm -f mcp_output.txt && touch mcp_output.txt
          │
          ▼
   echo "<clean_skill>" > MCP.command (Writes to FIFO)
          │
          ▼
   Polling Loop (Interval: 0.3s, Timeout: 30.0s)
   read_file("mcp_output.txt") until "RESULT:" appears
> **Command Length & Error Handling Contract**: `assisted_run` SKILL commands are written directly to `MCP.command` FIFO via shell `echo` (keep short/concise; use `load("file.il")` for large scripts). Server-side [`MCP_setup.il`](../../server_side/virtuoso/MCP_setup.il) wraps `evalstring` in `errset` and `unwindProtect` to catch SKILL exceptions, write `RESULT: ERROR ...`, and restore ports without timing out.
> **Cross-Process Concurrency Protection**: `assisted_run` acquires an OS-level `FileLock("/tmp/virtuoso_fifo.lock")` to prevent race conditions or pipe corruption when multiple external automation scripts, daemon requests, or agent instances invoke SKILL commands simultaneously.


### Standalone REPL Mode
- `start_standalone(work_dir)`: Sends `virtuoso -nograph` via `execute_interactive_stream()` matching `(>\s*$|\bCIW>\s*$)`.
- `run_standalone(command)`: Sends `_clean_skill_command(command)` via `execute_interactive_stream()`.
- `stop_standalone()`: Sends `exit()` to Virtuoso REPL stream.

---

## 2. Siemens Eldo Client ([`eldo_client.py`](../../src/clients/eldo_client.py))

### Interactive REPL Mode (`eldo -inter`)
- `start_interactive(netlist_file, work_dir)`: Sends `eldo <netlist_file> -inter` via `execute_interactive_stream()` matching `(eldo>\s*$|\bELDO>\s*$)`.
- `run_interactive(command)`: Sends REPL control command (`run`, `step`, `display`) via `execute_interactive_stream()`.
- `stop_interactive()`: Sends `quit` to Eldo REPL stream.
