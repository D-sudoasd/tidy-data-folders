#!/usr/bin/env python3
"""Root containment and plan path safety helpers (hardened)."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

# Unified MOVE_LOG schema (doc rename / unit move / shell remove)
LOG_FIELDS = [
    "run_id",
    "plan_id",
    "row_id",
    "timestamp_utc",
    "src",
    "dst",
    "kind",
    "status",
    "reason",
    "error",
    "sha256_before",
    "sha256_after",
]

ALLOWED_DOC_ACTIONS = frozenset(
    {"rename", "normalize", "move_only", "keep", "review", "protected"}
)
EXECUTABLE_DOC_ACTIONS = frozenset({"rename", "normalize", "move_only"})
ALLOWED_UNIT_KINDS = frozenset(
    {"move", "rename_parent", "archive", "shell_remove", "path_rewrite", "doc_rename"}
)

SHA256_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def normalize_rel(p: str) -> str:
    s = (p or "").strip().replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s


def is_unsafe_plan_path(p: str) -> str | None:
    """Return error message if plan path string is unsafe; else None."""
    s = (p or "").strip()
    if not s:
        return "empty path"
    if s.startswith("/") or (len(s) >= 2 and s[1] == ":"):
        return "absolute path not allowed in plan"
    if s.startswith("\\\\") or s.startswith("//"):
        return "UNC/absolute path not allowed in plan"
    parts = normalize_rel(s).split("/")
    if ".." in parts:
        return "path contains '..'"
    if any(part in (".", "") for part in parts if part != "."):
        # empty segment from //
        if "" in parts:
            return "empty path segment"
    return None


def _is_reparse(path: Path) -> bool:
    """True if path is symlink or Windows reparse point. Raises on attribute errors."""
    if path.is_symlink():
        return True
    if os.name == "nt":
        import ctypes

        GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW  # type: ignore[attr-defined]
        GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
        GetFileAttributesW.restype = ctypes.c_uint32
        attrs = GetFileAttributesW(str(path))
        if attrs == 0xFFFFFFFF:
            # invalid path / access — treat as failure for safety
            err = ctypes.get_last_error()
            raise OSError(f"GetFileAttributesW failed for {path} (err={err})")
        return bool(attrs & 0x400)
    return False


def _lexists(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except (OSError, ValueError):
        return False


def resolve_under_root(root: Path, rel: str, *, allow_symlink: bool = False) -> Path:
    """
    Resolve rel under root.

    Default: reject any existing path component that is a symlink or reparse point
    (including links that stay inside root). Walk components before following.
    """
    err = is_unsafe_plan_path(rel)
    if err:
        raise ValueError(err)
    root_res = root.resolve()
    parts = [p for p in normalize_rel(rel).split("/") if p and p != "."]
    if not parts:
        raise ValueError("empty path")

    # Walk component-by-component without resolving through links
    current = root_res
    for part in parts:
        current = current / part
        if _lexists(current):
            if not allow_symlink:
                try:
                    if current.is_symlink() or _is_reparse(current):
                        raise ValueError(f"reparse/symlink not allowed: {rel}")
                except OSError as e:
                    raise ValueError(f"cannot inspect path component: {rel}: {e}") from e

    # Lexical containment (no .. already)
    try:
        current.relative_to(root_res)
    except ValueError as e:
        raise ValueError(f"path escapes root: {rel}") from e

    if current.exists():
        real = current.resolve()
        try:
            real.relative_to(root_res)
        except ValueError as e:
            raise ValueError(f"path escapes root after resolve: {rel}") from e
        # After resolve, ensure no unexpected jump (re-check real is under root)
        if not allow_symlink and real != current:
            # resolved to different path — only OK if no symlink was in chain
            # (we already blocked symlinks; still verify containment)
            pass
        return real
    return current


def nearest_existing_ancestor(path: Path) -> Path:
    p = path
    while True:
        if p.exists():
            return p
        if p.parent == p:
            return p
        p = p.parent


def parent_chain_ok_for_dst(root: Path, dst: Path, *, allow_symlink: bool = False) -> str | None:
    """
    Ensure dst can be created: nearest existing ancestor is a directory under root,
    not a file, and not a reparse (unless allowed).
    """
    root_res = root.resolve()
    anc = nearest_existing_ancestor(dst.parent if not dst.exists() else dst)
    try:
        anc.resolve().relative_to(root_res)
    except ValueError:
        return f"dst ancestor outside root: {anc}"
    if not anc.is_dir():
        return f"dst parent ancestor is not a directory: {anc}"
    if not allow_symlink:
        try:
            if anc.is_symlink() or _is_reparse(anc):
                return f"dst ancestor is reparse/symlink: {anc}"
        except OSError as e:
            return f"cannot inspect dst ancestor: {e}"
    return None


def sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def quick_fingerprint(path: Path, max_bytes: int = 2 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    size = path.stat().st_size
    with path.open("rb") as f:
        h.update(f.read(max_bytes))
        h.update(b"|")
        h.update(str(size).encode("ascii"))
    return h.hexdigest()


def truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "y", "approved"}


def is_falsey_approved(v: str | None) -> bool:
    return (v or "").strip().lower() in {"0", "false", "no", "n", ""}


def parse_approved(v: str | None) -> bool | None:
    """Return True/False or None if invalid."""
    s = (v or "").strip().lower()
    if s in {"1", "true", "yes", "y"}:
        return True
    if s in {"0", "false", "no", "n"}:
        return False
    return None


def is_sha256_hex(s: str) -> bool:
    return bool(SHA256_HEX_RE.match((s or "").strip()))


def validate_log_header(path: Path) -> str | None:
    """If path exists, require exact LOG_FIELDS header. Return error or None."""
    if not path.exists():
        return None
    if path.stat().st_size == 0:
        return "move log exists but is empty (no header)"
    import csv

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return "move log has no header"
    header = [h.strip() for h in header]
    if header != LOG_FIELDS:
        return f"move log header mismatch: got {header}, expected {LOG_FIELDS}"
    return None


def ensure_log_header(path: Path) -> None:
    err = validate_log_header(path)
    if err:
        raise ValueError(err)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        import csv

        with path.open("w", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=LOG_FIELDS).writeheader()


def append_log_row(path: Path, row: dict) -> None:
    import csv

    ensure_log_header(path)
    # CSV injection guard
    safe = {}
    for k in LOG_FIELDS:
        v = row.get(k, "")
        if isinstance(v, str) and v and v[0] in "=+-@":
            v = "'" + v
        safe[k] = v
    with path.open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=LOG_FIELDS).writerow(safe)


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write via temp file in same directory then replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    try:
        with tmp.open("w", encoding=encoding, newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def refuse_out_overwrite(
    out: Path,
    *,
    root: Path | None = None,
    extra_forbidden: list[Path] | None = None,
    allow_overwrite_generated: bool = False,
) -> str | None:
    """
    Return error if out must not be written.
    By default refuse any existing path.
    """
    out = out.resolve() if out.exists() else out
    if out.exists() and not allow_overwrite_generated:
        return f"output exists (refuse overwrite): {out}"
    forbidden: list[Path] = list(extra_forbidden or [])
    for fp in forbidden:
        try:
            if fp.exists() and out.resolve() == fp.resolve():
                return f"output collides with control/source file: {out}"
        except OSError:
            if str(out) == str(fp):
                return f"output collides with control/source file: {out}"
    return None
