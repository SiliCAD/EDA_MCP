# MCP Server Reload Guide (`EDA_MCP`)

This guide outlines how to reload and restart the `EDA_MCP` server after code modifications, configuration updates, or environment changes.

---

## Why Reloading is Necessary

`EDA_MCP` is a FastMCP Python server executing over standard input/output (stdio JSON-RPC) as a long-running subprocess spawned by the AI host application (e.g., Antigravity IDE, `agy` CLI, Claude Desktop, Cursor, or VS Code).

Because Python loads modules into memory upon process initialization:
- Modifications to Python codebase files (`src/server.py`, `src/clients/*`, `src/core/*`, `config/*`) **do not auto-reload in existing sessions**.
- The in-memory process continues running previous bytecode until the process terminates and is re-spawned by the MCP host.

---

## Method 1: Process-Level Termination (Fastest & Most Reliable)

The fastest way to reload the server without restarting your entire IDE or terminal session is to terminate the running Python server process. The MCP host will automatically re-spawn a fresh instance on the next tool invocation.

### 1. Check Running MCP Server Processes
```bash
ps aux | grep -E "EDA_MCP/server\.py"
```

### 2. Terminate the Running Server
Kill by pattern match:
```bash
pkill -f "EDA_MCP/server.py"
```
Or kill specifically by Process ID (PID):
```bash
kill <PID>
# If process is unresponsive:
kill -9 <PID>
```

### 3. Automatic Recovery
Upon your next tool call (e.g., `remote_control`, `virtuoso`, `eldo`, or `workboard`), the MCP client/runner automatically launches a fresh Python process with the latest code loaded.

---

## Method 2: Antigravity IDE / Desktop UI Reload

If working within the Antigravity IDE or a graphical MCP client:

1. Open the MCP Servers management view:
   - Navigate to **Additional Options (`...`) > MCP Servers** (or open Command Palette with `Cmd+Shift+P` / `Ctrl+Shift+P` and type `MCP: View Servers`).
2. Locate **`eda-mcp`** in the configured server list.
3. Click the **Reload / Restart** icon (or toggle the server **Off** and back **On**).
4. Check the status indicator turns green (`Connected`).

---

## Method 3: Antigravity CLI (`agy`) Session Restart

When using the Antigravity CLI (`agy`):
- Starting a new session automatically initializes fresh MCP server connections:
  ```bash
  agy
  ```
- Alternatively, reconnecting or resuming with `agy --conversation=<id>` will establish connections to the configured MCP servers.

---

## Method 4: Reloading Remote Server-Side EDA Scripts

When you modify remote server-side scripts (such as Virtuoso SKILL files or shell scripts in `server_side/virtuoso/`):

### 1. Dynamic SKILL Reload (Inside Active Virtuoso Session)
You do not need to restart the entire MCP server or Virtuoso session to update SKILL procedures. Re-load the script directly into the running session:

- In `assisted_run`:
  ```python
  virtuoso(action="assisted_run", command='load("MCP_setup.il")')
  ```
- In `standalone`:
  ```python
  virtuoso(action="standalone", command='load("MCP_setup.il")')
  ```

### 2. Complete Virtuoso Session Restart
If you modified Virtuoso initialization files (`MCP_initialize.sh`, environment variables, or display settings) or need a clean session:
```python
# 1. Terminate existing session
virtuoso(action="exit")

# 2. Launch fresh session on next command
virtuoso(action="assisted_run", command='printf("Virtuoso re-initialized\\n")')
```

---

## Method 5: Background HTTP Gateway Daemon (`daemon.py`)

If you are running the persistent FastAPI background gateway (`daemon.py` on port `8765`) for multi-agent coordination:

```bash
# 1. Stop the running daemon
pkill -f "daemon.py"

# 2. Restart daemon in background
nohup /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 daemon.py > logs/daemon.log 2>&1 &

# 3. Verify health endpoint
curl -s http://127.0.0.1:8765/health
```

---

## Verification & Post-Reload Diagnostics

After reloading the MCP server, verify that the new process is healthy and functioning:

1. **Inspect the latest log file**:
   ```bash
   ls -lt logs/eda_mcp_*.log | head -n 1
   tail -n 30 logs/eda_mcp_<timestamp>_<pid>.log
   ```
2. **Execute a non-mutating sanity check**:
   - `remote_control:run_command("echo 'MCP RELOAD OK'")`
   - `virtuoso:standalone("printf(\"SKILL ENGINE READY\\n\")")`
3. **Run local test suite**:
   ```bash
   python3 -m unittest discover tests
   ```
