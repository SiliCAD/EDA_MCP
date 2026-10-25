"""
Observer port: lets an external service watch EDA_MCP tool calls and talk back.

Plug and play. When EDA_MCP_OBSERVER_URL is unset, every hook is a no-op and the
tools behave exactly as before. When it is set, each tool call makes two local
HTTP calls to the observer:

  POST <url>/v1/before   the call about to run  -> {"decision": "allow"|"block",
                                                     "message": str, "notices": [...]}
  POST <url>/v1/after    the call and its result -> {"notices": [...]}

Notices are appended to the tool result as a short "[harness_notice]" block, so the
agent reads them with the result. The port fails open: an unreachable, slow or
malformed observer never blocks or breaks a tool call. Protocol: doc/observer_port.md.
"""
import json
import logging
import os
import time
import uuid
import urllib.error
import urllib.request

logger = logging.getLogger("EDA_MCP")

PROTOCOL_VERSION = 1
RESULT_HEAD_CHARS = 2000      # how much of the tool result the observer sees
ARG_CHARS = 4000              # per-argument cap on what is sent
NOTICE_HEADER = "[harness_notice] from the AnalogMind watcher (guidance from the user):"


class ObserverPort:
    def __init__(self, url: str = "", timeout: float = 0.5, session: str = "", source: str = "mcp"):
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.session = session or f"eda-mcp:{os.getpid()}"
        self.source = source
        self._last_error_log = 0.0

    @classmethod
    def from_env(cls, source: str = "mcp") -> "ObserverPort":
        url = os.environ.get("EDA_MCP_OBSERVER_URL", "").strip()
        try:
            timeout = float(os.environ.get("EDA_MCP_OBSERVER_TIMEOUT", "0.5"))
        except ValueError:
            timeout = 0.5
        return cls(url=url, timeout=timeout, session=os.environ.get("EDA_MCP_OBSERVER_SESSION", ""), source=source)

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    # ------------------------------------------------------------ transport
    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            self.url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8") or "{}")
                return body if isinstance(body, dict) else {}
        except (urllib.error.URLError, OSError, ValueError) as e:
            now = time.time()
            if now - self._last_error_log > 60:   # don't flood the log while the observer is down
                logger.warning(f"[OBSERVER] {path} failed ({e}); continuing without the observer")
                self._last_error_log = now
            return {}

    # ------------------------------------------------------------ hooks
    def _event(self, call_id: str, tool: str, action: str, args: dict, stage: str, why: str) -> dict:
        clipped = {k: (v[:ARG_CHARS] if isinstance(v, str) else v) for k, v in args.items()}
        return {"v": PROTOCOL_VERSION, "call_id": call_id, "session": self.session, "source": self.source,
                "tool": tool, "action": action, "args": clipped, "stage": stage, "why": why, "ts": time.time()}

    def before(self, tool: str, action: str, args: dict, stage: str = "", why: str = ""):
        """Returns (call_id, block_message or "", notices)."""
        call_id = uuid.uuid4().hex
        if not self.enabled:
            return call_id, "", []
        resp = self._post("/v1/before", self._event(call_id, tool, action, args, stage, why))
        notices = _clean_notices(resp.get("notices"))
        if resp.get("decision") == "block":
            msg = str(resp.get("message") or "Blocked by the observer.")
            logger.warning(f"[OBSERVER] blocked {tool}.{action}: {msg}")
            return call_id, msg, notices
        return call_id, "", notices

    def after(self, call_id: str, tool: str, action: str, args: dict, result: str, duration: float,
              stage: str = "", why: str = "") -> list:
        if not self.enabled:
            return []
        event = self._event(call_id, tool, action, args, stage, why)
        event.update({"duration_s": round(duration, 3), "result_head": (result or "")[:RESULT_HEAD_CHARS],
                      "result_len": len(result or "")})
        return _clean_notices(self._post("/v1/after", event).get("notices"))


def _clean_notices(raw) -> list:
    out = []
    for n in raw or []:
        if isinstance(n, dict) and str(n.get("text", "")).strip():
            out.append({"severity": str(n.get("severity", "hint")), "text": str(n["text"]).strip()})
    return out


def append_notices(result: str, notices: list) -> str:
    """Adds the notices to a tool result; returns the result unchanged when there are none."""
    if not notices:
        return result
    seen, lines = set(), []
    for n in notices:
        key = (n["severity"], n["text"])
        if key not in seen:
            seen.add(key)
            lines.append(f"- ({n['severity']}) {n['text']}")
    return f"{result}\n\n{NOTICE_HEADER}\n" + "\n".join(lines)


def blocked_result(message: str) -> str:
    return f"Error: Blocked by the observer, the command was NOT executed.\n{message}"
