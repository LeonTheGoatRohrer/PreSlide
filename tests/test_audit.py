"""Synthetic unit fixtures exercise invariants; never used as research data."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from preslide.audit import date_quality, iso_day, position_passes, plausible_coordinates, filter_period
from preslide import sources


class QualityRules(unittest.TestCase):
    def attrs(self, narrative="13. Juni 2018", **changes):
        return {"Ereignisdatum_validFrom": "2018-06-13", "processTimeOrPeriodInfo": narrative,
                "EREIGNIS_J": 2018, "EREIGNIS_M": 6, "EREIGNIS_T": 13, **changes}

    def test_position_interval_uses_upper_bound(self):
        self.assertFalse(position_passes("50-2000m", 250))
        self.assertFalse(position_passes("Lage ungenau (100-1000m)", 250))
        self.assertTrue(position_passes("Lage relativ genau (20-100m)", 100))

    def test_position_unknown_and_open_ended_are_not_accepted(self):
        for value in (None, "", "unknown", "Lage sehr ungenau (>1000m)"):
            self.assertFalse(position_passes(value, 10000))

    def test_single_day_and_approximate_hour(self):
        for text in ("13. Juni 2018", "13. Juni 2018 (gegen 08:00 Uhr)",
                     "13. Juni 2018 (nach ca. 13:30 Uhr)", "2018-06-13"):
            self.assertEqual(date_quality(self.attrs(text)), "reported_single_day", text)

    def test_uncertain_day_not_overridden_by_iso_field(self):
        for text in ("12. oder 13. Juni 2018", "12./13. Juni 2018", "ab 13. Juni 2018",
                     "wahrscheinlich 13. Juni 2018", "13. Juni 2018 und am Folgetag",
                     "13. Juni 2018 (Nacht)", "13. Juni 2018 (23:30 bis 00:30 Uhr)"):
            self.assertNotEqual(date_quality(self.attrs(text)), "reported_single_day", text)

    def test_disagreeing_narrative_rejected(self):
        self.assertEqual(date_quality(self.attrs("12. Juni 2018")), "conflicting_date_fields")

    def test_partial_conflicting_fields_rejected(self):
        self.assertEqual(date_quality(self.attrs(EREIGNIS_J=2017, EREIGNIS_M=None)), "conflicting_date_fields")

    def test_missing_narrative_not_assumed_exact(self):
        self.assertEqual(date_quality(self.attrs(None)), "structured_day_unverified")

    def test_month_year_and_invalid_dates(self):
        self.assertIsNone(iso_day("2018-00-00"))
        self.assertIsNone(iso_day("2018-02-30"))
        self.assertIsNone(iso_day("2018-06-13T00:00:00Z"))
        self.assertEqual(date_quality({"Ereignisdatum": "2018-06-00"}), "month_only")
        self.assertEqual(date_quality({"Ereignisdatum": "2018-00-00"}), "year_only")

    def test_coordinates_axis_order_missing_and_nodata(self):
        self.assertTrue(plausible_coordinates({"x": 14, "y": 47}))
        for geometry in (None, {}, {"x": 47, "y": 14}, {"x": float("nan"), "y": 47}, {"x": 14, "y": -9999}):
            self.assertFalse(plausible_coordinates(geometry))

    def test_period_and_duplicates(self):
        config = json.loads((sources.ROOT / "config/audit.json").read_text())
        a = self.attrs()
        a.update({"Prozessgruppe": "Gleiten/Rutschen", "Prozessuntergruppe": "Lockergesteinsrutschung",
                  "QUAL_LAGE": "Lage genau (5-20m)", "QUAL_PROZ": "Codierung sicher",
                  "QUAL_MB": "Objekt ist sicher eine Massenbewegung", "nameOfEvent": "unit_fixture", "OBJECTID": 1})
        one = {"attributes": a, "geometry": {"x": 14, "y": 47}}
        duplicate = copy.deepcopy(one)
        duplicate["attributes"]["OBJECTID"] = 2
        report, accepted, _ = filter_period([one, duplicate], config, "2018-01-01")
        self.assertEqual(len(accepted), 1)
        self.assertEqual(report["exact_location_date_duplicates_removed"], 1)
        future_config = {**config, "end_date": "2018-06-12"}
        self.assertEqual(len(filter_period([one], future_config, "2018-01-01")[1]), 0)

    def test_rockfall_not_accepted(self):
        from preslide.audit import classify
        config = json.loads((sources.ROOT / "config/audit.json").read_text())
        f = {"attributes": {**self.attrs(), "Prozessgruppe": "Stuerzen"}, "geometry": {"x": 14, "y": 47}}
        self.assertFalse(classify(f, config, "2018-01-01")["accepted_process"])


class CacheRules(unittest.TestCase):
    def test_integrity_and_parameter_separation(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory, patch.object(sources, "ROOT", Path(directory)), \
                patch.object(sources.shutil, "which", return_value="curl"), \
                patch.object(sources.subprocess, "run", return_value=SimpleNamespace(stdout=b'{"value": 1}')) as run:
            self.assertEqual(sources.cached_json("https://example.test/data", {"id": 1}), {"value": 1})
            sources.cached_json("https://example.test/data", {"id": 1})
            self.assertEqual(run.call_count, 1)
            sources.cached_json("https://example.test/data", {"id": 2})
            self.assertEqual(run.call_count, 2)
            path = next(p for p in (Path(directory)/"data/raw/http").glob("*.json") if not p.name.endswith(".meta.json"))
            meta = json.loads(path.with_suffix(".meta.json").read_text())
            path.write_text('{"value":999}')
            original_id = 1 if "id=1" in meta["url"] else 2
            with self.assertRaisesRegex(RuntimeError, "integrity"):
                sources.cached_json("https://example.test/data", {"id": original_id})

    def test_cached_snapshot_checksums(self):
        manifests = list((sources.ROOT / "data/raw/http").glob("*.meta.json"))
        if not manifests:
            self.skipTest("Live snapshot has not been downloaded on this machine")
        for manifest in manifests:
            meta = json.loads(manifest.read_text(encoding="utf-8"))
            payload = manifest.with_name(manifest.name.replace(".meta.json", ".json"))
            self.assertEqual(hashlib.sha256(payload.read_bytes()).hexdigest(), meta["sha256"], str(payload))


if __name__ == "__main__":
    unittest.main()
