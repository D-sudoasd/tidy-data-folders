#!/usr/bin/env python3
"""Folder survey and multi-background profile signals.

This module is the shipped source of truth for ``python scripts/tidy.py survey``
and ``inventory.ps1``. Call ``collect_survey`` rather than reimplementing scoring.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

SURVEY_SCHEMA_VERSION = 1

DOC_EXTS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xlsm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".heic"}
ARCHIVE_EXTS = {".zip", ".7z", ".rar", ".tar", ".gz", ".tgz"}
INSTALLER_EXTS = {".exe", ".msi", ".dmg", ".pkg", ".appx"}
SCIENTIFIC_DATA_EXTS = {
    ".cbf",
    ".esg",
    ".fit",
    ".par",
    ".xy",
    ".chi",
    ".raw",
    ".dat",
    ".xye",
    ".spc",
    ".ras",
    ".xrdml",
}
MAP_NAMES = {
    "readme.md",
    "readme_project_map.md",
    "agents.md",
    "file_map.md",
    "archive_map.md",
}
USER_DUMP_DIR_NAMES = {"desktop", "downloads", "桌面"}
LOOSE_DIR_NAMES = {"loose", "inbox", "download", "downloads", "desktop", "dump", "桌面"}

PUBLISHER_NAME_RE = re.compile(
    r"1-s2\.0-|^\d{5,}\.pdf$|^s\d{4,}-|metals-\d|main(\s*\(\d+\))?\.pdf$|Review_`?\d",
    re.IGNORECASE,
)
JUNK_DOC_RE = re.compile(
    r"^(main|data|数据|SAXS|temp|tmp|document|未命名)(\s*\(\d+\))?\.pdf$",
    re.IGNORECASE,
)
SCREENSHOT_NAME_RE = re.compile(
    r"screenshot|screen[_\s-]?shot|屏幕|截图|IMG_\d|DSC_|ChatGPT_|fake",
    re.IGNORECASE,
)
AZIMUTH_NAME_RE = re.compile(r"^Az_\d", re.IGNORECASE)
TEXTURE_NAME_RE = re.compile(r"texture|omega|pole.?figure", re.IGNORECASE)
TENSILE_NAME_RE = re.compile(r"timestamp_aligned|peakfit|\bmaud\b", re.IGNORECASE)
MANUSCRIPT_NAME_RE = re.compile(r"Article_|Letter_|CURRENT", re.IGNORECASE)

MATCH_THRESHOLD = 2
DOMINANCE_RATIO = 2.0
DOMINANCE_DELTA = 2

PHASE_D_BY_PROFILE = {
    "literature-dump": "on",
    "desktop-dump": "docs_bucket",
    "manuscript-heavy": "references_only",
    "sxrd-texture": "off",
    "sxrd-tensile": "off",
    "generic": "optional",
}

FAMILY_PHASE_D = {
    "literature": "on",
    "desktop": "docs_bucket",
    "manuscript": "references_only",
    "scientific": "off",
}


@dataclass
class FileRecord:
    path: Path
    rel: str
    name: str
    ext: str
    size: int


@dataclass
class BackgroundScore:
    family: str
    score: int
    evidence: list[str] = field(default_factory=list)
    profile: str = "generic"

    @property
    def matched(self) -> bool:
        return self.score >= MATCH_THRESHOLD


def _rel_str(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def _iter_files(root: Path) -> Iterable[FileRecord]:
    for dirpath, dirnames, filenames in _walk(root):
        current = Path(dirpath)
        for name in filenames:
            path = current / name
            try:
                if path.is_symlink() and path.is_dir():
                    continue
                size = path.stat().st_size
            except OSError:
                continue
            yield FileRecord(
                path=path,
                rel=_rel_str(root, path),
                name=path.name,
                ext=path.suffix.lower(),
                size=size,
            )


def _walk(root: Path):
    """os.walk-like walk that does not descend into symlink directories."""
    import os

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        keep = []
        for name in dirnames:
            child = Path(dirpath) / name
            try:
                if child.is_symlink():
                    continue
            except OSError:
                continue
            keep.append(name)
        dirnames[:] = keep
        yield dirpath, dirnames, filenames


def _is_map_file(name: str) -> bool:
    lowered = name.lower()
    if lowered in MAP_NAMES:
        return True
    if lowered.startswith("move_log_") and lowered.endswith(".csv"):
        return True
    if lowered.startswith("placement_audit_") and lowered.endswith(".md"):
        return True
    if lowered.startswith("doc_rename_plan") and lowered.endswith(".csv"):
        return True
    return False


def _list_tree(root: Path, max_depth: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def walk(path: Path, depth: int) -> None:
        try:
            children = sorted(path.iterdir(), key=lambda item: item.name.casefold())
        except OSError:
            return
        for child in children:
            try:
                rel = _rel_str(root, child)
                is_dir = child.is_dir() and not child.is_symlink()
                is_file = child.is_file()
            except OSError:
                continue
            if is_dir:
                rows.append({"rel": rel, "kind": "dir", "bytes": None})
                if depth < max_depth:
                    walk(child, depth + 1)
            elif is_file:
                try:
                    size = child.stat().st_size
                except OSError:
                    size = None
                rows.append({"rel": rel, "kind": "file", "bytes": size})

    walk(root, 1)
    return rows


def _path_is_user_dump(root: Path) -> bool:
    return any(part.casefold() in USER_DUMP_DIR_NAMES for part in root.parts)


def _publisher_hit(name: str) -> bool:
    return PUBLISHER_NAME_RE.search(name) is not None


def _junk_doc_hit(name: str) -> bool:
    return bool(JUNK_DOC_RE.match(name) or len(name) <= 12)


def _scientific_profile(records: list[FileRecord], names_blob: str) -> str:
    exts = {record.ext for record in records}
    has_cbf = ".cbf" in exts
    has_esg = ".esg" in exts
    texture = has_esg or TEXTURE_NAME_RE.search(names_blob) is not None
    tensile = any(AZIMUTH_NAME_RE.search(record.name) for record in records) or (
        TENSILE_NAME_RE.search(names_blob) is not None or ".fit" in exts
    )
    if has_cbf and texture:
        return "sxrd-texture"
    if tensile:
        return "sxrd-tensile"
    return "generic"


def _score_literature(
    *,
    file_count: int,
    document_class_count: int,
    publisher_id_name_count: int,
    junk_doc_name_count: int,
    pdf_count: int,
) -> BackgroundScore:
    evidence: list[str] = []
    score = 0
    ratio = (document_class_count / file_count) if file_count else 0.0
    if document_class_count >= 5:
        score += 2
        evidence.append(f"document_class_count={document_class_count}")
    if ratio >= 0.5 and document_class_count >= 3:
        score += 1
        evidence.append(f"document_ratio={ratio:.2f}")
    if publisher_id_name_count >= 2:
        score += 1
        evidence.append(f"publisher_id_name_count={publisher_id_name_count}")
    if junk_doc_name_count >= 2:
        score += 1
        evidence.append(f"junk_doc_name_count={junk_doc_name_count}")
    if pdf_count >= 8:
        score += 1
        evidence.append(f"pdf_count={pdf_count}")
    return BackgroundScore(
        family="literature",
        score=score,
        evidence=evidence,
        profile="literature-dump",
    )


def _score_desktop(
    *,
    root: Path,
    records: list[FileRecord],
    document_class_count: int,
    image_count: int,
    archive_count: int,
    installer_count: int,
    family_count: int,
) -> BackgroundScore:
    evidence: list[str] = []
    score = 0
    if _path_is_user_dump(root):
        score += 3
        evidence.append("user_dump_path")
    if image_count >= 1 and document_class_count >= 1:
        score += 2
        evidence.append(f"images={image_count}+documents={document_class_count}")
    if archive_count or installer_count:
        score += 1
        evidence.append(f"archives={archive_count},installers={installer_count}")
    if any(SCREENSHOT_NAME_RE.search(record.name) for record in records):
        score += 1
        evidence.append("screenshot_or_dump_filename")
    if family_count >= 3:
        score += 1
        evidence.append(f"extension_families={family_count}")
    loose_files = [
        record
        for record in records
        if Path(record.rel).parts
        and Path(record.rel).parts[0].casefold() in LOOSE_DIR_NAMES
    ]
    if len(loose_files) >= 3:
        score += 1
        evidence.append(f"loose_dir_files={len(loose_files)}")
    return BackgroundScore(
        family="desktop",
        score=score,
        evidence=evidence,
        profile="desktop-dump",
    )


def _score_scientific(records: list[FileRecord], names_blob: str) -> BackgroundScore:
    evidence: list[str] = []
    score = 0
    exts = {record.ext for record in records}
    cbf_count = sum(1 for record in records if record.ext == ".cbf")
    sci_count = sum(1 for record in records if record.ext in SCIENTIFIC_DATA_EXTS)
    azimuth = sum(1 for record in records if AZIMUTH_NAME_RE.search(record.name))
    texture = ".esg" in exts or TEXTURE_NAME_RE.search(names_blob) is not None
    tensile_words = TENSILE_NAME_RE.search(names_blob) is not None or ".fit" in exts
    if cbf_count:
        score += 2
        evidence.append(f"cbf_count={cbf_count}")
    if texture:
        score += 2
        evidence.append("texture_or_esg")
    if azimuth:
        score += 2
        evidence.append(f"azimuth_files={azimuth}")
    if tensile_words:
        score += 1
        evidence.append("peakfit_maud_or_fit")
    file_count = len(records)
    document_class_count = sum(1 for record in records if record.ext in DOC_EXTS)
    ratio = (document_class_count / file_count) if file_count else 0.0
    if sci_count >= 4 and ratio < 0.35:
        score += 2
        evidence.append(f"scientific_data_files={sci_count}")
    return BackgroundScore(
        family="scientific",
        score=score,
        evidence=evidence,
        profile=_scientific_profile(records, names_blob),
    )


def _score_manuscript(records: list[FileRecord]) -> BackgroundScore:
    evidence: list[str] = []
    score = 0
    hits = [record.name for record in records if MANUSCRIPT_NAME_RE.search(record.name)]
    docx_count = sum(1 for record in records if record.ext == ".docx")
    if hits:
        score += 2
        evidence.append(f"manuscript_name_hits={len(hits)}")
    if docx_count >= 3 and hits:
        score += 1
        evidence.append(f"docx_count={docx_count}")
    return BackgroundScore(
        family="manuscript",
        score=score,
        evidence=evidence,
        profile="manuscript-heavy",
    )


def _choose_profile(
    scores: list[BackgroundScore],
) -> tuple[str, bool, str, list[BackgroundScore]]:
    matched = [row for row in scores if row.matched]
    matched.sort(key=lambda row: (-row.score, row.family))
    if not matched:
        return "generic", False, "low", []
    if len(matched) == 1:
        winner = matched[0]
        return winner.profile, False, "high", []

    top, second = matched[0], matched[1]
    dominant = (
        top.score >= second.score * DOMINANCE_RATIO
        and (top.score - second.score) >= DOMINANCE_DELTA
    )
    if dominant:
        return top.profile, True, "contested", matched
    return "generic", True, "contested", matched


def _observed_clusters(
    *,
    document_class_count: int,
    image_count: int,
    archive_count: int,
    installer_count: int,
    scientific_data_count: int,
    manuscript_hits: int,
) -> list[str]:
    clusters: list[str] = []
    if document_class_count:
        clusters.append("documents")
    if image_count:
        clusters.append("images")
    if archive_count:
        clusters.append("archives")
    if installer_count:
        clusters.append("installers")
    if scientific_data_count:
        clusters.append("scientific_data")
    if manuscript_hits:
        clusters.append("manuscripts")
    return clusters


def _extension_histogram(records: list[FileRecord]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for record in records:
        key = record.ext if record.ext else "(none)"
        counts[key] = counts.get(key, 0) + 1
    return [
        {"ext": ext, "count": counts[ext]}
        for ext in sorted(counts, key=lambda item: (-counts[item], item))
    ]


def _extension_family_count(
    *,
    document_class_count: int,
    image_count: int,
    archive_count: int,
    installer_count: int,
    other_count: int,
) -> int:
    return sum(
        1
        for count in (
            document_class_count,
            image_count,
            archive_count,
            installer_count,
            other_count,
        )
        if count
    )


def collect_survey(root: str | Path, max_depth: int = 2) -> dict[str, Any]:
    """Walk ``root`` and return the public survey payload."""
    root_path = Path(root).expanduser().resolve()
    if not root_path.is_dir():
        raise FileNotFoundError(f"root folder not found: {root_path}")

    records = list(_iter_files(root_path))
    file_count = len(records)
    total_bytes = sum(record.size for record in records)
    names_blob = "|".join(record.name for record in records)

    document_class = [record for record in records if record.ext in DOC_EXTS]
    document_class_count = len(document_class)
    publisher_id_name_count = sum(
        1 for record in document_class if _publisher_hit(record.name)
    )
    junk_doc_name_count = sum(1 for record in document_class if _junk_doc_hit(record.name))
    pdf_count = sum(1 for record in records if record.ext == ".pdf")
    image_count = sum(1 for record in records if record.ext in IMAGE_EXTS)
    archive_count = sum(1 for record in records if record.ext in ARCHIVE_EXTS)
    installer_count = sum(1 for record in records if record.ext in INSTALLER_EXTS)
    scientific_data_count = sum(
        1 for record in records if record.ext in SCIENTIFIC_DATA_EXTS
    )
    other_count = file_count - (
        document_class_count + image_count + archive_count + installer_count
    )
    if other_count < 0:
        other_count = sum(
            1
            for record in records
            if record.ext not in DOC_EXTS | IMAGE_EXTS | ARCHIVE_EXTS | INSTALLER_EXTS
        )

    scores = [
        _score_literature(
            file_count=file_count,
            document_class_count=document_class_count,
            publisher_id_name_count=publisher_id_name_count,
            junk_doc_name_count=junk_doc_name_count,
            pdf_count=pdf_count,
        ),
        _score_desktop(
            root=root_path,
            records=records,
            document_class_count=document_class_count,
            image_count=image_count,
            archive_count=archive_count,
            installer_count=installer_count,
            family_count=_extension_family_count(
                document_class_count=document_class_count,
                image_count=image_count,
                archive_count=archive_count,
                installer_count=installer_count,
                other_count=max(other_count, 0),
            ),
        ),
        _score_scientific(records, names_blob),
        _score_manuscript(records),
    ]
    suggested_profile, competition, confidence, competitors = _choose_profile(scores)
    phase_d = PHASE_D_BY_PROFILE[suggested_profile]
    layout_guidance = (
        "use_named_profile"
        if suggested_profile != "generic" and confidence == "high"
        else "adapt_from_observed"
    )
    manuscript_hits = sum(
        1 for record in records if MANUSCRIPT_NAME_RE.search(record.name)
    )
    maps = sorted(
        record.rel for record in records if _is_map_file(record.name)
    )
    competing_backgrounds = [
        {
            "id": row.family,
            "profile": row.profile,
            "score": row.score,
            "phase_d_policy": FAMILY_PHASE_D[row.family],
            "evidence": list(row.evidence),
        }
        for row in competitors
    ]
    background_signals = {
        row.family: {
            "score": row.score,
            "matched": row.matched,
            "profile": row.profile,
            "evidence": list(row.evidence),
        }
        for row in scores
    }

    return {
        "schema_version": SURVEY_SCHEMA_VERSION,
        "root": str(root_path),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "suggested_profile": suggested_profile,
        "phase_d_policy": phase_d,
        "profile_confidence": confidence,
        "background_competition": competition,
        "layout_guidance": layout_guidance,
        "document_class_count": document_class_count,
        "publisher_id_name_count": publisher_id_name_count,
        "junk_doc_name_count": junk_doc_name_count,
        "observed_clusters": _observed_clusters(
            document_class_count=document_class_count,
            image_count=image_count,
            archive_count=archive_count,
            installer_count=installer_count,
            scientific_data_count=scientific_data_count,
            manuscript_hits=manuscript_hits,
        ),
        "competing_backgrounds": competing_backgrounds,
        "background_signals": background_signals,
        "extensions": _extension_histogram(records),
        "existing_maps": maps,
        "listing": _list_tree(root_path, max_depth),
    }


def format_survey_text(payload: dict[str, Any], max_depth: int = 2) -> str:
    lines = [
        f"# inventory: {payload.get('root', '')}",
        "",
        f"- file_count: {payload.get('file_count', 0)}",
        f"- total_bytes: {payload.get('total_bytes', 0)}",
        f"- suggested_profile: {payload.get('suggested_profile', 'generic')}",
        f"- phase_d_policy: {payload.get('phase_d_policy', 'optional')}",
        f"- profile_confidence: {payload.get('profile_confidence', 'low')}",
        f"- background_competition: {str(bool(payload.get('background_competition'))).lower()}",
        f"- layout_guidance: {payload.get('layout_guidance', 'adapt_from_observed')}",
        f"- document_class_count: {payload.get('document_class_count', 0)}",
        f"- publisher_id_name_count: {payload.get('publisher_id_name_count', 0)}",
        f"- junk_doc_name_count: {payload.get('junk_doc_name_count', 0)}",
    ]
    clusters = payload.get("observed_clusters") or []
    lines.append(
        "- observed_clusters: " + (", ".join(clusters) if clusters else "(none)")
    )
    competitors = payload.get("competing_backgrounds") or []
    if competitors:
        rendered = ", ".join(
            f"{row.get('id')} ({row.get('score')})" for row in competitors
        )
    else:
        rendered = "(none)"
    lines.append(f"- competing_backgrounds: {rendered}")
    lines.extend(["", "## extensions"])
    for row in payload.get("extensions") or []:
        lines.append(f"- {row.get('ext')}: {row.get('count')}")
    lines.extend(["", "## existing_maps"])
    maps = payload.get("existing_maps") or []
    if not maps:
        lines.append("- (none)")
    else:
        lines.extend(f"- {item}" for item in maps)
    lines.extend(["", f"## listing (depth <= {max_depth})"])
    for row in payload.get("listing") or []:
        lines.append(f"- [{row.get('kind')}] {row.get('rel')}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inventory a folder and score competing project backgrounds."
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-depth", type=int, default=2)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).expanduser()
    if not root.is_dir():
        print(f"ERROR: root folder not found: {root}", file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    payload = collect_survey(root, max_depth=args.max_depth)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_survey_text(payload, max_depth=args.max_depth))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
