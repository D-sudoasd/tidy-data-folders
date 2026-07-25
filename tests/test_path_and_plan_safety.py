#!/usr/bin/env python3
"""Safety tests for path containment, preflight, hash, unique destinations (hardened)."""
from __future__ import annotations

import csv
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from path_safety import (  # noqa: E402
    is_unsafe_plan_path,
    resolve_under_root,
    sha256_file,
)
import propose_doc_renames as prop  # noqa: E402


def _plan_row(**kw):
    base = {
        "plan_version": "2",
        "plan_id": "t",
        "row_id": "1",
        "approved": "true",
        "src": "a.pdf",
        "dst": "out_a.pdf",
        "action": "rename",
        "src_size": "3",
        "src_sha256": "",
    }
    base.update(kw)
    return base


def _write_plan(path: Path, rows: list[dict]) -> None:
    fields = [
        "plan_version",
        "plan_id",
        "row_id",
        "approved",
        "src",
        "dst",
        "action",
        "src_size",
        "src_sha256",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


class PathSafetyTests(unittest.TestCase):
    def test_reject_dotdot(self):
        self.assertIsNotNone(is_unsafe_plan_path("../outside/x"))
        self.assertIsNotNone(is_unsafe_plan_path("a/../../x"))

    def test_reject_absolute(self):
        self.assertIsNotNone(is_unsafe_plan_path(r"C:\Windows\x"))
        self.assertIsNotNone(is_unsafe_plan_path("/etc/passwd"))

    def test_resolve_under_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a").mkdir()
            (root / "a" / "f.txt").write_text("hi", encoding="utf-8")
            p = resolve_under_root(root, "a/f.txt")
            self.assertTrue(p.is_file())
            with self.assertRaises(ValueError):
                resolve_under_root(root, "../x")

    def test_reject_internal_symlink(self):
        if os.name == "nt":
            # creating symlinks may need admin; skip if fails
            self.skipTest("symlink create often restricted on Windows CI")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real = root / "real"
            real.mkdir()
            (real / "a.txt").write_text("x", encoding="utf-8")
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaises(ValueError):
                resolve_under_root(root, "link/a.txt", allow_symlink=False)


class ApplyPreflightTests(unittest.TestCase):
    def test_traversal_zero_move(self):
        py = sys.executable
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "proj"
            outside = Path(td) / "outside"
            root.mkdir()
            outside.mkdir()
            secret = outside / "secret.txt"
            secret.write_text("secret", encoding="utf-8")
            (root / "ok.pdf").write_bytes(b"%PDF-1.4 ok")
            plan = root / "plan.csv"
            _write_plan(
                plan,
                [
                    _plan_row(
                        src="../outside/secret.txt",
                        dst="stolen.txt",
                        src_size="6",
                        src_sha256="0" * 64,
                    )
                ],
            )
            log = root / "log.csv"
            r = subprocess.run(
                [
                    py,
                    str(SCRIPTS / "apply_doc_renames.py"),
                    "--root",
                    str(root),
                    "--plan",
                    str(plan),
                    "--move-log",
                    str(log),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 3, r.stderr + r.stdout)
            self.assertTrue(secret.exists())
            self.assertFalse((root / "stolen.txt").exists())

    def test_conflict_zero_partial(self):
        py = sys.executable
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "a.pdf"
            b = root / "b.pdf"
            a.write_bytes(b"aaa")
            b.write_bytes(b"bbb")
            ha = sha256_file(a)
            hb = sha256_file(b)
            (root / "out_b.pdf").write_bytes(b"exists")
            plan = root / "plan.csv"
            _write_plan(
                plan,
                [
                    _plan_row(
                        row_id="1",
                        src="a.pdf",
                        dst="out_a.pdf",
                        src_size=str(a.stat().st_size),
                        src_sha256=ha,
                    ),
                    _plan_row(
                        row_id="2",
                        src="b.pdf",
                        dst="out_b.pdf",
                        src_size=str(b.stat().st_size),
                        src_sha256=hb,
                    ),
                ],
            )
            r = subprocess.run(
                [
                    py,
                    str(SCRIPTS / "apply_doc_renames.py"),
                    "--root",
                    str(root),
                    "--plan",
                    str(plan),
                    "--move-log",
                    str(root / "log.csv"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 3, r.stderr + r.stdout)
            self.assertTrue(a.exists())
            self.assertTrue(b.exists())
            self.assertFalse((root / "out_a.pdf").exists())

    def test_parent_is_file_zero_partial(self):
        py = sys.executable
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "a.pdf"
            b = root / "b.pdf"
            a.write_bytes(b"aaa")
            b.write_bytes(b"bbb")
            (root / "block").write_bytes(b"notadir")
            ha, hb = sha256_file(a), sha256_file(b)
            plan = root / "plan.csv"
            _write_plan(
                plan,
                [
                    _plan_row(
                        row_id="1",
                        src="a.pdf",
                        dst="out_a.pdf",
                        src_size=str(a.stat().st_size),
                        src_sha256=ha,
                    ),
                    _plan_row(
                        row_id="2",
                        src="b.pdf",
                        dst="block/out_b.pdf",
                        src_size=str(b.stat().st_size),
                        src_sha256=hb,
                    ),
                ],
            )
            r = subprocess.run(
                [
                    py,
                    str(SCRIPTS / "apply_doc_renames.py"),
                    "--root",
                    str(root),
                    "--plan",
                    str(plan),
                    "--move-log",
                    str(root / "log.csv"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 3, r.stderr + r.stdout)
            self.assertTrue(a.exists())
            self.assertFalse((root / "out_a.pdf").exists())

    def test_missing_hash_fails(self):
        py = sys.executable
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "a.pdf"
            a.write_bytes(b"aaa")
            plan = root / "plan.csv"
            _write_plan(
                plan,
                [
                    _plan_row(
                        src="a.pdf",
                        dst="b.pdf",
                        src_size=str(a.stat().st_size),
                        src_sha256="",
                    )
                ],
            )
            r = subprocess.run(
                [
                    py,
                    str(SCRIPTS / "apply_doc_renames.py"),
                    "--root",
                    str(root),
                    "--plan",
                    str(plan),
                    "--move-log",
                    str(root / "log.csv"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 3, r.stderr + r.stdout)
            self.assertTrue(a.exists())

    def test_plan_id_mismatch(self):
        py = sys.executable
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "a.pdf"
            a.write_bytes(b"aaa")
            h = sha256_file(a)
            plan = root / "plan.csv"
            _write_plan(
                plan,
                [
                    _plan_row(
                        plan_id="OTHER",
                        src="a.pdf",
                        dst="b.pdf",
                        src_size=str(a.stat().st_size),
                        src_sha256=h,
                    )
                ],
            )
            r = subprocess.run(
                [
                    py,
                    str(SCRIPTS / "apply_doc_renames.py"),
                    "--root",
                    str(root),
                    "--plan",
                    str(plan),
                    "--move-log",
                    str(root / "log.csv"),
                    "--plan-id",
                    "EXPECTED",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 3, r.stderr + r.stdout)
            self.assertTrue(a.exists())

    def test_bad_action_fails(self):
        py = sys.executable
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "a.pdf"
            a.write_bytes(b"aaa")
            h = sha256_file(a)
            plan = root / "plan.csv"
            _write_plan(
                plan,
                [
                    _plan_row(
                        action="renmae",
                        src="a.pdf",
                        dst="b.pdf",
                        src_size=str(a.stat().st_size),
                        src_sha256=h,
                    )
                ],
            )
            r = subprocess.run(
                [
                    py,
                    str(SCRIPTS / "apply_doc_renames.py"),
                    "--root",
                    str(root),
                    "--plan",
                    str(plan),
                    "--move-log",
                    str(root / "log.csv"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 3, r.stderr + r.stdout)

    def test_unapproved_not_applied(self):
        py = sys.executable
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "a.pdf"
            a.write_bytes(b"aaa")
            h = sha256_file(a)
            plan = root / "plan.csv"
            _write_plan(
                plan,
                [
                    _plan_row(
                        approved="false",
                        src="a.pdf",
                        dst="b.pdf",
                        src_size=str(a.stat().st_size),
                        src_sha256=h,
                    )
                ],
            )
            r = subprocess.run(
                [
                    py,
                    str(SCRIPTS / "apply_doc_renames.py"),
                    "--root",
                    str(root),
                    "--plan",
                    str(plan),
                    "--move-log",
                    str(root / "log.csv"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue(a.exists())
            self.assertFalse((root / "b.pdf").exists())


class OutOverwriteTests(unittest.TestCase):
    def test_extract_refuses_source_out(self):
        py = sys.executable
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            victim = root / "victim.doc"
            victim.write_bytes(b"DOCDATA")
            before = victim.read_bytes()
            r = subprocess.run(
                [
                    py,
                    str(SCRIPTS / "extract_doc_meta.py"),
                    "--root",
                    str(root),
                    "--out",
                    str(victim),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertEqual(victim.read_bytes(), before)

    def test_propose_refuses_source_out(self):
        py = sys.executable
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            victim = root / "victim.pdf"
            victim.write_bytes(b"%PDF")
            meta = root / "meta.jsonl"
            meta.write_text(
                '{"rel":"victim.pdf","name":"victim.pdf","ext":".pdf","sha256_full":"'
                + hashlib.sha256(b"%PDF").hexdigest()
                + '","bytes":4,"extract_supported":true}\n',
                encoding="utf-8",
            )
            before = victim.read_bytes()
            r = subprocess.run(
                [
                    py,
                    str(SCRIPTS / "propose_doc_renames.py"),
                    "--root",
                    str(root),
                    "--meta",
                    str(meta),
                    "--out",
                    str(victim),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertEqual(victim.read_bytes(), before)


class HashAndNameTests(unittest.TestCase):
    def test_quick_vs_full_hash(self):
        from extract_doc_meta import quick_fingerprint, sha256_full

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            head = b"X" * (2 * 1024 * 1024)
            f1 = root / "a.bin"
            f2 = root / "b.bin"
            f1.write_bytes(head + b"AAAA" + b"\0" * 96)
            f2.write_bytes(head + b"BBBB" + b"\0" * 96)
            self.assertEqual(f1.stat().st_size, f2.stat().st_size)
            self.assertEqual(quick_fingerprint(f1), quick_fingerprint(f2))
            self.assertNotEqual(sha256_full(f1), sha256_full(f2))

    def test_chinese_short_title(self):
        st, _ = prop.short_title("高熵合金 HEA 的变形机制研究", "x.pdf")
        self.assertIn("高熵合金", st)
        self.assertIn("HEA", st)

    def test_good_name_move_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            name = "2024_SciRep_Smith_GoodTitle.pdf"
            (root / name).write_bytes(b"%PDF fake")
            rec = {
                "rel": name,
                "name": name,
                "ext": ".pdf",
                "title": "Good Title for Materials Science Research Paper",
                "authors": ["Smith"],
                "year": 2024,
                "sha256_full": hashlib.sha256(b"%PDF fake").hexdigest(),
                "content_hash_short": "abcd1234",
                "bytes": 9,
                "mtime_utc": "2024-01-01T00:00:00Z",
                "filename_signals": {
                    "filename_year": 2024,
                    "filename_looks_academic": True,
                    "filename_has_publisher_id": False,
                },
                "class_snip": "abstract references doi",
                "extract_supported": True,
            }
            h = {rec["sha256_full"]: name}
            pl = prop.propose_one(
                rec, root, "academic", "literature-dump", 120, h, "pid", 1
            )
            self.assertEqual(pl["action"], "move_only")
            self.assertTrue(pl["dst"].endswith(name))
            # after allocate, still same basename
            prop.allocate_unique_dsts([pl], root)
            self.assertEqual(Path(pl["dst"]).name, name)
            self.assertIn(pl["action"], {"move_only", "keep", "review"})

    def test_unique_dst_allocation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plans = [
                {
                    "action": "rename",
                    "src": "a.pdf",
                    "dst": "01_papers/Same.pdf",
                    "content_hash_short": "aaa1",
                    "src_sha256": "x",
                    "reason_codes": "",
                },
                {
                    "action": "rename",
                    "src": "b.pdf",
                    "dst": "01_papers/Same.pdf",
                    "content_hash_short": "bbb2",
                    "src_sha256": "y",
                    "reason_codes": "",
                },
            ]
            prop.allocate_unique_dsts(plans, root)
            self.assertNotEqual(plans[0]["dst"].casefold(), plans[1]["dst"].casefold())

    def test_review_dst_equals_src_after_allocate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "to_sort").mkdir()
            (root / "to_sort" / "main.pdf").write_bytes(b"x")
            plans = [
                {
                    "action": "review",
                    "src": "to_sort/main.pdf",
                    "dst": "to_sort/main.pdf",
                    "content_hash_short": "abcd",
                    "src_sha256": "z",
                    "reason_codes": "",
                }
            ]
            prop.allocate_unique_dsts(plans, root)
            self.assertEqual(plans[0]["dst"], plans[0]["src"])
            self.assertEqual(plans[0]["action"], "review")

    def test_already_placed_keep(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            slot = root / "01_papers"
            slot.mkdir()
            name = "2024_SciRep_Smith_GoodTitle.pdf"
            (slot / name).write_bytes(b"%PDF fake")
            rel = f"01_papers/{name}"
            rec = {
                "rel": rel,
                "name": name,
                "ext": ".pdf",
                "title": "Good Title for Materials Science Research Paper",
                "authors": ["Smith"],
                "year": 2024,
                "sha256_full": hashlib.sha256(b"%PDF fake").hexdigest(),
                "content_hash_short": "abcd1234",
                "bytes": 9,
                "mtime_utc": "2024-01-01T00:00:00Z",
                "filename_signals": {
                    "filename_year": 2024,
                    "filename_looks_academic": True,
                    "filename_has_publisher_id": False,
                },
                "class_snip": "abstract references",
                "extract_supported": True,
            }
            h = {rec["sha256_full"]: rel}
            pl = prop.propose_one(
                rec, root, "academic", "literature-dump", 120, h, "pid", 1
            )
            prop.allocate_unique_dsts([pl], root)
            self.assertIn(pl["action"], {"keep", "move_only", "review"})
            if pl["action"] == "keep":
                self.assertEqual(pl["dst"], pl["src"])
            else:
                self.assertEqual(Path(pl["dst"]).name, name)

    def test_invoice_prefers_labeled_number(self):
        blob = "发票号码 12345678\n纳税人识别号 913101151234567890\n银行账号 6222021234567890123"
        num = prop.extract_invoice_number(blob)
        self.assertEqual(num, "12345678")

    def test_human_differs_from_academic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "p.pdf").write_bytes(b"%PDF")
            rec = {
                "rel": "p.pdf",
                "name": "p.pdf",
                "ext": ".pdf",
                "title": "High Entropy Alloy Deformation Mechanisms Study",
                "authors": ["Zhang"],
                "year": 2024,
                "sha256_full": hashlib.sha256(b"%PDF").hexdigest(),
                "content_hash_short": "abcd",
                "bytes": 4,
                "filename_signals": {},
                "class_snip": "abstract references doi journal",
                "extract_supported": True,
            }
            h = {rec["sha256_full"]: "p.pdf"}
            pa = prop.propose_one(rec, root, "academic", "none", 120, h, "pid", 1)
            ph = prop.propose_one(rec, root, "human", "none", 120, h, "pid", 2)
            self.assertNotEqual(Path(pa["dst"]).name, Path(ph["dst"]).name)

    def test_propose_requires_root(self):
        py = sys.executable
        r = subprocess.run(
            [
                py,
                str(SCRIPTS / "propose_doc_renames.py"),
                "--root",
                str(Path(tempfile.gettempdir()) / "no_such_root_xyz"),
                "--meta",
                str(SCRIPTS / "propose_doc_renames.py"),
                "--out",
                str(Path(tempfile.gettempdir()) / "out.csv"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(r.returncode, 0)


class MeetingNotesTypeTests(unittest.TestCase):
    def test_meeting_not_paper(self):
        rec = {
            "name": "notes.docx",
            "ext": ".docx",
            "title": "Weekly Project Meeting Notes",
            "class_snip": "Attendees discussed schedule and budget for the weekly project meeting notes.",
            "filename_signals": {},
            "extract_supported": True,
        }
        dt, codes = prop.guess_doc_type(rec)
        self.assertEqual(dt, "notes")
        self.assertNotEqual(dt, "paper")


if __name__ == "__main__":
    unittest.main()
