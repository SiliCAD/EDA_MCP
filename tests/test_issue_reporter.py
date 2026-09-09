import unittest
from unittest.mock import patch, MagicMock
import subprocess
import json
import re
from src.issue_reporter import IssueReporter

class TestIssueReporter(unittest.TestCase):

    def test_format_issue_body(self):
        body = IssueReporter.format_issue_body(
            body="## Problem\nTimeout waiting for output file lock",
            agent_name="Antigravity",
            agent_model="gemini-3.6-flash",
            session_id="test-session-123",
            log_file="eda_mcp_20260815_120000_999.log"
        )

        self.assertIn("> **Reported by Agent:** Antigravity (`gemini-3.6-flash`) (Chip Design Consumer)", body)
        self.assertIn("> **Session ID:** `test-session-123`", body)
        self.assertIn("> **MCP Log File:** `logs/eda_mcp_20260815_120000_999.log` (created in `logs/` folder)", body)
        self.assertIn("## Problem\nTimeout waiting for output file lock", body)

    def test_format_issue_body_freeform_markdown(self):
        freeform_md = """## Feature Request: Add Spectre Netlist Parser

Please add support for parsing Cadence Spectre netlist files `.scs` directly.

### User Benefits
- Allows automated extraction of transistor device models
- Enables automated corner sweep configuration
"""
        result = IssueReporter.format_issue_body(
            body=freeform_md,
            agent_name="Antigravity",
            agent_model="gemini-3.6-flash",
            session_id="test-session-456",
            log_file="eda_mcp_20260815_120000_999.log"
        )

        self.assertIn("> **Reported by Agent:** Antigravity (`gemini-3.6-flash`) (Chip Design Consumer)", result)
        self.assertIn("> **Session ID:** `test-session-456`", result)
        self.assertIn("## Feature Request: Add Spectre Netlist Parser", result)
        self.assertIn("- Allows automated extraction of transistor device models", result)

    def test_normalize_label_text(self):
        self.assertEqual(IssueReporter.normalize_label_text("new_lable"), "new lable")
        self.assertEqual(IssueReporter.normalize_label_text("good-first-issue"), "good first issue")
        self.assertEqual(IssueReporter.normalize_label_text("virtuoso/drc.check"), "virtuoso drc check")
        self.assertEqual(IssueReporter.normalize_label_text("  SPICE_Netlist   "), "spice netlist")

    def test_clean_alphanumeric(self):
        self.assertEqual(IssueReporter.clean_alphanumeric("new_lable-123!"), "newlable123")
        self.assertEqual(IssueReporter.clean_alphanumeric("Cadence Virtuoso"), "cadencevirtuoso")

    def test_generate_random_color(self):
        color = IssueReporter.generate_random_color()
        self.assertEqual(len(color), 6)
        self.assertTrue(bool(re.match(r'^[0-9a-f]{6}$', color)))

    @patch("subprocess.run")
    def test_get_existing_labels_json(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout=json.dumps([{"name": "bug"}, {"name": "enhancement"}, {"name": "good first issue"}]),
            returncode=0
        )
        labels = IssueReporter.get_existing_labels()
        self.assertEqual(labels, ["bug", "enhancement", "good first issue"])
        mock_run.assert_called_once()
        self.assertEqual(mock_run.call_args[0][0], ["gh", "label", "list", "--limit", "500", "--json", "name"])

    @patch("subprocess.run")
    def test_get_existing_labels_tsv_fallback(self, mock_run):
        # First call (JSON) fails, second call (TSV) succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["gh"], stderr="unknown flag --json"),
            MagicMock(stdout="bug\tBug report\t#d73a4a\nenhancement\tNew feature\t#a2eeef\n", returncode=0)
        ]
        labels = IssueReporter.get_existing_labels()
        self.assertEqual(labels, ["bug", "enhancement"])
        self.assertEqual(mock_run.call_count, 2)

    def test_find_matching_label(self):
        existing = ["bug", "enhancement", "good first issue", "cadence-virtuoso", "documentation", "new lable"]

        # Exact match
        self.assertEqual(IssueReporter.find_matching_label("bug", existing), "bug")

        # Case-insensitive
        self.assertEqual(IssueReporter.find_matching_label("BUG", existing), "bug")
        self.assertEqual(IssueReporter.find_matching_label("Enhancement", existing), "enhancement")

        # Separator normalization
        self.assertEqual(IssueReporter.find_matching_label("new_lable", existing), "new lable")
        self.assertEqual(IssueReporter.find_matching_label("good-first-issue", existing), "good first issue")
        self.assertEqual(IssueReporter.find_matching_label("cadence_virtuoso", existing), "cadence-virtuoso")

        # Alphanumeric
        self.assertEqual(IssueReporter.find_matching_label("cadence.virtuoso", existing), "cadence-virtuoso")

        # Fuzzy matching (typos)
        self.assertEqual(IssueReporter.find_matching_label("enhansement", existing), "enhancement")
        self.assertEqual(IssueReporter.find_matching_label("documentaion", existing), "documentation")

        # No false positive matches
        self.assertIsNone(IssueReporter.find_matching_label("unrelated_label", existing))
        self.assertIsNone(IssueReporter.find_matching_label("ci", existing))

    @patch("subprocess.run")
    def test_resolve_or_create_label_existing(self, mock_run):
        existing = ["bug", "enhancement"]
        resolved = IssueReporter.resolve_or_create_label("BUG", existing)
        self.assertEqual(resolved, "bug")
        # Subprocess should not be called since match exists
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_resolve_or_create_label_creates_new(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        existing = ["bug", "enhancement"]
        resolved = IssueReporter.resolve_or_create_label("eldo_simulator", existing)
        
        self.assertEqual(resolved, "eldo_simulator")
        self.assertIn("eldo_simulator", existing)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0:4], ["gh", "label", "create", "eldo_simulator"])
        self.assertIn("--color", cmd)

    @patch.object(IssueReporter, "get_existing_labels")
    @patch.object(IssueReporter, "resolve_or_create_label")
    @patch("subprocess.run")
    def test_create_issue_success(self, mock_run, mock_resolve, mock_get_labels):
        mock_get_labels.return_value = ["bug", "Claude"]
        mock_resolve.side_effect = lambda lbl, *args, **kwargs: lbl.lower()

        mock_run.return_value = MagicMock(
            stdout="https://github.com/vs34/EDA_MCP/issues/42\n",
            returncode=0
        )

        result = IssueReporter.create_issue(
            title="Eldo timeout on file lock",
            body="## Bug Details\nEldo script timed out after 600s",
            label="bug, virtuoso",
            agent_model="gemini-3.6-flash",
            session_id="test-session-123",
            agent_name="Claude"
        )

        self.assertIn("Successfully created GitHub issue: https://github.com/vs34/EDA_MCP/issues/42", result)
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        self.assertEqual(cmd[0:3], ["gh", "issue", "create"])
        self.assertIn("--title", cmd)
        self.assertIn("Eldo timeout on file lock", cmd)
        self.assertIn("--label", cmd)
        self.assertIn("bug", cmd)
        self.assertIn("virtuoso", cmd)
        self.assertIn("claude", cmd)

    @patch.object(IssueReporter, "get_existing_labels", return_value=["bug"])
    @patch.object(IssueReporter, "resolve_or_create_label", side_effect=lambda lbl, *args, **kwargs: lbl)
    @patch("subprocess.run")
    def test_create_issue_fallback_on_label_error(self, mock_run, mock_resolve, mock_get_labels):
        # First call with --label fails with GraphQL label error; second call without --label succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["gh", "issue", "create"], stderr="GraphQL: Could not resolve to a Label with the name of 'invalid-lbl'"),
            MagicMock(stdout="https://github.com/vs34/EDA_MCP/issues/99\n", returncode=0)
        ]

        result = IssueReporter.create_issue(
            title="Test fallback issue",
            body="Content",
            label="invalid-lbl",
            agent_name="Antigravity"
        )

        self.assertIn("Successfully created GitHub issue (labels omitted due to GitHub error): https://github.com/vs34/EDA_MCP/issues/99", result)
        self.assertEqual(mock_run.call_count, 2)
        # Verify second call omitted --label
        retry_cmd = mock_run.call_args_list[1][0][0]
        self.assertNotIn("--label", retry_cmd)

    @patch.object(IssueReporter, "get_existing_labels", return_value=["bug"])
    @patch.object(IssueReporter, "resolve_or_create_label", return_value="bug")
    def test_ensure_label_exists_backward_compat(self, mock_resolve, mock_get_labels):
        self.assertTrue(IssueReporter.ensure_label_exists("bug"))
        mock_resolve.assert_called_once()

if __name__ == "__main__":
    unittest.main()
