#!/usr/bin/env python3
"""Drive the shipped survey / background-signal path on constructed trees."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
import sys

sys.path.insert(0, str(SCRIPTS))

import survey_signals  # noqa: E402
import tidy  # noqa: E402

DOC_EXTS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xlsm"}
SXRD_PROFILES = {"sxrd-texture", "sxrd-tensile"}


def _write(path: Path, data: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _real_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file()]


def _survey(root: Path) -> dict:
    return survey_signals.collect_survey(root)


def _competitor_ids(payload: dict) -> set[str]:
    return {str(row["id"]) for row in payload.get("competing_backgrounds") or []}


class LiteratureBackgroundTests(unittest.TestCase):
    def test_publisher_pdf_dump_is_literature(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in (
                "1-s2.0-S0000000000001-main.pdf",
                "1-s2.0-S0000000000002-main.pdf",
                "metals-12-00345.pdf",
                "s41598-024-00001.pdf",
                "main.pdf",
                "Review_01.pdf",
                "group_notes.docx",
            ):
                _write(root / "incoming" / name)
            payload = _survey(root)

        self.assertEqual(payload["suggested_profile"], "literature-dump")
        self.assertEqual(payload["phase_d_policy"], "on")
        self.assertFalse(payload["background_competition"])
        self.assertEqual(payload["profile_confidence"], "high")
        self.assertEqual(payload["layout_guidance"], "use_named_profile")
        self.assertGreaterEqual(payload["document_class_count"], 5)
        self.assertIn("documents", payload["observed_clusters"])


class DesktopBackgroundTests(unittest.TestCase):
    def test_mixed_media_dump_is_desktop_without_desktop_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "project_scoop"
            root.mkdir()
            _write(root / "IMG_0001.jpg")
            _write(root / "screenshot.png")
            _write(root / "meeting_notes.docx")
            _write(root / "random_scan.pdf")
            _write(root / "setup.exe")
            _write(root / "archive.zip")
            payload = _survey(root)

        self.assertNotIn("Desktop", root.name)
        self.assertEqual(payload["suggested_profile"], "desktop-dump")
        self.assertEqual(payload["phase_d_policy"], "docs_bucket")
        self.assertFalse(payload["background_competition"])
        self.assertNotIn(payload["suggested_profile"], SXRD_PROFILES)
        self.assertIn("images", payload["observed_clusters"])
        self.assertIn("documents", payload["observed_clusters"])


class ScientificBackgroundTests(unittest.TestCase):
    def test_cbf_texture_tree_is_sxrd_texture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "raw" / "frame_001.cbf")
            _write(root / "raw" / "frame_002.cbf")
            _write(root / "products" / "texture_omega.esg")
            payload = _survey(root)

        self.assertEqual(payload["suggested_profile"], "sxrd-texture")
        self.assertEqual(payload["phase_d_policy"], "off")
        self.assertFalse(payload["background_competition"])
        self.assertIn("scientific_data", payload["observed_clusters"])

    def test_azimuth_peakfit_tree_is_sxrd_tensile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "Az_001.txt")
            _write(root / "Az_002.txt")
            _write(root / "timestamp_aligned.csv")
            _write(root / "peakfit_summary.txt")
            _write(root / "job.fit")
            payload = _survey(root)

        self.assertEqual(payload["suggested_profile"], "sxrd-tensile")
        self.assertEqual(payload["phase_d_policy"], "off")

    def test_generic_data_heavy_tree_is_not_a_forced_spine(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in (
                "scan_01.dat",
                "scan_02.dat",
                "scan_03.xy",
                "scan_04.chi",
                "scan_05.raw",
            ):
                _write(root / "spectra" / name)
            payload = _survey(root)

        self.assertEqual(payload["suggested_profile"], "generic")
        self.assertEqual(payload["phase_d_policy"], "optional")
        self.assertIn("scientific_data", payload["observed_clusters"])
        self.assertTrue(payload["background_signals"]["scientific"]["matched"])
        self.assertNotEqual(payload["suggested_profile"], "literature-dump")
        self.assertNotIn(payload["suggested_profile"], SXRD_PROFILES)


class GenericBackgroundTests(unittest.TestCase):
    def test_unmatched_small_tree_is_generic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "notes.txt", b"hello")
            _write(root / "app.py", b"print(1)\n")
            _write(root / "README.md", b"# x\n")
            payload = _survey(root)

        self.assertEqual(payload["suggested_profile"], "generic")
        self.assertEqual(payload["phase_d_policy"], "optional")
        self.assertFalse(payload["background_competition"])
        self.assertEqual(payload["profile_confidence"], "low")
        self.assertEqual(payload["layout_guidance"], "adapt_from_observed")
        self.assertEqual(payload["competing_backgrounds"], [])


class MixedBackgroundTests(unittest.TestCase):
    def test_mixed_tree_surfaces_competition_instead_of_first_regex_lock(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "raw" / "frame_001.cbf")
            _write(root / "raw" / "frame_002.cbf")
            _write(root / "raw" / "texture_omega.esg")
            for name in (
                "1-s2.0-S0000000000001-main.pdf",
                "1-s2.0-S0000000000002-main.pdf",
                "metals-12-00345.pdf",
                "s41598-024-00001.pdf",
                "main.pdf",
                "Review_01.pdf",
            ):
                _write(root / name)
            _write(root / "screenshot.png")
            _write(root / "setup.exe")
            payload = _survey(root)

        self.assertTrue(payload["background_competition"])
        self.assertEqual(payload["suggested_profile"], "generic")
        self.assertEqual(payload["phase_d_policy"], "optional")
        self.assertEqual(payload["layout_guidance"], "adapt_from_observed")
        self.assertEqual(payload["profile_confidence"], "contested")
        ids = _competitor_ids(payload)
        self.assertIn("literature", ids)
        self.assertIn("scientific", ids)
        self.assertNotIn(payload["suggested_profile"], SXRD_PROFILES)
        self.assertNotEqual(payload["suggested_profile"], "literature-dump")

    def test_azimuth_plus_papers_does_not_silently_lock_to_sxrd_tensile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "Az_001.txt")
            _write(root / "Az_002.txt")
            for name in (
                "1-s2.0-S0000000000001-main.pdf",
                "1-s2.0-S0000000000002-main.pdf",
                "metals-12-00345.pdf",
                "s41598-024-00001.pdf",
                "main.pdf",
                "Review_01.pdf",
            ):
                _write(root / name)
            payload = _survey(root)

        self.assertTrue(payload["background_competition"])
        self.assertNotEqual(payload["suggested_profile"], "sxrd-tensile")
        self.assertIn("literature", _competitor_ids(payload))
        self.assertIn("scientific", _competitor_ids(payload))


class AgentContractTests(unittest.TestCase):
    def test_skill_starts_with_survey_and_public_cli(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("python scripts/tidy.py survey --root <folder> --json", text)
        self.assertIn("按方案执行", text)
        self.assertIn("background_competition", text)
        self.assertIn("observed_clusters", text)
        self.assertIn("Do not force `sxrd-texture` or `literature-dump`", text)
        self.assertNotIn("pwsh -File \"$SkillScripts\\inventory.ps1\"", text)


class ExampleAndCliTests(unittest.TestCase):
    def test_desktop_messy_example_counts_and_is_not_sxrd(self) -> None:
        root = ROOT / "examples" / "desktop-messy"
        payload = _survey(root)
        files = _real_files(root)
        docs = [path for path in files if path.suffix.lower() in DOC_EXTS]
        self.assertEqual(payload["file_count"], len(files))
        self.assertEqual(payload["document_class_count"], len(docs))
        self.assertGreaterEqual(payload["document_class_count"], 3)
        self.assertNotIn(payload["suggested_profile"], SXRD_PROFILES)
        self.assertIn(payload["suggested_profile"], {"desktop-dump", "generic"})
        self.assertIn("listing", payload)
        self.assertIn("existing_maps", payload)

    def test_tidy_survey_json_uses_shipped_collect_survey(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "notes.txt")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = tidy.main(["survey", "--root", str(root), "--json"])
            payload = json.loads(buf.getvalue())
            direct = _survey(root)

        self.assertEqual(rc, 0)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["suggested_profile"], direct["suggested_profile"])
        self.assertEqual(payload["file_count"], direct["file_count"])
        self.assertEqual(payload["document_class_count"], direct["document_class_count"])
        self.assertEqual(payload["phase_d_policy"], direct["phase_d_policy"])
        self.assertEqual(
            payload["background_competition"], direct["background_competition"]
        )

    def test_text_survey_mentions_competition_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "raw" / "frame_001.cbf")
            _write(root / "raw" / "texture_omega.esg")
            for name in (
                "1-s2.0-S0000000000001-main.pdf",
                "1-s2.0-S0000000000002-main.pdf",
                "metals-12-00345.pdf",
                "s41598-024-00001.pdf",
                "main.pdf",
                "Review_01.pdf",
            ):
                _write(root / name)
            text = survey_signals.format_survey_text(_survey(root), max_depth=2)

        self.assertIn("background_competition:", text)
        self.assertIn("competing_backgrounds:", text)
        self.assertIn("literature", text)
        self.assertIn("scientific", text)


if __name__ == "__main__":
    unittest.main()
