# Observer port

A plug-in point that lets an outside service watch every EDA_MCP tool call and
talk back to the agent. The watcher itself lives outside this repo (AnalogMind
`watcher/`); EDA_MCP only knows the protocol below.

## Plugging in

| Env var | Default | Meaning |
|---|---|---|
| `EDA_MCP_OBSERVER_URL` | unset | Base URL of the observer, e.g. `http://127.0.0.1:8770`. Unset = port off, tools unchanged. |
| `EDA_MCP_OBSERVER_TIMEOUT` | `0.5` | Seconds per hook call. A slower answer is ignored. |
| `EDA_MCP_OBSERVER_SESSION` | `eda-mcp:<pid>` | Session name the observer sees. One stdio server runs per agent, so the pid tells agents apart. |

Set them in the `env` block of the `eda-mcp` server in the agent's MCP config.
The daemon (`daemon.py`) reports its calls with `source: "daemon"`.

## What changes for the agent

- `virtuoso`, `eldo`, `remote_control` and `workboard` take two optional
  arguments: `stage` (`schematic`, `sim`, `floorplan`, `route`, `drc`, `lvs`,
  `pex`, `tool_problem`, `other`) and `why` (one short line).
- A result may end with a notice block:
  ```text
  [harness_notice] from the AnalogMind watcher (guidance from the user):
  - (warn) probe once, then ask the user
  ```
- The observer may block a call before it runs. The result then starts with
  `Error: Blocked by the observer, the command was NOT executed.` and the reason.

## Protocol (v1)

Both hooks are `POST` with a JSON body and expect a JSON answer.

`/v1/before` runs before the tool body:
```json
{"v": 1, "call_id": "hex", "session": "eda-mcp:4242", "source": "mcp",
 "tool": "virtuoso", "action": "assisted_run",
 "args": {"command": "...", "work_dir": "~/Desktop/cmos65"},
 "stage": "schematic", "why": "wire the mirror", "ts": 1761370000.0}
```
Answer: `{"decision": "allow" | "block", "message": "why blocked", "notices": [{"severity": "hint|warn|block", "text": "..."}]}`

`/v1/after` runs after it, with the same `call_id` plus:
```json
{"duration_s": 3.2, "result_head": "first 2000 chars", "result_len": 18000}
```
Answer: `{"notices": [...]}`

String arguments are capped at 4000 characters; `remote_control` sends
`content_len` instead of the file content.

## Failure behaviour

The port fails open. A refused connection, a timeout, a non-JSON answer or an
unknown `decision` all mean "allow, no notices". Errors are logged at most once
a minute. A blocked call never reaches SSH, Virtuoso or Eldo.

Code: `src/core/observer.py`, wired in `src/server.py` (`_observed`,
`_observed_async`). Tests: `tests/test_observer_port.py`.
