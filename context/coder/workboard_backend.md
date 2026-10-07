# WORKBOARD_BACKEND_SPEC

## 1. Directory Structure & Registry Schema ([`workboard_client.py`](../../src/clients/workboard_client.py))

### Path Binding
- Base Directory: `<workspace_root>/workboard/<workboard_name>/`
- Manifest File: `<workspace_root>/workboard/<workboard_name>/.workboard.json`
- Root resolution lives in `src/server.py::_resolve_workboard_root` and runs on every `workboard` call:
  `workspace_root` arg (sticky in `_workboard_explicit_root`) > `WORKBOARD_ROOT` env > MCP client `roots/list` (only if the client declares the roots capability, 5s cap) > `EDA_MCP/workboard`.
- `WorkBoardClient.set_workspace_root()` maps `<root>` to `<root>/workboard` (paths already named `workboard` are kept) and clears `active_workboard` when the root changes. `root_source` is shown in `status`.
- The MCP tool is `async`; SCP/git work runs in `anyio.to_thread.run_sync` (`_workboard_sync`). Callers such as `daemon.py` must `await workboard(...)`.

### `.workboard.json` Schema Structure
```json
{
  "workboard_name": "string",
  "local_root": "string",
  "created_at": "ISO-8601 string",
  "last_synced": "ISO-8601 string",
  "files": {
    "<rel_local_path>": {
      "remote_path": "string",
      "local_checksum": "SHA-256 string",
      "last_sync_commit": "Git SHA-1 short hash string",
      "last_sync_time": "ISO-8601 string",
      "is_directory": false
    }
  }
}
```

---

## 2. Git Subprocess Invocation (`_git_cmd`)
```python
cmd = ["git", "-c", "user.name=WorkBoard MCP", "-c", "user.email=mcp@workboard.local"] + args
```

---

## 3. `diff` Auto-Baseline Advancing Algorithm

```
                  diff(local_path)
                         │
                         ▼
        scp_client.read_bytes(remote_path)
                         │
                         ▼
             Compare local vs remote bytes
            ┌─────────────────┴─────────────────┐
            │                                   │
      local == remote                     local != remote
            │                                   │
            ▼                                   ▼
 Get HEAD commit SHA                 difflib.unified_diff()
 Update last_sync_commit                    │
 Update last_sync_time                      ▼
 Save .workboard.json               Return unified diff string
 git commit --amend / commit
            │
            ▼
 Return "No diff detected..."
```
