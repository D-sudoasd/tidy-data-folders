#!/usr/bin/env python3
"""Tests for the unified tidy-data-folders command-line entry point."""
from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tidy  # noqa: E402


class CommandBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("/workspace/root")
        self.plan = Path("/workspace/root/docs/plan.csv")
        self.log = Path("/workspace/root/MOVE_LOG.csv")

    def test_apply_moves_defaults_to_preview(self):
        command = tidy.build_apply_moves_command(
            root=self.root,
            plan=self.plan,
            move_log=self.log,
            execute=False,
            pwsh="pwsh",
        )
        self.assertIn("-WhatIf", command)

    def test_apply_moves_execute_removes_preview_flag(self):
        command = tidy.build_apply_moves_command(
            root=self.root,
            plan=self.plan,
            move_log=self.log,
            execute=True,
            pwsh="pwsh",
        )
        self.assertNotIn("-WhatIf", command)

    def test_apply_docs_defaults_to_preview(self):
        command = tidy.build_apply_docs_command(
            root=self.root,
            plan=self.plan,
            move_log=self.log,
            execute=False,
            plan_id="p1",
        )
        self.assertIn("--what-if", command)
        self.assertEqual(command[-2:], ["--plan-id", "p1"])

    def test_apply_docs_execute_removes_preview_flag(self):
        command = tidy.build_apply_docs_command(
            root=self.root,
            plan=self.plan,
            move_log=self.log,
            execute=True,
            plan_id="",
        )
        self.assertNotIn("--what-if", command)

    def test_sweep_defaults_to_preview(self):
        command = tidy.build_sweep_command(
            root=self.root,
            move_log=self.log,
            execute=False,
            pwsh="pwsh",
        )
        self.assertIn("-WhatIf", command)

    def test_sweep_execute_removes_preview_flag(self):
        command = tidy.build_sweep_command(
            root=self.root,
            move_log=self.log,
            execute=True,
            pwsh="pwsh",
        )
        self.assertNotIn("-WhatIf", command)

    def test_audit_includes_selected_evidence(self):
        command = tidy.build_audit_command(
            root=self.root,
            pwsh="pwsh",
            before_count=10,
            move_log=self.log,
            doc_plan=self.plan,
            profile="literature-dump",
            require_readme=True,
            check_paths=["01_papers/current.pdf"],
        )
        self.assertIn("-BeforeCount", command)
        self.assertIn("-AppliedLog", command)
        self.assertIn("-DocRenamePlan", command)
        self.assertIn("-RequireReadme", command)
        self.assertIn("-CheckPaths", command)


class DoctorTests(unittest.TestCase):
    def test_doctor_payload_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as td:
            script_dir = Path(td)
            for name in tidy.REQUIRED_SCRIPTS:
                (script_dir / name).write_text("", encoding="utf-8")

            checks = tidy.collect_doctor_checks(
                script_dir=script_dir,
                which=lambda name: "/usr/bin/pwsh" if name == "pwsh" else None,
                find_spec=lambda name: object() if name in {"pypdf", "docx"} else None,
                pwsh_probe=lambda path: (True, f"7.4.0 at {path} (required >= 7)"),
            )
            payload = tidy._doctor_payload(checks)
            encoded = json.dumps(payload)

        self.assertTrue(payload["required_ready"])
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn('"tool": "tidy-data-folders"', encoded)
        by_name = {row["name"]: row for row in payload["checks"]}
        self.assertTrue(by_name["pypdf"]["ok"])
        self.assertFalse(by_name["python-pptx"]["ok"])
        self.assertFalse(by_name["python-pptx"]["required"])

    def test_missing_pwsh_marks_required_workflow_not_ready(self):
        with tempfile.TemporaryDirectory() as td:
            script_dir = Path(td)
            for name in tidy.REQUIRED_SCRIPTS:
                (script_dir / name).write_text("", encoding="utf-8")
            checks = tidy.collect_doctor_checks(
                script_dir=script_dir,
                which=lambda _: None,
                find_spec=lambda _: None,
                pwsh_probe=lambda _: (False, "not called"),
            )
        self.assertFalse(tidy._doctor_payload(checks)["required_ready"])


class ParserAndPathTests(unittest.TestCase):
    def test_mutating_commands_require_explicit_execute(self):
        parser = tidy.build_parser()
        moves = parser.parse_args(
            ["apply-moves", "--root", "/data", "--plan", "docs/unit_plan.csv"]
        )
        docs = parser.parse_args(
            ["apply-docs", "--root", "/data", "--plan", "docs/doc_plan.csv"]
        )
        sweep = parser.parse_args(
            ["sweep", "--root", "/data", "--move-log", "MOVE_LOG.csv"]
        )
        self.assertFalse(moves.execute)
        self.assertFalse(docs.execute)
        self.assertFalse(sweep.execute)

    def test_relative_control_path_is_root_relative(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            path = tidy._control_path(root, "docs/plan.csv")
        self.assertEqual(path, root / "docs" / "plan.csv")

    def test_relative_control_path_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            with self.assertRaises(tidy.CliError):
                tidy._control_path(root, "../outside.csv")

    def test_init_unit_plan_is_unapproved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output = io.StringIO()
            with redirect_stdout(output):
                rc = tidy.main(["init-unit-plan", "--root", str(root)])
            plan = root / "docs" / "unit_plan.csv"
            with plan.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(rc, 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["approved"], "false")
        self.assertEqual(rows[0]["kind"], "move")

    def test_init_unit_plan_refuses_overwrite_of_unrelated_csv(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "docs" / "unit_plan.csv"
            out.parent.mkdir()
            out.write_text("sample,value\n1,2\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc = tidy.main(
                    [
                        "init-unit-plan",
                        "--root",
                        str(root),
                        "--overwrite",
                    ]
                )
            text = out.read_text(encoding="utf-8")
        self.assertEqual(rc, 2)
        self.assertEqual(text, "sample,value\n1,2\n")

    def test_guide_runs_without_external_tools(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(tidy.main(["guide"]), 0)


if __name__ == "__main__":
    unittest.main()
