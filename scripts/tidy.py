#!/usr/bin/env python3
"""Unified, safe entry point for tidy-data-folders.

The launcher keeps the existing scripts as the execution source of truth. Commands
that can move or remove items run in preview mode unless ``--execute`` is supplied.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

VERSION = "0.3.0"
MIN_PYTHON = (3, 10)
SCRIPT_DIR = Path(__file__).resolve().parent

REQUIRED_SCRIPTS = (
    "inventory.ps1",
    "apply_moves.ps1",
    "empty_shell_sweep.ps1",
    "post_audit.ps1",
    "extract_doc_meta.py",
    "propose_doc_renames.py",
    "apply_doc_renames.py",
    "path_safety.py",
)

UNIT_PLAN_FIELDS = (
    "plan_version",
    "plan_id",
    "row_id",
    "approved",
    "src",
    "dst",
    "kind",
    "reason",
)

DOC_PLAN_FIELDS = (
    "plan_version",
    "plan_id",
    "row_id",
    "approved",
    "src",
    "dst",
    "action",
    "doc_type",
    "confidence",
    "reason",
    "reason_codes",
    "doi",
    "title",
    "year",
    "year_source",
    "title_source",
    "author_source",
    "src_size",
    "src_mtime_utc",
    "src_sha256",
    "content_hash_short",
)

OPTIONAL_EXTRACTORS = (
    ("pypdf", "pypdf", "PDF metadata and text signals"),
    ("docx", "python-docx", "DOCX metadata and text signals"),
    ("pptx", "python-pptx", "PPTX metadata signals"),
)


class CliError(RuntimeError):
    """Expected command-line precondition failure."""


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    required: bool
    detail: str


def _quote_command(command: Sequence[str]) -> str:
    """Return a copyable command string for diagnostics."""
    parts = [str(part) for part in command]
    if os.name == "nt":
        return subprocess.list2cmdline(parts)
    return shlex.join(parts)


def _run(command: Sequence[str]) -> int:
    command = [str(part) for part in command]
    print(f"> {_quote_command(command)}")
    try:
        completed = subprocess.run(command, check=False)
    except OSError as exc:
        print(f"ERROR: could not start command: {exc}", file=sys.stderr)
        return 2
    return int(completed.returncode)


def _script(name: str) -> Path:
    path = SCRIPT_DIR / name
    if not path.is_file():
        raise CliError(f"required script is missing: {path}")
    return path


def _existing_root(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise CliError(f"root folder not found: {path}")
    return path


def _control_path(root: Path, raw: str) -> Path:
    """Interpret relative plan/log paths from the selected root."""
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()

    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise CliError(
            "relative control path escapes the selected root; "
            f"use an explicit absolute path when external storage is intentional: {raw}"
        ) from exc
    return resolved


def _existing_control_path(root: Path, raw: str, label: str) -> Path:
    path = _control_path(root, raw)
    if not path.is_file():
        raise CliError(f"{label} not found: {path}")
    return path


def _default_move_log(root: Path) -> Path:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return root / f"MOVE_LOG_{day}_tidy.csv"


def _pwsh_path(which: Callable[[str], str | None] = shutil.which) -> str:
    pwsh = which("pwsh")
    if not pwsh:
        raise CliError(
            "PowerShell 7 was not found. Install `pwsh`, then run "
            "`python scripts/tidy.py doctor` again."
        )
    ok, detail = _probe_pwsh_version(pwsh)
    if not ok:
        raise CliError(f"PowerShell 7 is required: {detail}")
    return pwsh


def _probe_pwsh_version(pwsh: str) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            [
                pwsh,
                "-NoProfile",
                "-Command",
                "$PSVersionTable.PSVersion.ToString()",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"version check failed: {exc}"
    version = (completed.stdout or "").strip().splitlines()
    version_text = version[-1].strip() if version else "unknown"
    try:
        major = int(version_text.split(".", 1)[0])
    except (TypeError, ValueError):
        return False, f"could not parse version: {version_text}"
    if completed.returncode != 0:
        return False, f"version check exited {completed.returncode}: {version_text}"
    return major >= 7, f"{version_text} at {pwsh} (required >= 7)"


def collect_doctor_checks(
    *,
    script_dir: Path = SCRIPT_DIR,
    which: Callable[[str], str | None] = shutil.which,
    find_spec: Callable[[str], object | None] = importlib.util.find_spec,
    pwsh_probe: Callable[[str], tuple[bool, str]] = _probe_pwsh_version,
) -> list[Check]:
    py_ok = sys.version_info >= MIN_PYTHON
    checks = [
        Check(
            name="python",
            ok=py_ok,
            required=True,
            detail=(
                f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} "
                f"(required >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})"
            ),
        )
    ]

    pwsh = which("pwsh")
    if pwsh:
        pwsh_ok, pwsh_detail = pwsh_probe(pwsh)
    else:
        pwsh_ok, pwsh_detail = False, "PowerShell 7 executable not found"
    checks.append(
        Check(
            name="pwsh",
            ok=pwsh_ok,
            required=True,
            detail=pwsh_detail,
        )
    )

    missing = [name for name in REQUIRED_SCRIPTS if not (script_dir / name).is_file()]
    checks.append(
        Check(
            name="script_bundle",
            ok=not missing,
            required=True,
            detail="all required scripts present" if not missing else f"missing: {', '.join(missing)}",
        )
    )

    for import_name, package_name, role in OPTIONAL_EXTRACTORS:
        try:
            found = find_spec(import_name) is not None
        except (ImportError, AttributeError, ValueError):
            found = False
        checks.append(
            Check(
                name=package_name,
                ok=found,
                required=False,
                detail=role if found else f"optional; install `{package_name}` for {role.lower()}",
            )
        )
    return checks


def _doctor_payload(checks: Sequence[Check]) -> dict:
    required_ready = all(check.ok for check in checks if check.required)
    return {
        "schema_version": 1,
        "tool": "tidy-data-folders",
        "version": VERSION,
        "required_ready": required_ready,
        "checks": [asdict(check) for check in checks],
    }


def command_doctor(args: argparse.Namespace) -> int:
    checks = collect_doctor_checks()
    payload = _doctor_payload(checks)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"tidy-data-folders {VERSION}")
        for check in checks:
            marker = "OK" if check.ok else ("MISSING" if check.required else "OPTIONAL")
            requirement = "required" if check.required else "optional"
            print(f"[{marker}] {check.name} ({requirement}): {check.detail}")
        print(f"required workflow ready: {'yes' if payload['required_ready'] else 'no'}")
    return 0 if payload["required_ready"] else 1


def build_survey_command(
    *, root: Path, pwsh: str, json_output: bool, max_depth: int
) -> list[str]:
    command = [
        pwsh,
        "-NoProfile",
        "-File",
        str(_script("inventory.ps1")),
        "-Root",
        str(root),
        "-MaxDepthList",
        str(max_depth),
    ]
    if json_output:
        command.append("-Json")
    return command


def command_survey(args: argparse.Namespace) -> int:
    root = _existing_root(args.root)
    command = build_survey_command(
        root=root,
        pwsh=_pwsh_path(),
        json_output=args.json,
        max_depth=args.max_depth,
    )
    return _run(command)


def _csv_header(path: Path) -> tuple[str, ...]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return tuple(next(csv.reader(handle)))
    except (OSError, StopIteration, UnicodeError, csv.Error) as exc:
        raise CliError(f"cannot inspect existing generated CSV {path}: {exc}") from exc


def _require_generated_csv(path: Path, expected: Sequence[str], label: str) -> None:
    header = _csv_header(path)
    if header != tuple(expected):
        raise CliError(
            f"refuse to overwrite {label} with an unexpected header: {path}"
        )


def _require_generated_meta(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CliError(f"cannot inspect existing metadata JSONL {path}: {exc}") from exc
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        if "doc_meta" in path.stem.lower():
            return
        raise CliError(f"refuse to overwrite unrecognized empty JSONL: {path}")
    try:
        first = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise CliError(f"refuse to overwrite invalid metadata JSONL {path}: {exc}") from exc
    keys = set(first) if isinstance(first, dict) else set()
    if not {"rel", "name"}.issubset(keys) or not (
        {"sha256_full", "error", "extract_supported"} & keys
    ):
        raise CliError(f"refuse to overwrite unrecognized metadata JSONL: {path}")


def command_init_unit_plan(args: argparse.Namespace) -> int:
    root = _existing_root(args.root)
    out = _control_path(root, args.out)
    if out.suffix.lower() != ".csv":
        raise CliError(f"unit plan must end with .csv: {out}")
    if out.exists():
        if not args.overwrite:
            raise CliError(f"output exists; use --overwrite only for generated output: {out}")
        _require_generated_csv(out, UNIT_PLAN_FIELDS, "unit-plan CSV")

    out.parent.mkdir(parents=True, exist_ok=True)
    plan_id = args.plan_id or (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_"
        + uuid.uuid4().hex[:8]
    )
    rows: list[dict[str, str]] = []
    if not args.empty:
        rows.append(
            {
                "plan_version": "1",
                "plan_id": plan_id,
                "row_id": "1",
                "approved": "false",
                "src": "REPLACE_ME/source",
                "dst": "REPLACE_ME/destination",
                "kind": "move",
                "reason": "replace or delete this example row",
            }
        )

    tmp = out.with_name(out.name + f".tmp.{os.getpid()}")
    try:
        with tmp.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=UNIT_PLAN_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, out)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)

    print(f"unit plan: {out}")
    print(f"plan_id: {plan_id}")
    if rows:
        print("next: replace or delete the example row; keep approved=false until accepted")
    else:
        print("next: add one row per unit move; keep approved=false until accepted")
    return 0


def command_plan_docs(args: argparse.Namespace) -> int:
    root = _existing_root(args.root)
    out = _control_path(root, args.out)
    if out.suffix.lower() != ".csv":
        raise CliError(f"document plan must end with .csv: {out}")
    if out.exists():
        if not args.overwrite:
            raise CliError(f"output exists; use --overwrite only for generated output: {out}")
        _require_generated_csv(out, DOC_PLAN_FIELDS, "document-plan CSV")
    out.parent.mkdir(parents=True, exist_ok=True)

    temp_context: tempfile.TemporaryDirectory[str] | None = None
    if args.meta_out:
        meta = _control_path(root, args.meta_out)
        if meta.suffix.lower() != ".jsonl":
            raise CliError(f"metadata output must end with .jsonl: {meta}")
        if meta.exists():
            if not args.overwrite:
                raise CliError(f"metadata output exists; use --overwrite: {meta}")
            _require_generated_meta(meta)
        meta.parent.mkdir(parents=True, exist_ok=True)
    else:
        temp_context = tempfile.TemporaryDirectory(prefix="tidy_doc_meta_")
        meta = Path(temp_context.name) / "doc_meta.jsonl"

    extract = [
        sys.executable,
        str(_script("extract_doc_meta.py")),
        "--root",
        str(root),
        "--out",
        str(meta),
        "--max-file-mb",
        str(args.max_file_mb),
    ]
    if args.no_recursive:
        extract.append("--no-recursive")
    if args.include_text_snip:
        extract.append("--include-text-snip")
    if args.overwrite and meta.exists():
        extract.append("--overwrite-generated-output")

    propose = [
        sys.executable,
        str(_script("propose_doc_renames.py")),
        "--root",
        str(root),
        "--meta",
        str(meta),
        "--out",
        str(out),
        "--profile",
        args.profile,
        "--slot-layout",
        args.slot_layout,
        "--max-stem",
        str(args.max_stem),
    ]
    if args.overwrite and out.exists():
        propose.append("--overwrite-generated-output")

    try:
        rc = _run(extract)
        if rc != 0:
            return rc
        rc = _run(propose)
        if rc == 0:
            print(f"plan: {out}")
            print("next: review every row; set approved=true only on accepted rows")
            preview = [
                sys.executable,
                str(Path(__file__).resolve()),
                "apply-docs",
                "--root",
                str(root),
                "--plan",
                str(out),
            ]
            print(f"preview: {_quote_command(preview)}")
        return rc
    finally:
        if temp_context is not None:
            temp_context.cleanup()


def build_apply_moves_command(
    *,
    root: Path,
    plan: Path,
    move_log: Path,
    execute: bool,
    pwsh: str,
) -> list[str]:
    command = [
        pwsh,
        "-NoProfile",
        "-File",
        str(_script("apply_moves.ps1")),
        "-Root",
        str(root),
        "-PlanCsv",
        str(plan),
        "-MoveLog",
        str(move_log),
    ]
    if not execute:
        command.append("-WhatIf")
    return command


def command_apply_moves(args: argparse.Namespace) -> int:
    root = _existing_root(args.root)
    plan = _existing_control_path(root, args.plan, "unit plan")
    move_log = _control_path(root, args.move_log) if args.move_log else _default_move_log(root)
    print(f"mode: {'EXECUTE' if args.execute else 'PREVIEW'}")
    return _run(
        build_apply_moves_command(
            root=root,
            plan=plan,
            move_log=move_log,
            execute=args.execute,
            pwsh=_pwsh_path(),
        )
    )


def build_apply_docs_command(
    *,
    root: Path,
    plan: Path,
    move_log: Path,
    execute: bool,
    plan_id: str,
) -> list[str]:
    command = [
        sys.executable,
        str(_script("apply_doc_renames.py")),
        "--root",
        str(root),
        "--plan",
        str(plan),
        "--move-log",
        str(move_log),
    ]
    if not execute:
        command.append("--what-if")
    if plan_id:
        command.extend(["--plan-id", plan_id])
    return command


def command_apply_docs(args: argparse.Namespace) -> int:
    root = _existing_root(args.root)
    plan = _existing_control_path(root, args.plan, "document plan")
    move_log = _control_path(root, args.move_log) if args.move_log else _default_move_log(root)
    print(f"mode: {'EXECUTE' if args.execute else 'PREVIEW'}")
    return _run(
        build_apply_docs_command(
            root=root,
            plan=plan,
            move_log=move_log,
            execute=args.execute,
            plan_id=args.plan_id,
        )
    )


def build_sweep_command(
    *, root: Path, move_log: Path, execute: bool, pwsh: str
) -> list[str]:
    command = [
        pwsh,
        "-NoProfile",
        "-File",
        str(_script("empty_shell_sweep.ps1")),
        "-Root",
        str(root),
        "-AppliedLog",
        str(move_log),
        "-MoveLog",
        str(move_log),
    ]
    if not execute:
        command.append("-WhatIf")
    return command


def command_sweep(args: argparse.Namespace) -> int:
    root = _existing_root(args.root)
    move_log = _existing_control_path(root, args.move_log, "move log")
    print(f"mode: {'EXECUTE' if args.execute else 'PREVIEW'}")
    return _run(
        build_sweep_command(
            root=root,
            move_log=move_log,
            execute=args.execute,
            pwsh=_pwsh_path(),
        )
    )


def build_audit_command(
    *,
    root: Path,
    pwsh: str,
    before_count: int | None,
    move_log: Path | None,
    doc_plan: Path | None,
    profile: str,
    require_readme: bool,
    check_paths: Sequence[str],
) -> list[str]:
    command = [
        pwsh,
        "-NoProfile",
        "-File",
        str(_script("post_audit.ps1")),
        "-Root",
        str(root),
    ]
    if before_count is not None:
        command.extend(["-BeforeCount", str(before_count)])
    if move_log is not None:
        command.extend(["-AppliedLog", str(move_log)])
    if doc_plan is not None:
        command.extend(["-DocRenamePlan", str(doc_plan)])
    if profile:
        command.extend(["-Profile", profile])
    if require_readme:
        command.append("-RequireReadme")
    if check_paths:
        command.append("-CheckPaths")
        command.extend(str(path) for path in check_paths)
    return command


def command_audit(args: argparse.Namespace) -> int:
    root = _existing_root(args.root)
    move_log = (
        _existing_control_path(root, args.move_log, "move log") if args.move_log else None
    )
    doc_plan = (
        _existing_control_path(root, args.doc_plan, "document plan")
        if args.doc_plan
        else None
    )
    command = build_audit_command(
        root=root,
        pwsh=_pwsh_path(),
        before_count=args.before_count,
        move_log=move_log,
        doc_plan=doc_plan,
        profile=args.profile,
        require_readme=args.require_readme,
        check_paths=args.check_path,
    )
    return _run(command)


def command_guide(_: argparse.Namespace) -> int:
    print(
        "Safe workflow\n"
        "  1. python scripts/tidy.py doctor\n"
        "  2. python scripts/tidy.py survey --root <folder>\n"
        "  3. Create a template: python scripts/tidy.py init-unit-plan --root <folder>\n"
        "     Edit the CSV; keep approved=false until accepted.\n"
        "  4. Preview: python scripts/tidy.py apply-moves --root <folder> --plan <csv>\n"
        "  5. Execute approved rows: add --execute.\n"
        "  6. Preview/execute sweep, then run audit.\n\n"
        "Document-only planning:\n"
        "  python scripts/tidy.py plan-docs --root <folder>\n"
        "  python scripts/tidy.py apply-docs --root <folder> --plan docs/DOC_RENAME_PLAN.csv\n\n"
        "Mutating commands default to preview. `--execute` never bypasses approved=true."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tidy-data-folders",
        description=(
            "One safe entry point for inventory, document planning, preview, execution, "
            "cleanup, and audit."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="check runtime and optional document extractors")
    p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    p.set_defaults(func=command_doctor)

    p = sub.add_parser("guide", help="print the safe end-to-end workflow")
    p.set_defaults(func=command_guide)

    p = sub.add_parser("survey", help="inventory a folder without changing it")
    p.add_argument("--root", required=True)
    p.add_argument("--json", action="store_true", help="emit inventory JSON")
    p.add_argument("--max-depth", type=int, default=2, choices=range(0, 7))
    p.set_defaults(func=command_survey)

    p = sub.add_parser("init-unit-plan", help="create a safe unit-plan CSV template")
    p.add_argument("--root", required=True)
    p.add_argument("--out", default="docs/unit_plan.csv")
    p.add_argument("--plan-id", default="")
    p.add_argument("--empty", action="store_true", help="write only the header")
    p.add_argument("--overwrite", action="store_true", help="replace the generated template")
    p.set_defaults(func=command_init_unit_plan)

    p = sub.add_parser("plan-docs", help="extract metadata and create an unapproved document plan")
    p.add_argument("--root", required=True)
    p.add_argument("--out", default="docs/DOC_RENAME_PLAN.csv")
    p.add_argument("--meta-out", default="", help="keep metadata JSONL; default uses a temp file")
    p.add_argument("--profile", choices=("academic", "human", "normalize"), default="academic")
    p.add_argument("--slot-layout", choices=("literature-dump", "none"), default="literature-dump")
    p.add_argument("--max-stem", type=int, default=120)
    p.add_argument("--max-file-mb", type=float, default=200.0)
    p.add_argument("--no-recursive", action="store_true")
    p.add_argument(
        "--include-text-snip",
        action="store_true",
        help="persist document text snippets in metadata (privacy-sensitive)",
    )
    p.add_argument("--overwrite", action="store_true", help="replace generated CSV/JSONL only")
    p.set_defaults(func=command_plan_docs)

    p = sub.add_parser("apply-moves", help="preview or execute approved unit moves")
    p.add_argument("--root", required=True)
    p.add_argument("--plan", required=True)
    p.add_argument("--move-log", default="")
    p.add_argument("--execute", action="store_true", help="perform approved rows; default is preview")
    p.set_defaults(func=command_apply_moves)

    p = sub.add_parser("apply-docs", help="preview or execute approved document renames")
    p.add_argument("--root", required=True)
    p.add_argument("--plan", required=True)
    p.add_argument("--move-log", default="")
    p.add_argument("--plan-id", default="", help="require an exact plan_id")
    p.add_argument("--execute", action="store_true", help="perform approved rows; default is preview")
    p.set_defaults(func=command_apply_docs)

    p = sub.add_parser("sweep", help="preview or remove empty parents recorded by applied moves")
    p.add_argument("--root", required=True)
    p.add_argument("--move-log", required=True)
    p.add_argument("--execute", action="store_true", help="remove eligible empty directories")
    p.set_defaults(func=command_sweep)

    p = sub.add_parser("audit", help="run post-move integrity and placement checks")
    p.add_argument("--root", required=True)
    p.add_argument("--before-count", type=int)
    p.add_argument("--move-log", default="")
    p.add_argument("--doc-plan", default="")
    p.add_argument(
        "--profile",
        choices=(
            "generic",
            "literature-dump",
            "desktop-dump",
            "manuscript-heavy",
            "sxrd-texture",
            "sxrd-tensile",
        ),
        default="",
    )
    p.add_argument("--require-readme", action="store_true")
    p.add_argument("--check-path", action="append", default=[])
    p.set_defaults(func=command_audit)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except CliError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("ERROR: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
