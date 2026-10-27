"""
Observer port: lets an external service watch EDA_MCP tool calls and talk back.

Plug and play. When EDA_MCP_OBSERVER_URL is unset, every hook is a no-op and the
tools behave exactly as before. When it is set, each tool call makes two local
HTTP calls to the observer:

  POST <url>/v1/before   the call about to run  -> {"decision": "allow"|"block",
                                                     "message": str, "notices": [...]}
  POST <url>/v1/after    the call and its result -> {"notices": [...]}

A risky call may be answered "hold" instead (the before event says caps ["hold"]): the client then
POSTs <url>/v1/verdict and waits up to hold_s for allow / block. Only that wait fails closed.

Notices are appended to the tool result as a short "[harness_notice]" block, so the
agent reads them with the result. The port fails open: an unreachable, slow or
malformed observer never blocks or breaks a tool call. Protocol: doc/observer_port.md.
"""
import contextvars
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
CAPS = ["hold"]               # answers this client understands beyond allow / block
HOLD_MAX_S = 120.0            # longest a held call waits for its verdict
HOLD_DEFAULT_S = 20.0
VERDICT_MARGIN_S = 5.0        # the verdict request's HTTP timeout is hold_s + this
VERDICT_UNAVAILABLE = "watcher verdict unavailable; ask the user before sending it again"

# The caller's own observed call (e.g. an Arsenal tool) that this daemon request runs for
_parent_call_id: contextvars.ContextVar[str] = contextvars.ContextVar("observer_parent_call_id", default="")


def set_parent_call(call_id: str):
    """Tags the events of the calls that follow in this context with parent_call_id; returns the reset token."""
    return _parent_call_id.set(call_id or "")


def reset_parent_call(token) -> None:
    _parent_call_id.reset(token)


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
    def _request(self, path: str, payload: dict, timeout: float) -> dict:
        """The observer's JSON object answer; raises on a transport error or a non-object answer."""
        req = urllib.request.Request(
            self.url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8") or "{}")
        if not isinstance(body, dict):
            raise ValueError(f"answer is not a JSON object: {body!r:.80}")
        return body

    def _post(self, path: str, payload: dict) -> dict:
        """Fails open: any error means an empty answer (allow, no notices)."""
        try:
            return self._request(path, payload, self.timeout)
        except (urllib.error.URLError, OSError, ValueError) as e:
            now = time.time()
            if now - self._last_error_log > 60:   # don't flood the log while the observer is down
                logger.warning(f"[OBSERVER] {path} failed ({e}); continuing without the observer")
                self._last_error_log = now
            return {}

    def _verdict(self, call_id: str, tool: str, action: str, hold_s: float):
        """
        Waits for the verdict on a held call. Returns (block_message or "", notices).
        Fails closed: no usable verdict means block.
        """
        logger.info(f"[OBSERVER] {tool}.{action} held for the verifier's verdict (up to {hold_s:.0f} s)")
        start = time.time()
        try:
            resp = self._request("/v1/verdict", {"v": PROTOCOL_VERSION, "call_id": call_id, "wait_s": hold_s},
                                 hold_s + VERDICT_MARGIN_S)
        except (urllib.error.URLError, OSError, ValueError) as e:
            logger.warning(f"[OBSERVER] verdict for {tool}.{action} unavailable ({e}); not running it")
            return VERDICT_UNAVAILABLE, []
        decision = resp.get("decision")
        notices = _clean_notices(resp.get("notices"))
        logger.info(f"[OBSERVER] verdict for {tool}.{action} after {time.time() - start:.1f} s: {decision}")
        if decision == "allow":
            return "", notices
        if decision == "block":
            return str(resp.get("message") or "Blocked by the verifier."), notices
        return VERDICT_UNAVAILABLE, notices

    # ------------------------------------------------------------ hooks
    def _event(self, call_id: str, tool: str, action: str, args: dict, stage: str, why: str) -> dict:
        clipped = {k: (v[:ARG_CHARS] if isinstance(v, str) else v) for k, v in args.items()}
        event = {"v": PROTOCOL_VERSION, "call_id": call_id, "session": self.session, "source": self.source,
                 "tool": tool, "action": action, "args": clipped, "stage": stage, "why": why, "ts": time.time()}
        parent = _parent_call_id.get()
        if parent:
            event["parent_call_id"] = parent
        return event

    def before(self, tool: str, action: str, args: dict, stage: str = "", why: str = ""):
        """Returns (call_id, block_message or "", notices)."""
        call_id = uuid.uuid4().hex
        if not self.enabled:
            return call_id, "", []
        resp = self._post("/v1/before", dict(self._event(call_id, tool, action, args, stage, why), caps=CAPS))
        notices = _clean_notices(resp.get("notices"))
        if resp.get("decision") == "hold":
            block_msg, more = self._verdict(call_id, tool, action, _hold_seconds(resp.get("hold_s")))
            if block_msg:
                logger.warning(f"[OBSERVER] blocked {tool}.{action} after the hold: {block_msg}")
            return call_id, block_msg, notices + more
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


def _hold_seconds(raw) -> float:
    try:
        hold_s = float(raw)
    except (TypeError, ValueError):
        return HOLD_DEFAULT_S
    return min(max(hold_s, 0.0), HOLD_MAX_S) if hold_s == hold_s else HOLD_DEFAULT_S     # NaN -> default


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
