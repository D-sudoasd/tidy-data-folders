#!/usr/bin/env python3
"""Apply approved DOC_RENAME_PLAN.csv with root containment and full preflight."""
from __future__ import annotations

import argparse
import csv
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from path_safety import (  # noqa: E402
    ALLOWED_DOC_ACTIONS,
    EXECUTABLE_DOC_ACTIONS,
    LOG_FIELDS,
    append_log_row,
    ensure_log_header,
    is_sha256_hex,
    is_unsafe_plan_path,
    normalize_rel,
    parent_chain_ok_for_dst,
    parse_approved,
    resolve_under_root,
    sha256_file,
    validate_log_header,
)


def load_rows(plan_path: Path) -> list[dict]:
    with plan_path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def validate_plan_schema(
    rows: list[dict],
    *,
    require_plan_id: str,
    unsafe_skip_hash: bool,
) -> list[str]:
    errors: list[str] = []
    if not rows:
        return errors
    seen_row: set[str] = set()
    plan_ids: set[str] = set()
    for i, r in enumerate(rows, start=1):
        row_id = (r.get("row_id") or "").strip()
        if not row_id:
            errors.append(f"row {i}: missing row_id")
            row_id = str(i)
        if row_id in seen_row:
            errors.append(f"row {row_id}: duplicate row_id")
        seen_row.add(row_id)

        pv = (r.get("plan_version") or "").strip()
        if pv and pv != "2":
            errors.append(f"row {row_id}: plan_version must be 2 (got {pv})")
        elif not pv:
            errors.append(f"row {row_id}: missing plan_version (require 2)")

        pid = (r.get("plan_id") or "").strip()
        if not pid:
            errors.append(f"row {row_id}: missing plan_id")
        else:
            plan_ids.add(pid)

        ap = parse_approved(r.get("approved"))
        if ap is None:
            errors.append(
                f"row {row_id}: approved must be true or false (got {r.get('approved')!r})"
            )

        action = (r.get("action") or "").strip()
        if action not in ALLOWED_DOC_ACTIONS:
            errors.append(
                f"row {row_id}: unknown action {action!r} "
                f"(allowed: {sorted(ALLOWED_DOC_ACTIONS)})"
            )

        src_s = normalize_rel(r.get("src") or "")
        dst_s = normalize_rel(r.get("dst") or "")
        for label, p in (("src", src_s), ("dst", dst_s)):
            err = is_unsafe_plan_path(p)
            if err:
                errors.append(f"row {row_id}: {label} {err}")

        if action in {"review", "keep", "protected"}:
            if src_s and dst_s and src_s.replace("\\", "/") != dst_s.replace("\\", "/"):
                errors.append(
                    f"row {row_id}: {action} requires dst=src (got {src_s} vs {dst_s})"
                )

        # approved + executable → hard fingerprint
        if ap is True and action in EXECUTABLE_DOC_ACTIONS:
            size_s = (r.get("src_size") or "").strip()
            if not size_s.isdigit():
                errors.append(f"row {row_id}: src_size must be non-negative integer")
            h = (r.get("src_sha256") or "").strip()
            if not unsafe_skip_hash:
                if not is_sha256_hex(h):
                    errors.append(
                        f"row {row_id}: src_sha256 must be 64 hex chars for approved executable row"
                    )

    if len(plan_ids) > 1:
        errors.append(f"multiple plan_id values in file: {sorted(plan_ids)}")
    if require_plan_id:
        if not plan_ids:
            errors.append(f"--plan-id {require_plan_id} but plan has no plan_id")
        elif require_plan_id not in plan_ids:
            errors.append(
                f"--plan-id {require_plan_id} does not match plan ({sorted(plan_ids)})"
            )
        elif any((r.get("plan_id") or "").strip() != require_plan_id for r in rows):
            errors.append("every row plan_id must equal --plan-id (missing not filled)")
    return errors


def preflight(
    root: Path,
    rows: list[dict],
    allowed: set[str],
    *,
    allow_symlink: bool,
    unsafe_skip_hash: bool,
    plan_path: Path,
    log_path: Path,
) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    jobs: list[dict] = []
    seen_src: set[str] = set()
    seen_dst: set[str] = set()
    control = {
        plan_path.resolve() if plan_path.exists() else plan_path,
        log_path.resolve() if log_path.exists() else log_path,
    }

    for i, r in enumerate(rows, start=1):
        row_id = (r.get("row_id") or str(i)).strip()
        action = (r.get("action") or "").strip()
        ap = parse_approved(r.get("approved"))
        if ap is not True:
            continue
        if action not in allowed:
            if action in ALLOWED_DOC_ACTIONS:
                continue  # keep/review/protected — no-op for apply
            errors.append(f"row {row_id}: action not executable: {action}")
            continue

        src_s = normalize_rel(r.get("src") or "")
        dst_s = normalize_rel(r.get("dst") or "")

        try:
            src = resolve_under_root(root, src_s, allow_symlink=allow_symlink)
            dst = resolve_under_root(root, dst_s, allow_symlink=allow_symlink)
        except ValueError as e:
            errors.append(f"row {row_id}: {e}")
            continue

        try:
            if src.resolve() in control or (
                src.exists() and any(src.samefile(c) for c in control if c.exists())
            ):
                errors.append(f"row {row_id}: refuses to move control file {src_s}")
                continue
        except OSError:
            pass

        if "DOC_RENAME_PLAN" in Path(src_s).name or src_s.endswith("_doc_meta.jsonl"):
            errors.append(f"row {row_id}: refuses to move control file {src_s}")
            continue

        if not src.exists() or not src.is_file():
            errors.append(f"row {row_id}: src missing or not a file: {src_s}")
            continue

        key_src = str(src).casefold()
        key_dst = str(dst).casefold()
        if key_src in seen_src:
            errors.append(f"row {row_id}: duplicate src in plan: {src_s}")
            continue
        if key_dst in seen_dst:
            errors.append(f"row {row_id}: duplicate dst in plan: {dst_s}")
            continue
        seen_src.add(key_src)
        seen_dst.add(key_dst)

        if normalize_rel(src_s).casefold() == normalize_rel(dst_s).casefold():
            continue
        try:
            if src.exists() and dst.exists() and src.samefile(dst):
                continue
        except OSError:
            pass

        if dst.exists():
            errors.append(f"row {row_id}: dest exists: {dst_s}")
            continue

        perr = parent_chain_ok_for_dst(root, dst, allow_symlink=allow_symlink)
        if perr:
            errors.append(f"row {row_id}: {perr}")
            continue

        if action == "move_only" and Path(src_s).name != Path(dst_s).name:
            errors.append(
                f"row {row_id}: move_only must preserve basename "
                f"({Path(src_s).name} vs {Path(dst_s).name})"
            )
            continue

        size = src.stat().st_size
        plan_size = (r.get("src_size") or "").strip()
        plan_hash = (r.get("src_sha256") or "").strip()

        if plan_size.isdigit() and int(plan_size) != size:
            errors.append(
                f"row {row_id}: src size changed (plan={plan_size} now={size})"
            )
            continue

        now_hash = sha256_file(src)
        if not unsafe_skip_hash:
            if not is_sha256_hex(plan_hash):
                errors.append(f"row {row_id}: missing/invalid src_sha256")
                continue
            if now_hash.lower() != plan_hash.lower():
                errors.append(f"row {row_id}: src sha256 mismatch (file changed)")
                continue

        jobs.append(
            {
                "row_id": row_id,
                "plan_id": (r.get("plan_id") or "").strip(),
                "src_rel": src_s,
                "dst_rel": dst_s,
                "src": src,
                "dst": dst,
                "action": action,
                "reason": (r.get("reason") or r.get("reason_codes") or "doc rename"),
                "sha256": now_hash,
                "kind": "move" if action == "move_only" else "doc_rename",
            }
        )

    return jobs, errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Apply document rename plan (safe)")
    ap.add_argument("--root", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--move-log", required=True)
    ap.add_argument("--what-if", action="store_true")
    ap.add_argument(
        "--actions",
        default="rename,normalize,move_only",
        help="Comma-separated executable actions",
    )
    ap.add_argument(
        "--allow-symlink",
        action="store_true",
        help="Allow reparse points / symlinks under root (default refuse)",
    )
    ap.add_argument("--plan-id", default="", help="Require exact plan_id match")
    ap.add_argument(
        "--unsafe-skip-hash",
        action="store_true",
        help="MAINTENANCE ONLY: skip sha256 requirement/check",
    )
    # Deprecated aliases that now fail closed (or map to unsafe)
    ap.add_argument("--no-check-hash", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--no-require-approved", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    if args.no_require_approved:
        print(
            "ERROR: --no-require-approved removed; approved=true is always required",
            file=sys.stderr,
        )
        return 2
    if args.no_check_hash:
        args.unsafe_skip_hash = True
        print(
            "WARN: --no-check-hash is deprecated; use --unsafe-skip-hash",
            file=sys.stderr,
        )

    root = Path(args.root).resolve()
    plan_path = Path(args.plan).resolve()
    log_path = Path(args.move_log)
    if not root.is_dir():
        print(f"Root not found: {root}", file=sys.stderr)
        return 2
    if not plan_path.is_file():
        print(f"Plan not found: {plan_path}", file=sys.stderr)
        return 2

    allowed = {a.strip() for a in args.actions.split(",") if a.strip()}
    rows = load_rows(plan_path)
    if not rows:
        print("empty plan")
        return 0

    schema_errors = validate_plan_schema(
        rows,
        require_plan_id=args.plan_id,
        unsafe_skip_hash=args.unsafe_skip_hash,
    )

    # log header preflight
    try:
        if log_path.exists():
            herr = validate_log_header(log_path)
            if herr:
                schema_errors.append(herr)
        else:
            # ensure parent writable
            log_path.parent.mkdir(parents=True, exist_ok=True)
            probe = log_path.parent / f"._tidy_probe_{uuid.uuid4().hex[:8]}"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
    except OSError as e:
        schema_errors.append(f"move log not writable: {e}")

    if schema_errors:
        print("PREFLIGHT FAILED — zero files moved", file=sys.stderr)
        for e in schema_errors:
            print(f"  ERROR: {e}", file=sys.stderr)
        return 3

    jobs, errors = preflight(
        root,
        rows,
        allowed,
        allow_symlink=args.allow_symlink,
        unsafe_skip_hash=args.unsafe_skip_hash,
        plan_path=plan_path,
        log_path=log_path,
    )

    if errors:
        print("PREFLIGHT FAILED — zero files moved", file=sys.stderr)
        for e in errors:
            print(f"  ERROR: {e}", file=sys.stderr)
        return 3

    if not jobs:
        print("preflight_ok: 0 jobs (nothing approved or all no-ops)")
        return 0

    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    )
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"preflight_ok: {len(jobs)} jobs run_id={run_id}")

    if args.what_if:
        for j in jobs:
            print(f"WHATIF {j['action']}: {j['src_rel']} -> {j['dst_rel']}")
        print(f"applied: 0 (what-if) would_apply: {len(jobs)}")
        return 0

    try:
        ensure_log_header(log_path)
    except ValueError as e:
        print(f"PREFLIGHT FAILED — {e}", file=sys.stderr)
        return 3

    ok = 0
    applied_jobs: list[dict] = []
    for j in jobs:
        # re-check hash immediately before move
        try:
            if not j["src"].is_file():
                raise RuntimeError("src disappeared")
            now_h = sha256_file(j["src"])
            if not args.unsafe_skip_hash and now_h.lower() != j["sha256"].lower():
                raise RuntimeError("src sha256 changed between preflight and apply")
            perr = parent_chain_ok_for_dst(root, j["dst"], allow_symlink=args.allow_symlink)
            if perr:
                raise RuntimeError(perr)
            j["dst"].parent.mkdir(parents=True, exist_ok=True)
            if j["dst"].exists():
                raise RuntimeError("dest appeared after preflight")
            append_log_row(
                log_path,
                {
                    "run_id": run_id,
                    "plan_id": j.get("plan_id", ""),
                    "row_id": j["row_id"],
                    "timestamp_utc": ts,
                    "src": j["src_rel"],
                    "dst": j["dst_rel"],
                    "kind": j["kind"],
                    "status": "preflight_ok",
                    "reason": j["reason"],
                    "error": "",
                    "sha256_before": j["sha256"],
                    "sha256_after": "",
                },
            )
            j["src"].rename(j["dst"])
            after = sha256_file(j["dst"]) if j["dst"].is_file() else ""
            if after and after.lower() != j["sha256"].lower():
                raise RuntimeError("sha256_after != sha256_before after rename")
            append_log_row(
                log_path,
                {
                    "run_id": run_id,
                    "plan_id": j.get("plan_id", ""),
                    "row_id": j["row_id"],
                    "timestamp_utc": ts,
                    "src": j["src_rel"],
                    "dst": j["dst_rel"],
                    "kind": j["kind"],
                    "status": "applied",
                    "reason": j["reason"],
                    "error": "",
                    "sha256_before": j["sha256"],
                    "sha256_after": after,
                },
            )
            print(f"OK {j['action']}: {j['src_rel']} -> {j['dst_rel']}")
            ok += 1
            applied_jobs.append(j)
        except Exception as e:
            append_log_row(
                log_path,
                {
                    "run_id": run_id,
                    "plan_id": j.get("plan_id", ""),
                    "row_id": j["row_id"],
                    "timestamp_utc": ts,
                    "src": j["src_rel"],
                    "dst": j["dst_rel"],
                    "kind": j["kind"],
                    "status": "failed",
                    "reason": j["reason"],
                    "error": f"{type(e).__name__}: {e}",
                    "sha256_before": j.get("sha256", ""),
                    "sha256_after": "",
                },
            )
            # best-effort reverse already applied jobs
            for prev in reversed(applied_jobs):
                try:
                    if prev["dst"].exists() and not prev["src"].exists():
                        prev["dst"].rename(prev["src"])
                        append_log_row(
                            log_path,
                            {
                                "run_id": run_id,
                                "plan_id": prev.get("plan_id", ""),
                                "row_id": prev["row_id"],
                                "timestamp_utc": ts,
                                "src": prev["dst_rel"],
                                "dst": prev["src_rel"],
                                "kind": prev["kind"],
                                "status": "rolled_back",
                                "reason": "rollback after later failure",
                                "error": "",
                                "sha256_before": prev["sha256"],
                                "sha256_after": prev["sha256"],
                            },
                        )
                except Exception as re:
                    append_log_row(
                        log_path,
                        {
                            "run_id": run_id,
                            "plan_id": prev.get("plan_id", ""),
                            "row_id": prev["row_id"],
                            "timestamp_utc": ts,
                            "src": prev["dst_rel"],
                            "dst": prev["src_rel"],
                            "kind": prev["kind"],
                            "status": "rollback_failed",
                            "reason": "rollback after later failure",
                            "error": f"{type(re).__name__}: {re}",
                            "sha256_before": prev.get("sha256", ""),
                            "sha256_after": "",
                        },
                    )
            print(
                f"FAILED after partial apply at row {j['row_id']}: {e}",
                file=sys.stderr,
            )
            print(f"applied: {ok} (stopped; rollback attempted)")
            print(f"move_log: {log_path}")
            return 4

    print(f"applied: {ok}")
    print(f"move_log: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
