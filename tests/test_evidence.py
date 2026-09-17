"""Archive integrity and reproducibility checks using actual captured responses."""
import json
from pathlib import Path
import shutil
import socket
import tempfile
import unittest
from unittest.mock import patch

from scripts.verify_evidence import (PROJECT, RecordedClient, check_manifest,
                                     reconstruct_cohort, url_key, verify)


class EvidenceTests(unittest.TestCase):
    def test_entire_archive_replays_with_network_disabled(self):
        with patch.object(socket, "socket", side_effect=AssertionError("Network forbidden in offline verification")):
            result = verify()
        self.assertEqual(result["raw_http_receipts_verified"], 89)
        self.assertEqual(result["cohort"]["title_disagreements"], 5)
        self.assertEqual(result["full_real_http_replay"]["registry_dois"], 5)
        self.assertFalse(result["full_real_http_replay"]["shared_citation_used_as_identity"])

    def test_a_changed_raw_byte_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "live-audit"
            shutil.copytree(PROJECT / "data/evidence/live-audit", target)
            manifest = json.loads((target / "manifest.json").read_text())
            body = target / manifest["receipts"][0]["file"]
            payload = body.read_bytes()
            body.write_bytes(bytes([payload[0] ^ 1]) + payload[1:])
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                check_manifest(target / "manifest.json")

    def test_changed_derived_count_is_recomputed_and_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "title-divergence"
            shutil.copytree(PROJECT / "data/evidence/title-divergence", target)
            summary = json.loads((target / "summary.json").read_text())
            summary["counts"]["title_disagreements"] = 4
            (target / "summary.json").write_text(json.dumps(summary))
            receipts = check_manifest(target / "manifest.json")
            with self.assertRaisesRegex(ValueError, "counts do not match raw data"):
                reconstruct_cohort(target, receipts)

    def test_replay_cannot_invent_a_missing_response(self):
        client = RecordedClient([])
        with patch.object(socket, "socket", side_effect=AssertionError("No live fallback allowed")):
            with self.assertRaisesRegex(ValueError, "No recorded HTTP response"):
                client.get_json("https://api.crossref.org/works/10.1234/missing")
        self.assertEqual(client.evidence, [])

    def test_lookup_aliases_normalize_without_confusing_providers(self):
        expected = ("api.openalex.org", "10.4230/lipics.itp.2023.19")
        self.assertEqual(url_key("https://api.openalex.org/works/doi:10.4230/LIPIcs.ITP.2023.19"), expected)
        self.assertEqual(url_key("https://api.openalex.org/works/https://doi.org/10.4230%2Flipics.itp.2023.19"), expected)
        self.assertNotEqual(url_key("https://api.datacite.org/dois/10.4230/lipics.itp.2023.19"), expected)


if __name__ == "__main__":
    unittest.main()
