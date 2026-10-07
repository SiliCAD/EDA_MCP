import os
import re
import json
import time
import shlex
import logging
import posixpath
from typing import List, Optional, Tuple

logger = logging.getLogger("eda_mcp.command_guard")

DEFAULT_ALLOWED_DIRS = ["~/Desktop/cmos65", "~/Desktop/eldo", "/tmp"]

# Always blocked, regardless of target paths.
BLOCKED_PATTERNS: List[Tuple[str, str]] = [
    (r"\bmkfs(\.\w+)?\b", "filesystem formatting (mkfs)"),
    (r"\bdd\b[^;&|]*\bof=/dev/", "raw disk overwrite (dd of=/dev/...)"),
    (r">\s*/dev/(sd|hd|nvme|disk|xvd)", "redirect onto a raw disk device"),
    (r"(^|[;&|(]\s*|\bsudo\s+)(shutdown|reboot|halt|poweroff)\b", "host shutdown / reboot"),
    (r"\bkill\s+(-\w+\s+)*-?1\b(?!\d)", "signal to PID 1 / all processes"),
    (r"\bchmod\b[^;&|]*\b777\b", "world-writable permissions (chmod 777)"),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}", "fork bomb"),
]

# Commands that modify or delete their path arguments.
DESTRUCTIVE_CMDS = {"rm", "rmdir", "unlink", "shred", "truncate", "mv", "chmod", "chown", "chgrp", "tee", "cp", "ln"}
# For these, only the last path argument (the destination) is written.
DEST_ONLY_CMDS = {"mv", "cp", "ln"}
# Leading wrappers that don't change what the command does.
PREFIX_WORDS = {"sudo", "nohup", "time", "command", "builtin", "exec", "env", "nice"}
# Shells / eval whose string argument is itself a command line to check.
NESTED_SHELLS = {"sh", "bash", "csh", "tcsh", "zsh", "ksh"}

SEPARATORS = {";", "&&", "||", "|", "&", "\n", "(", ")"}
REDIRECTS = {">", ">>", ">|", "&>", "&>>", ">>&", ">&"}


class CommandGuard:
    """
    Pre-execution safety check for shell commands sent to the remote EDA server (issue #55).
    Blocks known-catastrophic commands outright, and requires every path written or deleted
    by a destructive command (rm, mv, chmod, redirects, ...) to sit inside an allowed directory.
    """

    def __init__(self, allowed_dirs: Optional[List[str]] = None, enabled: bool = True, audit_log_path: str = ""):
        self.allowed_dirs = [self._norm(d) for d in (allowed_dirs or DEFAULT_ALLOWED_DIRS)]
        self.enabled = enabled
        self.audit_log_path = audit_log_path

    @classmethod
    def from_config(cls, config_path: str = "", audit_log_path: str = "") -> "CommandGuard":
        """
        Loads settings from config JSON ({"enabled": bool, "allowed_dirs": [...]}),
        overridden by EDA_MCP_COMMAND_GUARD=off and EDA_MCP_GUARD_ALLOWED_DIRS (colon-separated).
        """
        enabled, allowed = True, list(DEFAULT_ALLOWED_DIRS)
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                enabled = bool(cfg.get("enabled", True))
                allowed = cfg.get("allowed_dirs") or allowed
            except Exception as e:
                logger.error(f"Failed to read command guard config {config_path}: {e}")
        env_flag = os.environ.get("EDA_MCP_COMMAND_GUARD", "").strip().lower()
        if env_flag in ("0", "off", "false", "disabled"):
            enabled = False
        env_dirs = os.environ.get("EDA_MCP_GUARD_ALLOWED_DIRS", "").strip()
        if env_dirs:
            allowed = [d for d in env_dirs.split(":") if d.strip()]
        return cls(allowed_dirs=allowed, enabled=enabled, audit_log_path=audit_log_path)

    # ---------- path helpers ----------

    @staticmethod
    def _norm(path: str) -> str:
        """Normalizes a remote path, keeping '~' symbolic (remote $HOME is unknown locally)."""
        p = path.strip()
        if p in ("$HOME", "${HOME}"):
            p = "~"
        elif p.startswith("$HOME/") or p.startswith("${HOME}/"):
            p = "~/" + p.split("/", 1)[1]
        if p == "~" or p.startswith("~/"):
            rest = posixpath.normpath("/" + p[1:].lstrip("/"))
            return "~" if rest == "/" else "~" + rest
        return posixpath.normpath(p) if p.startswith("/") else p

    def _resolve(self, path: str, cwd: Optional[str]) -> Optional[str]:
        """Absolute normalized path, or None when it can't be determined (relative with unknown cwd)."""
        p = self._norm(path)
        if p == "~" or p.startswith("~/") or p.startswith("/"):
            return p
        if cwd is None:
            return None
        return self._norm(posixpath.join(cwd, p))

    def _containing_root(self, path: str) -> Optional[str]:
        for root in self.allowed_dirs:
            if path == root or path.startswith(root.rstrip("/") + "/"):
                return root
        return None

    def _check_target(self, raw: str, cwd: Optional[str], deleting: bool, what: str) -> Optional[str]:
        """Returns a block reason for one written/deleted path, or None if it is allowed."""
        if "$(" in raw or "`" in raw or re.search(r"\$(?!HOME\b|\{HOME\})", raw):
            shown = raw.replace("$SUBSHELL", "$(...)")
            return f"{what} target '{shown}' uses shell expansion that can't be verified before running"
        path = self._resolve(raw, cwd)
        if path is None:
            return (f"{what} target '{raw}' is a relative path and the remote working directory is unknown; "
                    f"use an absolute path or 'cd <allowed dir> && ...' in the same command")
        root = self._containing_root(path)
        if root is None:
            return f"{what} target '{path}' is outside the allowed directories ({', '.join(self.allowed_dirs)})"
        if deleting:
            if path == root:
                return f"{what} would delete the allowed root directory '{root}' itself"
            first_level = path[len(root.rstrip('/')) + 1:].split("/", 1)[0]
            if any(ch in first_level for ch in "*?["):
                return f"{what} target '{raw}' wildcards the top level of '{root}'; name the specific sub-directory"
        return None

    # ---------- command parsing ----------

    @staticmethod
    def _split_segments(command: str) -> List[List[str]]:
        text = command.replace("\r", "\n").replace("\n", " ; ")
        text = re.sub(r"\$\([^()]*\)|`[^`]*`", "$SUBSHELL", text)  # keep command substitution as one token
        text = re.sub(r"(?<![\w/])\d+(?=>)", " ", text)       # drop fd numbers: 2>file -> >file
        text = re.sub(r">&\s*\d+\b", " ", text)               # fd duplication: 2>&1 writes no file
        lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        segments, current = [], []
        for tok in lexer:
            if tok in SEPARATORS or (set(tok) <= set(";&|") and tok not in REDIRECTS):
                if current:
                    segments.append(current)
                current = []
            else:
                current.append(tok)
        if current:
            segments.append(current)
        return segments

    def validate(self, command: str, cwd: Optional[str] = None) -> Tuple[bool, str]:
        """
        Returns (is_safe, reason). 'cwd' is the remote directory the command starts in when the
        caller knows it (e.g. tools that 'cd <work_dir>' first); relative paths resolve against it.
        """
        if not self.enabled:
            return True, "Command guard disabled"
        text = command.strip()
        if not text:
            return True, "Empty command"

        for pattern, label in BLOCKED_PATTERNS:
            if re.search(pattern, text):
                return False, f"Blocked: {label}"

        try:
            segments = self._split_segments(text)
        except ValueError as e:
            return False, f"Blocked: command could not be parsed safely ({e})"

        cwd = self._resolve(cwd, None) if cwd else None
        for seg in segments:
            # Output redirections anywhere in the segment write to their target.
            args: List[str] = []
            i = 0
            while i < len(seg):
                tok = seg[i]
                if tok in REDIRECTS:
                    if i + 1 < len(seg):
                        target = seg[i + 1]
                        if target != "/dev/null" and not target.startswith("&"):
                            reason = self._check_target(target, cwd, deleting=False, what="Redirect")
                            if reason:
                                return False, f"Blocked: {reason}"
                    i += 2
                    continue
                if tok in ("<", "<<", "<<<"):
                    i += 2
                    continue
                args.append(tok)
                i += 1

            via_xargs = False
            while args and (args[0] in PREFIX_WORDS or args[0] == "xargs" or re.match(r"^\w+=", args[0])):
                via_xargs = via_xargs or args[0] == "xargs"
                args = args[1:]
                while args and args[0].startswith("-") and args[0] != "-":
                    args = args[1:]
            if not args:
                continue

            cmd = posixpath.basename(args[0])
            operands = [a for a in args[1:] if not a.startswith("-")]

            if cmd == "eval" or (cmd in NESTED_SHELLS and "-c" in args):
                inner = " ".join(args[1:]) if cmd == "eval" else (args[args.index("-c") + 1] if args.index("-c") + 1 < len(args) else "")
                ok, reason = self.validate(inner)
                if not ok:
                    return False, f"{reason} (inside {cmd})"
                continue

            if via_xargs and cmd in DESTRUCTIVE_CMDS:
                return False, f"Blocked: '{cmd}' via xargs takes its targets from input that can't be verified before running"

            if cmd == "cd":
                target = operands[0] if operands else "~"
                resolved = None if ("$(" in target or "`" in target) else self._resolve(target, cwd)
                cwd = resolved
                continue

            if cmd == "find" and ("-delete" in args or "-exec" in args):
                roots = [a for a in args[1:] if not a.startswith("-") and not a.startswith("(")][:1] or ["."]
                reason = self._check_target(roots[0], cwd, deleting=True, what="find -delete/-exec")
                if reason:
                    return False, f"Blocked: {reason}"
                continue

            if cmd not in DESTRUCTIVE_CMDS:
                continue

            if cmd in ("chmod", "chown", "chgrp") and operands:
                operands = operands[1:]  # first operand is the mode / owner
            if cmd in DEST_ONLY_CMDS:
                operands = operands[-1:]
            if cmd == "mv":
                srcs = [a for a in args[1:] if not a.startswith("-")][:-1]
                operands = srcs + operands  # moving a file away also removes it from its source

            deleting = cmd in ("rm", "rmdir", "unlink", "shred", "mv")
            for op in operands:
                reason = self._check_target(op, cwd, deleting=deleting, what=cmd)
                if reason:
                    return False, f"Blocked: {reason}"

        return True, "Allowed"

    def check_write_path(self, path: str) -> Tuple[bool, str]:
        """Validates a direct remote file write (remote_control write_file)."""
        if not self.enabled:
            return True, "Command guard disabled"
        reason = self._check_target(path, None, deleting=False, what="write_file")
        return (False, f"Blocked: {reason}") if reason else (True, "Allowed")

    # ---------- audit ----------

    def audit(self, tool: str, command: str, allowed: bool, reason: str, dry_run: bool = False):
        """Appends one JSON line per guarded command to the audit log."""
        if not self.audit_log_path:
            return
        entry = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "tool": tool,
            "command": command,
            "decision": "allowed" if allowed else "blocked",
            "dry_run": dry_run,
            "reason": reason,
        }
        try:
            os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write command audit log: {e}")

    def blocked_message(self, reason: str) -> str:
        return (
            f"Error: {reason}\n"
            f"The command was NOT executed. Destructive operations are only allowed inside: {', '.join(self.allowed_dirs)}.\n"
            f"If this operation is genuinely required, ask the human user to run it or to adjust config/command_guard.json."
        )
