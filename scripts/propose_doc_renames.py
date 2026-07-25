#!/usr/bin/env python3
"""Propose document renames from extract_doc_meta JSONL (hardened v0.2)."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from path_safety import normalize_rel, resolve_under_root, sha256_file  # noqa: E402

ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
MULTI_US = re.compile(r"_+")

VENUE_SLUGS = {
    "advanced materials": "AdvMater",
    "acta materialia": "ActaMater",
    "scripta materialia": "ScriptaMater",
    "materials science and engineering a": "MSEA",
    "journal of alloys and compounds": "JALCOM",
    "nature communications": "NatCommun",
    "scientific reports": "SciRep",
    "metals": "Metals",
    "advanced engineering materials": "AdvEngMater",
    "progress in materials science": "ProgMaterSci",
    "journal of materials science & technology": "JMST",
    "journal of materials science and technology": "JMST",
    "materials & design": "MaterDes",
    "materials and design": "MaterDes",
    "international journal of plasticity": "IJP",
    "materials research letters": "MaterResLett",
}

SLOT = {
    "paper": "01_papers",
    "review": "01_papers",
    "figure_export": "03_figures_exports",
    "notes": "02_other_docs",
    "report": "02_other_docs",
    "slides": "02_other_docs",
    "datasheet": "02_other_docs",
    "thesis": "02_other_docs",
    "patent": "02_other_docs",
    "unknown": "to_sort",
}

STOP_TITLE = re.compile(
    r"^(a|an|the|study|of|on|towards|toward|based|using|via|for|and|in|with)\b",
    re.I,
)

BAD_TITLE_RE = re.compile(
    r"journal pre-proof|article in press|pii:|microsoft (word|powerpoint)|"
    r"电子发票|发票号码|accepted manuscript|^proofs?\b",
    re.I,
)

PLAN_FIELDS = [
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
]


def sanitize_stem(stem: str, max_len: int = 120) -> str:
    s = ILLEGAL.sub("_", stem)
    s = s.replace("—", "-").replace("–", "-").replace("‐", "-")
    s = s.replace(" ", "_").replace("\t", "_")
    s = re.sub(r"[^\w\u4e00-\u9fff\-.]+", "_", s, flags=re.UNICODE)
    s = MULTI_US.sub("_", s).strip("._ ")
    if len(s) > max_len:
        s = s[:max_len].rstrip("._-")
    if not s:
        s = "untitled"
    if s.upper() in {"CON", "PRN", "AUX", "NUL"} or re.match(
        r"^(COM|LPT)\d$", s.upper()
    ):
        s = f"_{s}"
    return s


def clean_title(title: str) -> str:
    t = (title or "").strip()
    if not t or BAD_TITLE_RE.search(t):
        return ""
    if t.lower().startswith("pii:"):
        return ""
    if re.search(
        r"creative commons|providing this early version|graduate institute|"
        r"national laboratory|corresponding author",
        t,
        re.I,
    ):
        return ""
    if re.search(r"\b(Institute|University|Laboratory|Department)\b", t) and len(t) < 100:
        return ""
    if re.match(r"^[\d\s.]+$", t):
        return ""
    return t


def venue_slug(venue: str, filename: str) -> str:
    v = (venue or "").strip()
    if v:
        key = re.sub(r"\s+", " ", v.lower())
        if key in VENUE_SLUGS:
            return VENUE_SLUGS[key]
        words = re.findall(r"[A-Za-z]+", v)
        words = [
            w
            for w in words
            if w.lower() not in {"the", "of", "and", "journal", "an", "a"}
        ]
        if words:
            slug = "".join(w[:1].upper() + w[1:] for w in words[:3])
            return sanitize_stem(slug, 16)
    fl = filename.lower()
    if "metals-" in fl:
        return "Metals"
    if "s41598" in fl:
        return "SciRep"
    if "s41467" in fl:
        return "NatCommun"
    if "advanced materials" in fl:
        return "AdvMater"
    if "advancedengineeringmaterials" in fl.replace(" ", "").replace("_", "").lower():
        return "AdvEngMater"
    if "1-s2.0-s09215093" in fl:
        return "MSEA"
    if "1-s2.0-s09258388" in fl:
        return "JALCOM"
    if "1-s2.0-s1359645" in fl:
        return "ActaMater"
    return "UnknownVenue"


def first_author(authors: list, filename: str) -> tuple[str, str]:
    if authors:
        a = authors[0]
        parts = re.findall(r"[\w\u4e00-\u9fff\-']+", a, flags=re.UNICODE)
        if not parts:
            return "Anon", "none"
        if re.search(r"[\u4e00-\u9fff]", a):
            return sanitize_stem(parts[0], 20), "extract"
        return sanitize_stem(parts[-1], 24), "extract"
    if " - " in filename:
        parts = Path(filename).stem.split(" - ")
        if len(parts) >= 3:
            return sanitize_stem(parts[2].split()[0], 24), "filename"
    return "Anon", "none"


def short_title(title: str, filename: str, max_tokens: int = 7) -> tuple[str, str]:
    """Return (short_title, source). Preserves Chinese + meaningful English (F-11)."""
    t = clean_title(title) if title else ""
    source = "extract" if t else "filename"
    if not t and " - " in filename:
        parts = Path(filename).stem.split(" - ")
        if len(parts) >= 4:
            t = " - ".join(parts[3:])
            source = "filename"
    if not t:
        stem = Path(filename).stem
        if re.match(r"1-s2\.0-", stem, re.I) or re.match(r"s\d+-", stem):
            return "Untitled", "none"
        m = re.match(r"^(?:19|20)\d{2}_[A-Za-z]+_(.+)$", stem)
        t = m.group(1) if m else stem
        source = "filename"

    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", t))
    if has_cjk:
        # keep CJK runs and meaningful Latin tokens (HEA, SXRD, MAUD, …)
        parts = re.findall(
            r"[\u4e00-\u9fff]+|[A-Za-z][A-Za-z0-9\-]{1,}|[0-9]+(?:\.[0-9]+)?",
            t,
        )
        # drop pure stop English
        keep = []
        for p in parts:
            if re.fullmatch(r"[A-Za-z]+", p) and STOP_TITLE.match(p):
                continue
            keep.append(p)
        if not keep:
            return "Untitled", source
        # join CJK without underscore between CJK-only? use _ between mixed
        out = []
        for p in keep[:10]:
            out.append(p)
        return sanitize_stem("_".join(out), 60), source

    t2 = re.sub(r"[^\w\s\u4e00-\u9fff\-]", " ", t, flags=re.UNICODE)
    tokens = [x for x in re.split(r"\s+", t2.strip()) if x]
    while tokens and STOP_TITLE.match(tokens[0]) and len(tokens) > 2:
        tokens = tokens[1:]
    en = [tok for tok in tokens if re.search(r"[A-Za-z0-9]", tok)]
    if en:
        return sanitize_stem("_".join(en[:max_tokens]), 60), source
    return "Untitled", source


def guess_doc_type(rec: dict) -> tuple[str, list[str]]:
    name = rec.get("name") or ""
    text = (rec.get("class_snip") or rec.get("text_snip") or "")[:1500]
    title = clean_title(rec.get("title") or "")
    blob = (title + " " + name + " " + text).lower()
    pages = rec.get("page_count") or 0
    snip_len = len(text)
    codes: list[str] = []

    ext = (rec.get("ext") or Path(name).suffix).lower()
    if ext == ".pptx" or ext == ".ppt":
        return "slides", ["ext_pptx"]
    if ext in {".xlsx", ".xlsm"}:
        return "unknown", ["spreadsheet_review"]
    if ext in {".doc"}:
        return "unknown", ["legacy_doc"]

    if re.search(r"电子发票|发票号码|增值税", blob):
        return "report", ["invoice"]
    if re.search(r"\bpatent\b|专利权|权利要求", blob):
        return "patent", ["patent_signal"]
    if re.search(r"\bthesis\b|dissertation|学位论文|博士|硕士论文", blob):
        return "thesis", ["thesis_signal"]
    if re.search(
        r"meeting notes|minutes of|会议纪要|项目例会|weekly project",
        blob,
    ):
        return "notes", ["meeting_notes"]
    if re.search(r"\bmanual\b|操作手册|说明书|user guide", blob):
        return "report", ["manual"]

    if rec.get("is_likely_scanned") and snip_len < 40:
        if pages and pages <= 3:
            return "figure_export", ["few_pages_low_text"]
        return "unknown", ["likely_scanned"]

    paper_signals = 0
    if rec.get("doi"):
        paper_signals += 1
        codes.append("doi")
    if re.search(r"\babstract\b|摘要", blob):
        paper_signals += 1
        codes.append("abstract")
    if re.search(r"\breferences\b|参考文献", blob):
        paper_signals += 1
        codes.append("references")
    if re.search(
        r"elsevier|springer|wiley|elsevier|acta materialia|scientific reports|"
        r"nature communications|\bdoi\b",
        blob,
    ):
        paper_signals += 1
        codes.append("publisher")
    if rec.get("authors") and title and len(title) > 20:
        paper_signals += 1
        codes.append("title_authors")
    if (rec.get("filename_signals") or {}).get("filename_has_publisher_id"):
        paper_signals += 1
        codes.append("publisher_filename")

    if re.search(r"\breview\b|综述|recent progress and challenges", blob) and paper_signals >= 1:
        return "review", codes + ["review_word"]

    if paper_signals >= 2:
        return "paper", codes

    if pages and pages <= 2 and snip_len < 120:
        return "figure_export", ["short_pdf"]
    if re.search(r"datasheet|specification", blob):
        return "datasheet", ["datasheet"]
    if name.lower() in {"saxs.pdf", "数据.pdf"} or re.match(r"^\d+\s*图片", name):
        return ("notes" if "图片" not in name else "figure_export"), ["short_name"]
    if "powerpoint" in blob:
        return "notes", ["pptx_export_pdf"]
    # F-10: do NOT classify as paper only because text is long
    if title and len(title) > 20 and paper_signals == 1:
        return "unknown", codes + ["weak_paper"]
    return "unknown", codes + ["no_strong_type"]


def effective_year(rec: dict) -> tuple[int | None, str]:
    """Prefer filename year over body year (F-12)."""
    fy = (rec.get("filename_signals") or {}).get("filename_year")
    if not fy:
        m = re.match(r"^((?:19|20)\d{2})_", rec.get("name") or "")
        if m:
            fy = int(m.group(1))
    if fy and 1980 <= int(fy) <= 2035:
        return int(fy), "filename"

    # Wiley style in name
    if " - " in (rec.get("name") or ""):
        parts = Path(rec["name"]).stem.split(" - ")
        if len(parts) >= 2 and re.fullmatch(r"(19|20)\d{2}", parts[1].strip()):
            return int(parts[1].strip()), "filename"

    y = rec.get("year")
    if y:
        try:
            yi = int(y)
            if 1990 <= yi <= 2035:
                return yi, rec.get("year_source") or "body_or_meta"
            if 1980 <= yi < 1990 and clean_title(rec.get("title") or ""):
                return yi, rec.get("year_source") or "body_or_meta"
        except (TypeError, ValueError):
            pass
    return None, "none"


def already_good_name(name: str) -> bool:
    stem = Path(name).stem
    return bool(re.match(r"^(19|20)\d{2}_[A-Za-z][A-Za-z0-9]+_[A-Za-z]", stem))


def score_confidence(
    rec: dict, doc_type: str, title: str, year, codes: list[str]
) -> float:
    c = 0.35
    if rec.get("doi"):
        c += 0.2
    if title and len(title) > 15:
        c += 0.25
    if year:
        c += 0.1
    if rec.get("authors"):
        c += 0.08
    if doc_type in {"paper", "review"} and title:
        c += 0.05
    if doc_type == "report" and "invoice" in codes:
        c = 0.8
    if doc_type == "slides":
        c = max(c, 0.7)
    if rec.get("is_likely_scanned"):
        c -= 0.25
    if rec.get("error"):
        c -= 0.15
    if not rec.get("extract_supported", True):
        c = min(c, 0.4)
    if doc_type == "unknown":
        c = min(c, 0.5)
    return max(0.05, min(0.98, c))


def extract_invoice_number(blob: str) -> str | None:
    """Only take explicitly labeled invoice numbers; never tax id / bank account."""
    if not blob:
        return None
    # exclude sensitive labels neighborhoods
    blocked = re.compile(
        r"(纳税人识别号|税号|统一社会信用代码|银行账号|账号|身份证|电话|手机)",
        re.I,
    )
    m = re.search(r"发票号码\s*[:：]?\s*([0-9]{8,20})", blob)
    if m:
        # ensure not immediately after a blocked label in a wider window
        start = max(0, m.start() - 12)
        window = blob[start : m.end()]
        if blocked.search(window) and "发票号码" not in window:
            return None
        return m.group(1)
    m2 = re.search(r"(?i)invoice\s*(?:no|number|#)?\s*[:：]?\s*([0-9]{8,20})", blob)
    if m2:
        return m2.group(1)
    return None


def build_type_stem(
    rec: dict,
    doc_type: str,
    title: str,
    year,
    author: str,
    st: str,
    max_stem: int,
    profile: str,
) -> str:
    blob_id = (rec.get("name") or "") + (rec.get("class_snip") or "")[:300]
    invoice_like = (
        rec.get("has_invoice_label")
        or "invoice" in blob_id.lower()
        or re.search(r"发票", blob_id)
    )
    if doc_type == "report" and invoice_like:
        num = extract_invoice_number(blob_id)
        if not num:
            h4 = (rec.get("content_hash_short") or rec.get("sha256_full") or "xxxx")[:4]
            return sanitize_stem(f"Invoice_review_{h4}", max_stem)
        return sanitize_stem(f"Invoice_{num}", max_stem)

    y = str(year) if year else ""
    if profile == "human":
        parts = [p for p in (y, st, author if author not in {"Anon", "Team", ""} else "") if p]
        return sanitize_stem("_".join(parts) if parts else st or "untitled", max_stem)

    # type-specific short templates (non-paper)
    if doc_type == "notes":
        base = "_".join(p for p in (y, st, "notes") if p)
        return sanitize_stem(base, max_stem)
    if doc_type == "slides":
        parts = [p for p in (y, st, "slides", author if author not in {"Anon", "Team"} else "") if p]
        return sanitize_stem("_".join(parts), max_stem)
    if doc_type == "report":
        parts = [p for p in (y, st or "report", "report") if p]
        return sanitize_stem("_".join(parts), max_stem)
    if doc_type == "thesis":
        parts = [p for p in (y, author if author != "Anon" else "", st, "thesis") if p]
        return sanitize_stem("_".join(parts), max_stem)
    if doc_type == "patent":
        parts = [p for p in (y, st, "patent") if p]
        return sanitize_stem("_".join(parts), max_stem)
    if doc_type == "figure_export":
        parts = [p for p in (y, st, "figures") if p]
        return sanitize_stem("_".join(parts), max_stem)

    # academic paper / review
    venue = venue_slug(rec.get("venue") or "", rec.get("name") or "")
    tag = "_Review" if doc_type == "review" else ""
    y2 = y or "Undated"
    return sanitize_stem(f"{y2}_{venue}_{author}_{st}{tag}", max_stem)


def allocate_unique_dsts(plans: list[dict], root: Path) -> None:
    """Ensure unique destinations; never collide with own src; preserve move_only basename."""
    used: set[str] = set()
    for p in root.rglob("*"):
        if p.is_file() or p.is_dir():
            try:
                rel = str(p.relative_to(root)).replace("\\", "/")
                used.add(rel.casefold())
            except ValueError:
                pass

    for pl in plans:
        action = pl.get("action") or ""
        src = (pl.get("src") or "").replace("\\", "/")
        src_cf = src.casefold()

        if action in {"keep", "protected", "review"}:
            pl["dst"] = src
            used.add(src_cf)
            continue

        dst = (pl.get("dst") or "").replace("\\", "/")
        # already perfect placement
        if dst.casefold() == src_cf:
            used.add(src_cf)
            continue

        src_name = Path(src).name
        if action == "move_only" and Path(dst).name != src_name:
            pl["action"] = "review"
            pl["dst"] = src
            pl["reason_codes"] = (pl.get("reason_codes") or "") + ";move_only_basename_guard"
            used.add(src_cf)
            continue

        def free(d: str) -> bool:
            cf = d.casefold()
            if cf == src_cf:
                return True
            return cf not in used

        if free(dst):
            pl["dst"] = dst
            used.add(dst.casefold())
            # free source path for others after this would move (optional)
            continue

        # conflict
        if action == "move_only":
            # cannot rename basename to resolve conflict
            pl["action"] = "review"
            pl["dst"] = src
            pl["reason_codes"] = (pl.get("reason_codes") or "") + ";dst_collision_review"
            used.add(src_cf)
            continue

        h4 = (pl.get("content_hash_short") or pl.get("src_sha256") or "xxxx")[:4]
        path = Path(dst)
        stem, ext = path.stem, path.suffix
        if stem.endswith("_dup"):
            stem = stem[: -len("_dup")] + f"_dup_{h4}"
        else:
            stem = f"{stem}_{h4}"
        new_dst = str(path.with_name(stem + ext)).replace("\\", "/")
        n = 2
        while not free(new_dst):
            new_dst = str(path.with_name(f"{stem}_{n}{ext}")).replace("\\", "/")
            n += 1
        pl["dst"] = new_dst
        pl["reason_codes"] = (pl.get("reason_codes") or "") + ";dst_dedupe"
        if action == "move_only":
            # basename changed → must not stay move_only
            pl["action"] = "rename"
            pl["reason_codes"] += ";action_upgraded_rename"
        used.add(pl["dst"].casefold())


def propose_one(
    rec: dict,
    root: Path,
    profile: str,
    slot_layout: str,
    max_stem: int,
    hash_to_primary: dict,
    plan_id: str,
    row_id: int,
) -> dict | None:
    rel = normalize_rel(rec.get("rel") or rec.get("name") or "")
    if not rel:
        return None
    # verify under root
    try:
        src_path = resolve_under_root(root, rel, allow_symlink=False)
    except ValueError:
        return {
            "plan_version": "2",
            "plan_id": plan_id,
            "row_id": str(row_id),
            "approved": "false",
            "src": rel,
            "dst": rel,
            "action": "protected",
            "doc_type": "unknown",
            "confidence": "0.00",
            "reason": "path escapes root or unsafe",
            "reason_codes": "unsafe_path",
            "doi": "",
            "title": "",
            "year": "",
            "year_source": "",
            "title_source": "",
            "author_source": "",
            "src_size": "",
            "src_mtime_utc": "",
            "src_sha256": "",
            "content_hash_short": "",
        }

    name = rec.get("name") or Path(rel).name
    ext = (rec.get("ext") or Path(name).suffix).lower()
    title = clean_title(rec.get("title") or "")
    title_source = "extract" if title else "none"
    year, year_source = effective_year(rec)
    doc_type, type_codes = guess_doc_type(rec)
    author, author_source = first_author(rec.get("authors") or [], name)
    st, st_source = short_title(title, name)
    if st_source != "none" and title_source == "none":
        title_source = st_source

    hfull = rec.get("sha256_full") or rec.get("content_hash") or ""
    if not hfull and src_path.is_file():
        hfull = sha256_file(src_path)
    hshort = (rec.get("content_hash_short") or hfull[:8] or "")[:8]
    size = rec.get("bytes") or (src_path.stat().st_size if src_path.is_file() else "")
    mtime = rec.get("mtime_utc") or ""

    conf = score_confidence(rec, doc_type, title, year, type_codes)
    reason_codes = list(type_codes)

    # default action path
    action = "rename"
    reason = "content identity"
    stem = build_type_stem(rec, doc_type, title, year, author, st, max_stem, profile)
    dst_name = stem + ext

    if profile == "normalize":
        # sanitize basename only — no semantic academic rebuild
        stem = sanitize_stem(Path(name).stem, max_stem)
        dst_name = stem + ext
        action = "normalize"
        reason = "normalize only"
        if dst_name == name:
            action = "keep"
            reason = "already normalized"

    # F-08: good academic name → keep basename, slot move only
    if already_good_name(name) and profile not in {"normalize"}:
        action = "move_only"
        dst_name = name
        reason = "keep good basename; slot placement only"
        reason_codes.append("good_name_keep_basename")
        conf = max(conf, 0.9)

    # invoice special stem
    if "invoice" in type_codes:
        action = "rename"
        reason = "invoice/report identity"
        stem = build_type_stem(rec, doc_type, title, year, author, st, max_stem, profile)
        dst_name = stem + ext
        if "Invoice_review_" in stem:
            reason_codes.append("sensitive_field_risk")

    # F-04/F-05 duplicates: full hash only
    if hfull and hfull in hash_to_primary and hash_to_primary[hfull] != rel:
        primary = hash_to_primary[hfull]
        if already_good_name(name):
            # keep basename, mark dup via folder; action rename if we must change name
            action = "rename"
            stem = sanitize_stem(Path(name).stem + f"_dup_{hshort[:4]}", max_stem)
            dst_name = stem + ext
        else:
            action = "rename"
            stem = sanitize_stem(Path(dst_name).stem + f"_dup_{hshort[:4]}", max_stem)
            dst_name = stem + ext
        reason = f"duplicate of {primary}"
        reason_codes.append("sha256_dup")
        conf = max(conf, 0.85)

    # low confidence → review; with slots use move_only to to_sort (F-09)
    low = conf < 0.55 or doc_type == "unknown" or st == "Untitled" and not rec.get("doi")
    if low and action not in {"move_only"} and "sha256_dup" not in reason_codes:
        if slot_layout == "literature-dump":
            action = "move_only"
            dst_name = name  # keep original name
            reason = "low confidence → to_sort keep basename"
            reason_codes.append("review_move_only")
        else:
            action = "review"
            dst_name = name
            reason = "low confidence review in place"
            reason_codes.append("review")

    if not rec.get("extract_supported", True) and ext not in {".pdf", ".docx"}:
        action = "review"
        dst_name = name
        reason = "format not auto-renamed"
        reason_codes.append("unsupported_format")

    # slots
    if slot_layout == "literature-dump":
        if "sha256_dup" in reason_codes:
            slot = "99_archive"
        elif action == "move_only" and "review_move_only" in reason_codes:
            slot = "to_sort"
        elif action in {"rename", "normalize", "move_only"}:
            slot = SLOT.get(doc_type, "to_sort")
        else:
            slot = ""
        if slot and action != "review":
            dst = f"{slot}/{dst_name}"
        elif action == "review":
            dst = rel
        else:
            dst = dst_name
    else:
        parent = str(Path(rel).parent).replace("\\", "/")
        if parent in (".", ""):
            dst = dst_name if action not in {"review", "keep", "protected"} else rel
        else:
            dst = (
                f"{parent}/{dst_name}"
                if action not in {"review", "keep", "protected"}
                else rel
            )

    if action in {"keep", "protected"}:
        dst = rel

    # publisher-style long name → real rename (not false normalize)
    if action == "rename" and " - " in name and year and profile != "normalize":
        reason = "rename long publisher-style name"
        reason_codes.append("publisher_style_name")

    # perfect already: same path after slotting
    dst = dst.replace("\\", "/")
    if action in {"rename", "normalize", "move_only"} and dst.casefold() == rel.casefold():
        action = "keep"
        reason = "already at target path"
        reason_codes.append("already_placed")
        dst = rel

    # move_only basename invariant
    if action == "move_only" and Path(dst).name != Path(rel).name:
        action = "review"
        dst = rel
        reason_codes.append("move_only_basename_guard")

    return {
        "plan_version": "2",
        "plan_id": plan_id,
        "row_id": str(row_id),
        "approved": "false",
        "src": rel,
        "dst": dst,
        "action": action,
        "doc_type": doc_type,
        "confidence": f"{conf:.2f}",
        "reason": reason,
        "reason_codes": ";".join(reason_codes),
        "doi": rec.get("doi") or "",
        "title": (title or "")[:180],
        "year": year or "",
        "year_source": year_source,
        "title_source": title_source,
        "author_source": author_source,
        "src_size": str(size),
        "src_mtime_utc": mtime,
        "src_sha256": hfull,
        "content_hash_short": hshort,
    }


def load_meta(path: Path) -> list:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--meta", required=True, help="JSONL from extract_doc_meta.py")
    ap.add_argument("--out", required=True, help="CSV plan path")
    ap.add_argument(
        "--profile", default="academic", choices=["academic", "human", "normalize"]
    )
    ap.add_argument(
        "--slot-layout",
        default="literature-dump",
        choices=["literature-dump", "none"],
    )
    ap.add_argument("--max-stem", type=int, default=120)
    ap.add_argument("--plan-id", default="", help="Plan id (default auto)")
    ap.add_argument(
        "--overwrite-generated-output",
        action="store_true",
        help="Allow overwriting an existing plan CSV (never sources)",
    )
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Root not found: {root}", file=sys.stderr)
        return 2

    meta_path = Path(args.meta)
    if not meta_path.is_file():
        print(f"meta not found: {meta_path}", file=sys.stderr)
        return 2

    out = Path(args.out)
    if out.suffix.lower() != ".csv":
        print("ERROR: --out must end with .csv", file=sys.stderr)
        return 2
    # refuse overwriting source docs / meta
    try:
        out_res = out.resolve() if out.exists() else out
        meta_res = meta_path.resolve()
        if out.exists() and not args.overwrite_generated_output:
            print(f"ERROR: output exists (refuse overwrite): {out}", file=sys.stderr)
            return 2
        if out_res == meta_res:
            print("ERROR: --out collides with --meta", file=sys.stderr)
            return 2
        # if out is under root and equals a scanned document
        try:
            rel_out = str(out_res.relative_to(root)).replace("\\", "/")
            if out.exists() and out.suffix.lower() in {
                ".pdf",
                ".docx",
                ".doc",
                ".pptx",
                ".ppt",
                ".xlsx",
                ".xlsm",
            }:
                print(f"ERROR: --out collides with document path: {rel_out}", file=sys.stderr)
                return 2
        except ValueError:
            pass
    except OSError as e:
        print(f"ERROR: cannot validate --out: {e}", file=sys.stderr)
        return 2

    plan_id = args.plan_id or (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    )
    records = load_meta(meta_path)

    # full-hash groups only
    hash_groups: dict[str, list] = defaultdict(list)
    for rec in records:
        h = rec.get("sha256_full") or rec.get("content_hash")
        if h:
            hash_groups[h].append(rec)

    def primary_key(rec):
        name = rec.get("name") or ""
        penalty = 0
        if re.search(r"\(\d+\)", name):
            penalty += 10
        if re.search(r"copy|副本", name, re.I):
            penalty += 10
        if re.match(r"1-s2\.0-|main", name, re.I):
            penalty += 1
        return (penalty, len(name), name)

    hash_to_primary = {}
    for h, group in hash_groups.items():
        best = sorted(group, key=primary_key)[0]
        hash_to_primary[h] = normalize_rel(best.get("rel") or best.get("name"))

    plans = []
    row_id = 0
    for rec in records:
        row_id += 1
        pl = propose_one(
            rec,
            root,
            args.profile,
            args.slot_layout,
            args.max_stem,
            hash_to_primary,
            plan_id,
            row_id,
        )
        if pl:
            plans.append(pl)

    allocate_unique_dsts(plans, root)

    # final uniqueness assert
    dsts = [p["dst"].casefold() for p in plans if p["action"] not in {"keep", "review", "protected"}]
    if len(dsts) != len(set(dsts)):
        print("ERROR: duplicate destinations remain after allocation", file=sys.stderr)
        return 3

    out.parent.mkdir(parents=True, exist_ok=True)
    import io
    import os

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=PLAN_FIELDS, extrasaction="ignore")
    w.writeheader()
    for row in plans:
        w.writerow(row)
    text = buf.getvalue()
    tmp = out.with_name(out.name + f".tmp.{os.getpid()}")
    try:
        with tmp.open("w", encoding="utf-8-sig", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, out)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass

    by_action = defaultdict(int)
    for p in plans:
        by_action[p["action"]] += 1
    print(f"wrote {len(plans)} rows -> {out}")
    print(f"plan_id: {plan_id}")
    print("approved: all false (set approved=true after user confirms)")
    for k, v in sorted(by_action.items()):
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
