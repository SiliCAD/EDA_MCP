import os
import subprocess
import shlex
import logging
import re
import difflib
import random
import json
from typing import Dict, Any, Optional, List

logger = logging.getLogger("EDA_MCP.IssueReporter")

class IssueReporter:
    """
    Helper utility for Agent A (Chip Design Consumer) to report tool issues, 
    bugs, or feature requests to GitHub without needing context of EDA_MCP code.
    """

    @staticmethod
    def format_issue_body(
        body: str = "",
        label: str = "bug",
        agent_model: str = "",
        session_id: str = "unknown",
        agent_name: str = "unknown",
        log_file: str = ""
    ) -> str:
        """Formats a simple GitHub issue body with metadata banner."""
        clean_log = log_file.strip() if log_file else ""
        if clean_log:
            log_file_str = clean_log if ("logs/" in clean_log or "logs\\" in clean_log or "temp/" in clean_log or "temp\\" in clean_log) else f"logs/{clean_log}"
            log_line = f"`{log_file_str}` (created in `logs/` folder)"
        else:
            log_line = "Created in `logs/` folder (`logs/eda_mcp_*.log`)"

        model_str = f" (`{agent_model.strip()}`)" if (agent_model and agent_model.strip()) else ""

        header_parts = [
            f"> **Reported by Agent:** {agent_name}{model_str} (Chip Design Consumer)",
            f"> **Session ID:** `{session_id}`",
            f"> **MCP Log File:** {log_line}",
            "---",
            ""
        ]

        content = body.strip() if (body and body.strip()) else "No issue content provided."
        return "\n".join(header_parts) + content

    @staticmethod
    def normalize_label_text(text: str) -> str:
        """
        Normalizes label string for typography-insensitive comparison:
        replaces hyphens, underscores, dots, slashes, and redundant spaces with single spaces,
        and converts to lowercase.
        """
        return re.sub(r'[\s_\-\.\/]+', ' ', text.strip()).lower()

    @staticmethod
    def clean_alphanumeric(text: str) -> str:
        """Strips all non-alphanumeric characters and converts to lowercase."""
        return re.sub(r'[^a-z0-9]', '', text.lower())

    @staticmethod
    def generate_random_color() -> str:
        """Generates a random 6-character hex color code for GitHub labels (without leading #)."""
        return f"{random.randint(0, 0xFFFFFF):06x}"

    @classmethod
    def get_existing_labels(cls, cwd: Optional[str] = None) -> List[str]:
        """Fetches all existing label names from the GitHub repository."""
        try:
            # Fast path: JSON output
            cmd = ["gh", "label", "list", "--limit", "500", "--json", "name"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd)
            data = json.loads(res.stdout)
            return [item["name"] for item in data if isinstance(item, dict) and "name" in item]
        except Exception as e:
            logger.debug(f"JSON label list failed ({e}), falling back to plain text parsing")
            try:
                # Fallback path: plain TSV output
                cmd = ["gh", "label", "list", "--limit", "500"]
                res = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd)
                labels = []
                for line in res.stdout.splitlines():
                    parts = line.split('\t')
                    if parts and parts[0].strip():
                        labels.append(parts[0].strip())
                return labels
            except Exception as e2:
                logger.warning(f"Failed to fetch GitHub labels: {e2}")
                return []

    @classmethod
    def find_matching_label(cls, target: str, existing_labels: List[str]) -> Optional[str]:
        """
        5-tier matching evaluation cascade:
        1. Exact match (case-sensitive)
        2. Case-insensitive match (e.g. 'BUG' -> 'bug')
        3. Separator/delimiter normalized match (e.g. 'new_lable' <-> 'new lable')
        4. Pure alphanumeric match (ignores all punctuation and delimiters)
        5. Fuzzy match for minor typos via SequenceMatcher (ratio >= 0.82)
        """
        if not target or not target.strip():
            return None

        clean_target = target.strip()
        target_lower = clean_target.lower()
        target_norm = cls.normalize_label_text(clean_target)
        target_alpha = cls.clean_alphanumeric(clean_target)

        # 1. Exact match (case-sensitive)
        for lbl in existing_labels:
            if lbl == clean_target:
                return lbl

        # 2. Case-insensitive match (e.g. "BUG" -> "bug")
        for lbl in existing_labels:
            if lbl.lower() == target_lower:
                return lbl

        # 3. Separator/delimiter normalized match (e.g. "new_lable" <-> "new lable" <-> "new-lable")
        for lbl in existing_labels:
            if cls.normalize_label_text(lbl) == target_norm:
                return lbl

        # 4. Pure alphanumeric match (ignores all punctuation and delimiters)
        if target_alpha:
            for lbl in existing_labels:
                if cls.clean_alphanumeric(lbl) == target_alpha:
                    return lbl

        # 5. Fuzzy match for minor typos using difflib.SequenceMatcher
        best_match = None
        best_ratio = 0.0
        # Higher threshold for short labels (< 4 chars) to prevent false positives like 'ci' <-> 'ui'
        min_ratio = 0.82 if len(target_norm) >= 4 else 0.90

        for lbl in existing_labels:
            lbl_norm = cls.normalize_label_text(lbl)
            ratio = difflib.SequenceMatcher(None, target_norm, lbl_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = lbl

        if best_ratio >= min_ratio and best_match is not None:
            logger.info(f"Fuzzy matched label {target!r} -> {best_match!r} (ratio: {best_ratio:.2f})")
            return best_match

        return None

    @classmethod
    def resolve_or_create_label(
        cls,
        label_name: str,
        existing_labels: List[str],
        cwd: Optional[str] = None,
        default_description: Optional[str] = None
    ) -> Optional[str]:
        """
        Resolves label_name against existing_labels using smart matching.
        If no matching label exists, creates a new GitHub label with a random 6-character hex color.
        """
        if not label_name or not label_name.strip():
            return None

        clean_name = label_name.strip()
        matched = cls.find_matching_label(clean_name, existing_labels)
        if matched:
            logger.info(f"Resolved label {clean_name!r} to existing GitHub label: {matched!r}")
            return matched

        # Label does not exist -> auto-create with randomized hex color
        random_color = cls.generate_random_color()
        description = default_description or f"Auto-created label for {clean_name}"
        create_cmd = [
            "gh", "label", "create", clean_name,
            "--description", description,
            "--color", random_color
        ]
        try:
            subprocess.run(create_cmd, capture_output=True, text=True, check=True, cwd=cwd)
            logger.info(f"Created new GitHub label: {clean_name!r} (color: #{random_color})")
            # In-memory cache update to prevent duplicate creation in same turn/batch
            existing_labels.append(clean_name)
            return clean_name
        except subprocess.CalledProcessError as e:
            logger.warning(f"Label creation returned error for {clean_name!r}: {e.stderr.strip() if e.stderr else e}")
            # Check if it was created concurrently or already exists
            current_labels = cls.get_existing_labels(cwd=cwd)
            matched_now = cls.find_matching_label(clean_name, current_labels)
            if matched_now:
                if matched_now not in existing_labels:
                    existing_labels.append(matched_now)
                return matched_now
            return None
        except Exception as e:
            logger.warning(f"Failed to create label {clean_name!r}: {e}")
            return None

    @classmethod
    def ensure_label_exists(cls, label_name: str, cwd: Optional[str] = None) -> bool:
        """
        Checks if a label exists in the GitHub repository, creating it via gh label create if missing.
        Retained for backward compatibility.
        """
        existing = cls.get_existing_labels(cwd=cwd)
        resolved = cls.resolve_or_create_label(label_name, existing, cwd=cwd)
        return resolved is not None

    @classmethod
    def create_issue(
        cls,
        title: str,
        body: str = "",
        label: str = "bug",
        agent_model: str = "",
        session_id: str = "unknown",
        agent_name: str = "unknown",
        log_file: str = "",
        cwd: Optional[str] = None
    ) -> str:
        """
        Creates a GitHub issue via the gh CLI tool with auto-created AI agent label.
        
        Returns:
            The URL of the created issue or an error message.
        """
        issue_body = cls.format_issue_body(
            body=body,
            label=label,
            agent_model=agent_model,
            session_id=session_id,
            agent_name=agent_name,
            log_file=log_file
        )

        existing_labels = cls.get_existing_labels(cwd=cwd)
        labels_to_apply: List[str] = []

        # Process input label(s) - supporting comma-separated strings
        if label and label.strip():
            raw_labels = [l.strip() for l in label.split(",") if l.strip()]
            for raw_lbl in raw_labels:
                resolved = cls.resolve_or_create_label(
                    raw_lbl,
                    existing_labels,
                    cwd=cwd,
                    default_description=f"Auto-created issue label: {raw_lbl}"
                )
                if resolved and resolved not in labels_to_apply:
                    labels_to_apply.append(resolved)

        # Process agent identifier label
        if agent_name and agent_name.strip():
            agent_label = agent_name.strip()
            if agent_label.lower() != "unknown":
                resolved_agent = cls.resolve_or_create_label(
                    agent_label,
                    existing_labels,
                    cwd=cwd,
                    default_description=f"Issues reported by {agent_label} AI Agent"
                )
                if resolved_agent and resolved_agent not in labels_to_apply:
                    labels_to_apply.append(resolved_agent)

        cmd = [
            "gh", "issue", "create",
            "--title", title,
            "--body", issue_body
        ]

        for lbl in labels_to_apply:
            cmd.extend(["--label", lbl])

        logger.info(f"Creating GitHub issue: title={title!r}, labels={labels_to_apply!r}, agent={agent_name!r}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=cwd
            )
            issue_url = result.stdout.strip()
            logger.info(f"Successfully created GitHub issue: {issue_url}")
            return f"Successfully created GitHub issue: {issue_url}"
        except FileNotFoundError:
            err_msg = "Error: 'gh' CLI tool is not installed or not found in PATH."
            logger.error(err_msg)
            return err_msg
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else ""
            # Fallback resilience: If gh failed specifically due to a label error, retry without labels
            if "label" in stderr.lower() and labels_to_apply:
                logger.warning(f"gh issue create failed with label error ({stderr}). Retrying without labels...")
                retry_cmd = [
                    "gh", "issue", "create",
                    "--title", title,
                    "--body", issue_body
                ]
                try:
                    retry_result = subprocess.run(
                        retry_cmd,
                        capture_output=True,
                        text=True,
                        check=True,
                        cwd=cwd
                    )
                    issue_url = retry_result.stdout.strip()
                    logger.info(f"Successfully created GitHub issue on retry without labels: {issue_url}")
                    return f"Successfully created GitHub issue (labels omitted due to GitHub error): {issue_url}"
                except Exception as retry_err:
                    logger.error(f"Retry without labels failed: {retry_err}")

            err_msg = f"Error creating GitHub issue via gh CLI (exit code {e.returncode}):\n{stderr}"
            logger.error(err_msg)
            return err_msg
