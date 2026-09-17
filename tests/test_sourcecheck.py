"""Behavioral boundary tests; no test makes a network request."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError, URLError

from sourcecheck.audit import (EvidenceClient, MAX_RESPONSE_BYTES, SourceFailure,
                              audit, normalize_title, parse_input)


DOI = "10.4230/lipics.itp.2023.19"
OTHER = "10.4230/oasics.icpec.2026.2"
OA = "https://api.openalex.org/works/W4385245566"


def work(title="MizAR 60 for Mizar 50", doi=DOI, locations=None):
    return {"id": "https://openalex.org/W4385245566", "title": title,
            "doi": "https://doi.org/" + doi if doi else None,
            "authorships": [{"raw_author_name": "Josef Urban", "author": {"display_name": "Josef Urban"}}],
            "locations": locations or []}


def crossref(title="MizAR 60 for Mizar 50", family="Urban"):
    return {"message": {"title": [title] if title is not None else [],
                        "author": [{"given": "Josef", "family": family}]}}


def datacite(title="MizAR 60 for Mizar 50", alternatives=None, related=None):
    titles = [{"title": title}] if title is not None else []
    titles.extend(alternatives or [])
    return {"data": {"attributes": {"titles": titles,
            "creators": [{"name": "Urban, Josef", "familyName": "Urban", "givenName": "Josef"}],
            "relatedIdentifiers": related or []}}}


class Response(io.BytesIO):
    def __init__(self, body, status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = headers or {}


class ScriptedOpener:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request.full_url, timeout))
        if not self.script:
            raise AssertionError("Unexpected fetch " + request.full_url)
        expected, status, body, headers = self.script.pop(0)
        if request.full_url != expected:
            raise AssertionError("Expected {} but fetched {}".format(expected, request.full_url))
        if isinstance(body, Exception):
            raise body
        payload = body if isinstance(body, bytes) else json.dumps(body).encode()
        if status != 200:
            raise HTTPError(request.full_url, status, "test", headers or {}, io.BytesIO(payload))
        return Response(payload, status, headers)


def cr(doi=DOI):
    return "https://api.crossref.org/works/" + doi


def dc(doi=DOI):
    return "https://api.datacite.org/dois/" + doi


class SourcecheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def run_audit(self, script, value="W4385245566"):
        opener = ScriptedOpener(script)
        waits = []
        client = EvidenceClient(self.temp.name, opener=opener, sleeper=waits.append)
        result = audit(value, self.temp.name, client=client)
        self.assertFalse(opener.script, "Unused expected requests")
        return result, opener, waits

    def test_unicode_html_punctuation_and_accents(self):
        self.assertEqual(normalize_title("<i>ＭｉｚＡＲ</i>&nbsp;60: for Mizar—50"), "mizar 60 for mizar 50")
        self.assertEqual(normalize_title("<p>First</p><p>Second</p>"), "first second")
        self.assertEqual(normalize_title("ÉTUDE &amp; café"), "étude café")
        self.assertNotEqual(normalize_title("café"), normalize_title("cafe"))

    def test_unfinished_markup_has_a_version_independent_boundary(self):
        cases = [("<i unfinished", ""), ("<i", ""),
                 ('Title <span data-x="unfinished', "title"),
                 ('Title <span data-x="a>b" unfinished', "title"),
                 ("Title &lt;span unfinished", "title"),
                 ("x < y and y > 0", "x y and y 0"), ("x < 3", "x 3"),
                 ('x <span title="a>b">y</span>', "x y")]
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(normalize_title(title), expected)

    def test_accepted_and_malicious_inputs(self):
        self.assertEqual(parse_input("https://api.openalex.org/works/W123")["normalized"], "W123")
        self.assertEqual(parse_input("https://doi.org/10.4230%2FLIPICS.ITP.2023.19")["input_doi"], DOI)
        for value in ["https://evil.example/W123", "https://openalex.org.evil/W123", "https://evil@openalex.org/W123",
                      "https://openalex.org:443/W123", "http://openalex.org/W123", "https://openalex.org/W123?",
                      "https://openalex.org/W123#", "https://openalex.org/W123?api_key=secret",
                      "https://api.openalex.org/authors/A123", "https://doi.org/10.1234/a%3Fsecret=1",
                      "W123\n", " W123", "x" * 513, "https://doi.org/10.1234/%0aevil"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_input(value)

    def test_fetch_allowlist_rejects_before_network(self):
        opener = ScriptedOpener([])
        client = EvidenceClient(self.temp.name, opener=opener)
        for url in ["https://evil.example/works/x", "https://api.crossref.org:443/works/x", "http://api.crossref.org/works/x",
                    "https://api.crossref.org/works/x?key=x", "https://api.openalex.org/authors/A1"]:
            with self.assertRaises(ValueError):
                client.get_json(url)
        self.assertFalse(opener.calls)

    def test_404_falls_back_and_evidence_bytes_are_receipted(self):
        report, _, _ = self.run_audit([(OA, 200, work(), {}), (cr(), 404, b"not found", {}), (dc(), 200, datacite(), {})])
        self.assertEqual(report["status"], "aligned")
        self.assertEqual(report["registry"]["provider"], "datacite")
        self.assertEqual(report["errors"][0]["kind"], "not_found")
        self.assertEqual([e["http_status"] for e in report["evidence"]], [200, 404, 200])
        for receipt in report["evidence"]:
            body = Path(receipt["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(), receipt["sha256"])
            self.assertEqual(len(body), receipt["bytes"])

    def test_missing_title_is_inconclusive(self):
        for own_title, registry_title in [(None, "Present"), ("Present", None), ("", "Present")]:
            with self.subTest(own_title=own_title, registry_title=registry_title):
                report, _, _ = self.run_audit([(OA, 200, work(own_title), {}), (cr(), 200, crossref(registry_title), {})])
                self.assertEqual(report["status"], "inconclusive")
                self.assertIsNone(report["comparison"]["token_jaccard"])

    def test_no_doi_does_not_guess_from_locations(self):
        report, opener, _ = self.run_audit([(OA, 200, work(doi=None, locations=[{"landing_page_url": "https://doi.org/" + OTHER}]), {})])
        self.assertEqual(report["status"], "inconclusive")
        self.assertEqual(len(opener.calls), 1)

    def test_alternate_title_is_preserved_but_not_a_silent_main_title(self):
        document = datacite("Registry main", alternatives=[{"title": "Other main", "titleType": "AlternativeTitle"}, {"title": "Subtitle", "titleType": "Subtitle"}])
        report, _, _ = self.run_audit([(OA, 200, work("Other main"), {}), (cr(), 404, {}, {}), (dc(), 200, document, {})])
        self.assertEqual(report["status"], "review")
        self.assertEqual(report["registry"]["alternate_titles"], ["Other main"])
        self.assertEqual(report["registry"]["subtitles"], ["Subtitle"])
        self.assertIsNone(report["comparison"]["matched_main_title"])

    def test_any_main_title_can_match_without_treating_translations_as_a_conflict(self):
        document = datacite("English main")
        document["data"]["attributes"]["titles"].append({"title": "French main"})
        report, _, _ = self.run_audit([(OA, 200, work("French main"), {}), (cr(), 404, {}, {}), (dc(), 200, document, {})])
        self.assertEqual(report["status"], "aligned")

    def test_requested_doi_is_primary_when_canonical_differs(self):
        oa_doi = "https://api.openalex.org/works/https://doi.org/" + OTHER
        report, _, _ = self.run_audit([(oa_doi, 200, work(), {}), (cr(OTHER), 200, crossref("Requested title"), {}),
                                     (cr(), 200, crossref(), {})], OTHER)
        self.assertEqual(report["registry"]["doi"], OTHER)
        self.assertEqual(report["comparison"]["selected_doi"], OTHER)
        self.assertTrue(report["comparison"]["input_doi_differs_from_canonical"])
        self.assertEqual(report["status"], "review")

    def test_shared_citation_does_not_establish_identity(self):
        relation = [{"relatedIdentifier": "https://arxiv.org/abs/1706.03762", "relatedIdentifierType": "URL", "relationType": "Cites"}]
        observed = work("Wrong title", locations=[{"landing_page_url": "https://doi.org/" + OTHER}])
        report, _, _ = self.run_audit([(OA, 200, observed, {}), (cr(), 404, {}, {}), (dc(), 200, datacite(related=relation), {}),
                                     (cr(OTHER), 404, {}, {}), (dc(OTHER), 200, datacite("Wrong title", related=relation), {})])
        self.assertEqual(report["status"], "review")
        self.assertEqual(report["work"]["location_dois"], [OTHER])
        common = report["source_conflicts"]["common_related_identifiers"][0]
        self.assertEqual(common["relation_type"], "Cites")
        self.assertFalse(common["merge_evidence"])
        self.assertEqual(common["source_dois"], [DOI, OTHER])
        self.assertEqual(len(report["source_conflicts"]["divergent_source_doi_pairs"]), 1)

    def test_author_overlap_is_context_not_identity(self):
        report, _, _ = self.run_audit([(OA, 200, work(), {}), (cr(), 200, crossref(family="Smith"), {})])
        self.assertEqual(report["status"], "aligned")
        self.assertEqual(report["comparison"]["author_family_overlap"]["shared_count"], 0)
        self.assertNotIn("confidence", report["comparison"])

    def test_429_retry_is_bounded_and_never_falls_back(self):
        report, opener, waits = self.run_audit([(OA, 200, work(), {}), (cr(), 429, {}, {"Retry-After": "0"}), (cr(), 429, {}, {})])
        self.assertEqual(report["status"], "inconclusive")
        self.assertEqual(report["errors"][-1]["kind"], "rate_limited")
        self.assertEqual(waits, [0])
        self.assertFalse(any("datacite" in url for url, _ in opener.calls))

    def test_long_retry_after_is_not_violated_or_slept(self):
        report, _, waits = self.run_audit([(OA, 200, work(), {}), (cr(), 429, {}, {"Retry-After": "60"})])
        self.assertEqual(report["status"], "inconclusive")
        self.assertFalse(waits)

    def test_no_registry_provider_is_inconclusive(self):
        report, _, _ = self.run_audit([(OA, 200, work(), {}), (cr(), 404, {}, {}), (dc(), 404, {}, {})])
        self.assertEqual(report["status"], "inconclusive")
        self.assertEqual([e["kind"] for e in report["errors"]], ["not_found", "not_found"])
        self.assertFalse(report["scope"]["all_selected_registry_sources_read"])

    def test_missing_secondary_source_does_not_claim_complete_alignment(self):
        observed = work(locations=[{"landing_page_url": "https://doi.org/" + OTHER}])
        report, _, _ = self.run_audit([(OA, 200, observed, {}), (cr(), 200, crossref(), {}), (cr(OTHER), 403, {}, {})])
        self.assertEqual(report["status"], "inconclusive")
        self.assertEqual(report["comparison"]["matched_main_title"], "MizAR 60 for Mizar 50")
        self.assertIn("registry_source_unavailable", report["signals"])

    def test_network_error_has_two_receipts_without_fake_bodies(self):
        report, _, waits = self.run_audit([(OA, None, URLError("offline"), {}), (OA, None, URLError("offline"), {})])
        self.assertEqual(report["status"], "inconclusive")
        self.assertEqual(report["errors"][0]["kind"], "network_error")
        self.assertEqual(len(report["evidence"]), 2)
        self.assertTrue(all(e["path"] is None for e in report["evidence"]))
        self.assertEqual(waits, [0.25])

    def test_redirect_is_not_followed(self):
        report, opener, _ = self.run_audit([(OA, 302, b"redirect", {"Location": "https://evil.example/steal"})])
        self.assertEqual(report["status"], "inconclusive")
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(report["evidence"][0]["http_status"], 302)

    def test_response_size_cap_preserves_marked_prefix(self):
        report, _, _ = self.run_audit([(OA, 200, b"x" * (MAX_RESPONSE_BYTES + 100), {})])
        self.assertEqual(report["status"], "inconclusive")
        self.assertEqual(report["errors"][0]["kind"], "response_too_large")
        self.assertTrue(report["evidence"][0]["truncated"])
        self.assertEqual(report["evidence"][0]["bytes"], MAX_RESPONSE_BYTES)

    def test_at_most_six_distinct_registry_dois(self):
        extra = ["10.1234/item{}".format(i) for i in range(8)]
        observed = work(locations=[{"landing_page_url": "https://doi.org/" + doi} for doi in extra])
        script = [(OA, 200, observed, {}), (cr(), 200, crossref(), {})]
        script.extend((cr(doi), 200, crossref(), {}) for doi in extra[:5])
        report, _, _ = self.run_audit(script)
        self.assertEqual(len(report["registry_sources"]), 6)
        self.assertEqual(report["scope"]["registry_dois_omitted"], extra[5:])

    def test_existing_evidence_is_verified_not_overwritten(self):
        client = EvidenceClient(self.temp.name)
        body = b"original"
        sha = hashlib.sha256(body).hexdigest()
        path = Path(self.temp.name) / (sha + ".body")
        path.write_bytes(b"tampered")
        with self.assertRaises(SourceFailure):
            client._receipt(OA, 200, body, 1)
        self.assertEqual(path.read_bytes(), b"tampered")


if __name__ == "__main__":
    unittest.main()
