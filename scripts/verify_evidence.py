#!/usr/bin/env python3
"""Offline proof check: validate raw receipts, rebuild cohort, replay real HTTP.

No network requests, fabricated API responses, or file modifications are made.
The 30-pair cohort checks primary titles only. The full five-DOI case replays
the saved HTTP 200 *and* HTTP 404 bodies through the current audit engine.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from sourcecheck.audit import SourceFailure, audit, normalize_title, parse_registry


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_manifest(path):
    """Validate both archive manifest formats without trusting derived JSON."""
    path = Path(path)
    manifest = read_json(path)
    rows = manifest.get("receipts", manifest.get("responses"))
    require(isinstance(rows, list) and rows, "No receipts in " + str(path))
    checked = []
    for row in rows:
        file = row.get("file")
        require(isinstance(file, str) and file, "Receipt lacks a relative filename")
        body_path = (path.parent / file).resolve()
        require(body_path.parent == path.parent.resolve(), "Receipt escapes its evidence directory")
        body = body_path.read_bytes()
        require(len(body) == row["bytes"], "Byte count mismatch: " + str(body_path))
        require(hashlib.sha256(body).hexdigest() == row["sha256"], "SHA-256 mismatch: " + str(body_path))
        status = row.get("status", row.get("http_status"))
        require(isinstance(status, int) and 100 <= status <= 599, "Missing HTTP status")
        captured = row.get("captured_at", row.get("retrieved_at_utc", row.get("retrieved_at")))
        require(isinstance(captured, str), "Missing retrieval timestamp")
        require(datetime.fromisoformat(captured.replace("Z", "+00:00")).tzinfo is not None,
                "Retrieval timestamp must have a timezone")
        require(urlsplit(row["url"]).scheme == "https", "Receipt URL must be HTTPS")
        checked.append(dict(row, body_path=body_path, status=status, captured=captured))
    return checked


def url_key(url):
    """Normalize only the known API lookup spellings; retain provider identity."""
    parsed = urlsplit(url)
    require(not parsed.query and not parsed.fragment, "Unexpected query or fragment in replay URL")
    host = parsed.netloc.lower()
    path = unquote(parsed.path)
    if host == "api.openalex.org" and path.startswith("/works/"):
        key = path[len("/works/"):]
        if re.fullmatch(r"w\d+", key, re.I):
            return host, key.upper()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if key.lower().startswith(prefix):
                key = key[len(prefix):]
                break
        return host, key.lower()
    if host in {"api.crossref.org", "api.datacite.org"}:
        prefix = "/works/" if host == "api.crossref.org" else "/dois/"
        require(path.startswith(prefix), "Unexpected registry URL")
        return host, path[len(prefix):].lower()
    return host, path


class RecordedClient:
    """Dispatch exact recorded bytes; unknown URLs fail, never use the network."""
    def __init__(self, receipts):
        self.evidence = []
        self.calls = []
        self.receipts = {}
        for receipt in receipts:
            key = url_key(receipt["url"])
            previous = self.receipts.get(key)
            if previous is None or receipt["captured"] > previous["captured"]:
                self.receipts[key] = receipt

    def get_json(self, url):
        self.calls.append(url_key(url))
        receipt = self.receipts.get(url_key(url))
        require(receipt is not None, "No recorded HTTP response for " + url)
        self.evidence.append({"url": receipt["url"], "http_status": receipt["status"],
                              "retrieved_at": receipt["captured"], "sha256": receipt["sha256"],
                              "bytes": receipt["bytes"], "path": str(receipt["body_path"]),
                              "attempt": receipt.get("attempt", 1), "truncated": False,
                              "error_kind": receipt.get("error_kind")})
        if receipt["status"] != 200:
            kind = "not_found" if receipt["status"] == 404 else "http_error"
            raise SourceFailure(kind, "Replayed captured HTTP {}.".format(receipt["status"]), receipt["status"])
        return read_json(receipt["body_path"])


def cohort_normalize(value):
    # Independent reconstruction of the archived cohort's stated text rule.
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold()))


def reconstruct_cohort(directory, receipts):
    saved = read_json(directory / "summary.json")
    by_label = {row["label"]: row for row in receipts}
    require(len(by_label) == len(receipts), "Duplicate receipt labels")
    expected_dois = ["10.4230/lipics.itp.2023.{}".format(n) for n in range(1, 31)]
    require(saved["cohort"]["dois"] == expected_dois, "Cohort DOI selection changed")
    require(len(saved["records"]) == 30 and saved["cohort"]["count"] == 30, "Cohort must have 30 pairs")
    disagreements = []
    name_agreements = 0
    for suffix, row in enumerate(saved["records"], 1):
        doi = expected_dois[suffix - 1]
        require(row["suffix"] == suffix and row["doi"] == doi, "Cohort ordering changed")
        oa_receipt, dc_receipt = by_label[row["openalex_receipt"]], by_label[row["registry_receipt"]]
        require(oa_receipt["status"] == dc_receipt["status"] == 200, "Cohort source unavailable")
        require(url_key(oa_receipt["url"]) == ("api.openalex.org", doi), "Wrong OpenAlex lookup receipt")
        require(url_key(dc_receipt["url"]) == ("api.datacite.org", doi), "Wrong registry lookup receipt")
        work = read_json(oa_receipt["body_path"])
        document = read_json(dc_receipt["body_path"])
        registry = document["data"]["attributes"]
        titles = [item["title"] for item in registry["titles"]]
        names = [item["author"].get("display_name", "") for item in work["authorships"]]
        creators = [item.get("name", "") for item in registry["creators"]]
        title_match = cohort_normalize(work["title"]) in [cohort_normalize(t) for t in titles]
        names_match = [cohort_normalize(n) for n in names] == [cohort_normalize(n) for n in creators]
        engine_registry = parse_registry("datacite", doi, document)
        engine_match = normalize_title(work["title"]) in [normalize_title(t) for t in engine_registry["main_titles"]]
        require(engine_match == title_match, "Engine and independent title rule disagree for " + doi)
        for field, derived in (("openalex_id", work["id"]), ("openalex_title", work["title"]),
                               ("registry_titles", titles), ("openalex_authors", names),
                               ("registry_authors", creators), ("title_exact_match", title_match),
                               ("author_name_exact_match", names_match)):
            require(row[field] == derived, "Derived summary mismatch: {} {}".format(doi, field))
        if not title_match:
            disagreements.append(suffix)
        name_agreements += int(names_match)
    calculated = {"requested": 30, "comparable": 30, "title_agreements": 30 - len(disagreements),
                  "title_disagreements": len(disagreements), "author_name_agreements": name_agreements,
                  "author_name_disagreements": 30 - name_agreements}
    require(saved["counts"] == calculated, "Saved cohort counts do not match raw data")
    require(disagreements == [13, 17, 18, 19, 26], "Captured cohort findings changed")
    return dict(calculated, disagreement_suffixes=disagreements)


def replay_collision(directory, receipts):
    client = RecordedClient(receipts)
    report = audit("W4385245566", directory, client=client)
    archived = read_json(directory / "report.json")
    require(report["status"] == "review", "Real collision must request review")
    require(report["work"]["id"] == "https://openalex.org/W4385245566", "Wrong replay work")
    require(len(client.calls) == 11, "Expected 11 real HTTP responses in full replay")
    require([e["http_status"] for e in client.evidence] == [200] + [404, 200] * 5,
            "Replay must use the five actual Crossref 404 fallback responses")
    require(len(report["registry_sources"]) == 5, "Expected five DOI registry records")
    require(report["scope"]["all_selected_registry_sources_read"] is True, "Source replay incomplete")
    conflicts = report["source_conflicts"]
    require(len(conflicts["distinct_normalized_main_titles"]) == 3, "Expected three distinct title groups")
    require(len(conflicts["divergent_source_doi_pairs"]) == 7, "Expected seven divergent DOI pairs")
    require(conflicts == archived["source_conflicts"], "Saved source-conflict result differs from current engine")
    citations = [row for row in conflicts["common_related_identifiers"]
                 if row["identifier"] == "arXiv:1706.03762" and row["relation_type"] == "Cites"]
    require(len(citations) == 1 and len(citations[0]["source_dois"]) == 5,
            "Shared citation evidence must remain visible across five records")
    for source in report["registry_sources"]:
        require(all(row["merge_evidence"] is False for row in source["related_identifiers"]),
                "A relation was wrongly treated as identity/merge evidence")
    require(all(row["merge_evidence"] is False for row in conflicts["common_related_identifiers"]),
            "A shared relation was wrongly treated as merge evidence")
    require("title_divergence" in report["signals"] and
            "multiple_registry_main_titles_across_location_dois" in report["signals"],
            "Both primary title and source-family divergence must be exposed")
    return {"status": report["status"], "real_http_responses_replayed": len(client.calls),
            "registry_dois": 5, "distinct_title_groups": 3, "divergent_doi_pairs": 7,
            "shared_citation_used_as_identity": False}


def verify(root=PROJECT):
    evidence = Path(root) / "data" / "evidence"
    groups = {}
    for name in ("title-divergence", "source-collision", "live-audit"):
        groups[name] = check_manifest(evidence / name / "manifest.json")
    return {"raw_http_receipts_verified": sum(len(rows) for rows in groups.values()),
            "cohort": reconstruct_cohort(evidence / "title-divergence", groups["title-divergence"]),
            "full_real_http_replay": replay_collision(evidence / "live-audit", groups["live-audit"]),
            "network_requests": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT, help="Project root; defaults to this checkout")
    args = parser.parse_args(argv)
    try:
        result = verify(args.root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, "Evidence verification failed: {}\n".format(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
