import copy
import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from repairdesk.engine import Store, canonical_bytes, digest, normalize_record, review_record
from repairdesk.evaluation import evaluate
from repairdesk.scenarios import SCENARIO_IDS, build_demo, load_source, replay
from repairdesk.server import Handler


class EvidenceAndDecisionTests(unittest.TestCase):
    def test_behavioral_evaluation_including_counterexamples(self):
        result = evaluate()
        self.assertGreaterEqual(result["total"], 20)
        self.assertEqual(result["failed"], 0, [case for case in result["cases"] if not case["passed"]])

    def test_source_hash_and_exact_source_recovery(self):
        payload, source, provenance = load_source()
        self.assertEqual(digest(payload), provenance["sha256"])
        result = replay("affiliation-drop")
        self.assertEqual(result["silver"]["record"], normalize_record(source)[0])
        self.assertEqual(result["metrics"]["affected_authorships"], 1)
        self.assertEqual(result["silver"]["before"]["authorships"][2]["institutions"], [])
        for index, authorship in enumerate(source["authorships"]):
            if index != 2:
                self.assertEqual(authorship, result["silver"]["record"]["authorships"][index])

    def test_no_author_identity_reassignment(self):
        result = replay("orcid-conflict")
        self.assertEqual(result["silver"]["before"], result["silver"]["after"])
        self.assertEqual(result["findings"][0]["action"], "review-only")
        self.assertFalse(result["outcome"]["repair_applied"])

    def test_complete_bundle_determinism(self):
        self.assertEqual(canonical_bytes(build_demo()), canonical_bytes(build_demo()))

    def test_persistent_mixed_replays_are_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evidence.sqlite"
            for _ in range(2):
                for key in SCENARIO_IDS:
                    result = replay(key, path)
                    self.assertTrue(result["regression"]["passed"], (key, result["regression"]))
            store = Store(path)
            try:
                self.assertEqual(store.count("silver"), 3)
                self.assertEqual(store.count("replay_runs"), 8)
                self.assertEqual(store.count("bronze"), 5)
                self.assertEqual(store.connection.execute("SELECT MAX(version) FROM silver").fetchone()[0], 1)
            finally:
                store.close()

    def test_bronze_payload_survives_replay_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evidence.sqlite"
            result = replay("affiliation-drop", path)
            payload, _, _ = load_source()
            con = sqlite3.connect(str(path))
            try:
                persisted = con.execute("SELECT payload FROM bronze WHERE sha256=?", (result["bronze"]["sha256"],)).fetchone()[0]
                self.assertEqual(persisted, payload)
            finally:
                con.close()

    def test_repeated_repair_is_noop(self):
        _, source, _ = load_source()
        dropped = copy.deepcopy(source)
        dropped["authorships"][2]["institutions"] = []
        repaired, first_findings = review_record(dropped, source)
        replayed, second_findings = review_record(repaired, source)
        self.assertEqual(len(first_findings), 1)
        self.assertEqual(replayed, repaired)
        self.assertEqual(second_findings, [])

    def test_changed_affiliation_evidence_blocks_repair(self):
        _, source, _ = load_source()
        work = copy.deepcopy(source)
        work["authorships"][2]["institutions"] = []
        work["authorships"][2]["raw_affiliation_strings"] = ["A different affiliation"]
        work["authorships"][2]["affiliations"][0]["raw_affiliation_string"] = "A different affiliation"
        after, findings = review_record(work, source)
        self.assertEqual(after, work)
        self.assertEqual(findings[0]["action"], "review-only")

    def test_missing_institutions_key_recovers_without_exception(self):
        _, source, _ = load_source()
        work = copy.deepcopy(source)
        del work["authorships"][2]["institutions"]
        after, findings = review_record(work, source)
        self.assertEqual(after, source)
        self.assertEqual(findings[0]["action"], "restore-from-bronze")

    def test_identity_dispute_blocks_membership_repair(self):
        _, source, _ = load_source()
        source["authorships"][2]["raw_orcid"] = "0000-0002-1825-0097"
        work = copy.deepcopy(source)
        work["authorships"][2]["institutions"] = []
        after, findings = review_record(work, source)
        self.assertEqual(after, work)
        self.assertEqual(len(findings), 2)
        self.assertTrue(all(f["action"] == "review-only" for f in findings))

    def test_malformed_nested_institution_abstains(self):
        _, source, _ = load_source()
        work = copy.deepcopy(source)
        work["authorships"][2]["institutions"] = [None]
        after, findings = review_record(work, source)
        self.assertEqual(after, work)
        self.assertEqual(findings[0]["action"], "abstain")


class QuietHandler(Handler):
    def log_message(self, format, *args):
        pass


class LocalAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, data=None, headers=None):
        req = urllib.request.Request(self.base + path,
              data=None if data is None else json.dumps(data).encode(),
              headers=headers or ({"Content-Type": "application/json"} if data is not None else {}))
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)

    def test_scenario_and_evaluation_endpoints(self):
        status, data = self.request("/api/scenarios")
        self.assertEqual(status, 200)
        self.assertEqual([s["id"] for s in data["scenarios"]], list(SCENARIO_IDS))
        status, evaluation = self.request("/api/evaluation")
        self.assertEqual(status, 200)
        self.assertTrue(evaluation["all_passed"])

    def test_replay_endpoint_returns_computed_receipt(self):
        status, result = self.request("/api/replay", {"scenario": "affiliation-drop"})
        self.assertEqual(status, 200)
        self.assertTrue(result["regression"]["passed"])
        self.assertEqual(result, replay("affiliation-drop"))

    def test_arbitrary_url_or_file_input_rejected(self):
        for payload in [{"scenario": "https://example.com"}, {"scenario": "../../etc/passwd"},
                        {"scenario": "affiliation-drop", "source": "/etc/passwd"}, {"scenario": []}]:
            with self.subTest(payload=payload):
                status, result = self.request("/api/replay", payload)
                self.assertEqual(status, 400)
                self.assertIn("error", result)

    def test_cross_origin_post_rejected(self):
        status, _ = self.request("/api/replay", {"scenario": "affiliation-drop"},
                     {"Content-Type": "application/json", "Origin": "https://example.com"})
        self.assertEqual(status, 403)

    def test_untrusted_host_rejected(self):
        status, _ = self.request("/api/scenarios", headers={"Host": "example.com"})
        self.assertEqual(status, 403)

    def test_non_json_post_rejected(self):
        status, _ = self.request("/api/replay", {"scenario": "affiliation-drop"}, {"Content-Type": "text/plain"})
        self.assertEqual(status, 415)


if __name__ == "__main__":
    unittest.main()
