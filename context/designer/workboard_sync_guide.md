# WORKBOARD_SYNC_SPEC

## 1. Local-Remote Workspace Mapping
- **Local WorkBoard Root**: `<workspace_root>/workboard/<workboard_name>/`
- **Registry File**: `<workspace_root>/workboard/<workboard_name>/.workboard.json`
- **Sync Baseline**: `last_sync_commit` (SHA of local Git commit at last synchronized state $C_{\text{sync}}$)

### Workspace Root Resolution
The MCP server runs from its own repository, so `./workboard/` is NOT automatically your project folder. `<workspace_root>` is resolved per call in this order:

| Priority | Source | Notes |
| :--- | :--- | :--- |
| 1 | `workspace_root` argument | Absolute path to your project. Remembered for all later `workboard` calls in this server session. Must be an existing directory. |
| 2 | `WORKBOARD_ROOT` env var | Set in the MCP server launch config. |
| 3 | MCP client workspace root | Used automatically if your client advertises roots. |
| 4 | EDA_MCP server repo | Legacy fallback; `status` shows `Root Source: server default ...`. |

**Rule**: On the first `workboard` call of a session, pass `workspace_root="<absolute path of your project>"`. Then check `Local Root` / `Root Source` in the result. Paths ending in `/workboard` are used as-is (no extra `workboard/` is appended). Changing the root clears the remembered active WorkBoard, so pass `workboard_name` again.

Every `add`/`export`/`pull`/`push` result prints `Local file: <absolute path>`; use that path to read/edit the file.

```text
workboard(action="status", workspace_root="/Users/me/AnalogMind", workboard_name="inverter_sim")
```

`local_path` is relative to the selected WorkBoard root, not an arbitrary workspace path. To create a new simulation deck, first initialize/select a board, then create the file at `./workboard/<workboard_name>/<local_path>` before calling `export`.

### Local Deck Authoring Protocol
To write `<workspace_root>/workboard/<name>/tb_<cell>.cir`:
- Use `write_to_file` WITHOUT `ArtifactMetadata` (ArtifactMetadata is strictly for artifact directory files; passing it for workspace files causes validation errors).
- Alternatively, write `./workboard/<name>/tb_<cell>.txt` then run `mv ./workboard/<name>/tb_<cell>.txt ./workboard/<name>/tb_<cell>.cir`.
- Export: `workboard(action="export", workboard_name="<name>", local_path="tb_<cell>.cir", remote_path="~/Desktop/eldo/tb_<cell>.cir")`.

Example lifecycle:

```text
workboard(action="initialize", workboard_name="inverter_sim", workspace_root="/abs/path/to/project")
# write ./workboard/inverter_sim/tb_inverter.txt -> mv to tb_inverter.cir
workboard(action="export", workboard_name="inverter_sim",
          local_path="tb_inverter.cir", remote_path="~/Desktop/eldo/tb_inverter.cir")
```

When more than one WorkBoard exists, pass `workboard_name` on every operation unless the current server session has already selected one. That selection is session-local; do not assume it persists across MCP server restarts.

---

## 2. Action State Matrix

| Action | Target Input | Local Git Effect | Sync Baseline ($C_{\text{sync}}$) |
| :--- | :--- | :--- | :--- |
| `initialize` | `workboard_name` | `git init`, write `.gitignore` | Created |
| `add` | `remote_path`, `local_path` | Download via SCP, `git commit` | Updated to `HEAD` |
| `pull` | `local_path` | Re-download via SCP, `git commit` | Advanced to `HEAD` |
| `push` | `local_path` | Upload via SCP, `git commit` | Advanced to `HEAD` |
| `diff` | `local_path` | Compare local vs remote bytes | Auto-advanced if 100% match |
| `status` | None | Read-only state report | Read-only |
| `history` | `local_path` | `git log -n 10` execution | Read-only |

---

## 3. Native Git Shell Navigation Commands
Agent can execute terminal commands inside `<workspace_root>/workboard/<name>/`:
- Commit log: `git log -n 10 --oneline -- <local_path>`
- Baseline state view: `git show <commit_sha>:<local_path>`
- Revert file to baseline: `git checkout <commit_sha> -- <local_path>`
- Diff baselines: `git diff <commit_sha_1> <commit_sha_2> -- <local_path>`

---

## 4. Local Tooling & Sizing Computation Authorization
- Agents may use local tools to calculate transistor aspect ratios ($W/L$), evaluate equations, analyze retrieved results, and author **simulation decks**. Structural transistor netlists must come from the verified Virtuoso exporter, not local reconstruction.

---

## 5. File Encoding & Non-UTF8 Character Handling
- EDA tool outputs (such as Calibre DRC summary decks, `.chi` Eldo log files, or `.db` reports) frequently contain Latin-1 / ISO-8859-1 encoded characters (e.g. byte `0xb5` representing `µm`).
- All WorkBoard diff, read, and pull operations automatically decode files using UTF-8 with fallback replacement (`errors="replace"`) to prevent decoder crashes (`UnicodeDecodeError`).
- When authoring local simulation decks or inspecting report files, ensure non-ASCII symbols use standard ASCII units (`um`, `ns`, `mV`) where required by EDA tool syntax.
