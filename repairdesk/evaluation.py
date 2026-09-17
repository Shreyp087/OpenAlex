"""A tiny deterministic behavioral suite: counterexamples are part of the product."""
import copy
import json
import sqlite3
from .engine import Store, RecordError, canonical_bytes, digest, normalize_doi, normalize_orcid, normalize_record, review_record
from .scenarios import SCENARIO_IDS, load_source, replay, synthetic_work


def evaluate():
    cases = []

    def run(case_id, name, operation, detail):
        try:
            passed = bool(operation())
            error = None
        except Exception as exc:
            passed = False
            error = type(exc).__name__ + ": " + str(exc)
        item = {"id": case_id, "name": name, "passed": passed, "detail": detail}
        if error:
            item["error"] = error
        cases.append(item)

    def scenario_ok(key):
        return replay(key)["regression"]["passed"]

    for key in SCENARIO_IDS:
        run(key, "End-to-end: " + key, lambda key=key: scenario_ok(key),
            "Exercises evidence ingestion, decision, materialization, and scenario-specific regression checks.")

    def no_conflict(raw_orcid, resolved_orcid):
        work = synthetic_work("missing-orcid")
        work["authorships"][0]["raw_orcid"] = raw_orcid
        work["authorships"][0]["author"]["orcid"] = resolved_orcid
        result, findings = review_record(work)
        return result == work and not any(f["code"] == "ORCID_CONFLICT" for f in findings)

    run("missing-raw-orcid", "Missing raw ORCID is not a conflict", lambda: no_conflict(None, "https://orcid.org/0000-0002-1825-0097"), "Absence is not disagreement.")
    run("missing-resolved-orcid", "Missing resolved ORCID is not a conflict", lambda: no_conflict("0000-0002-1825-0097", None), "No author identity is invented.")
    run("equivalent-orcid", "Equivalent ORCID representations agree", lambda: no_conflict("0000-0002-1825-0097", "https://orcid.org/0000-0002-1825-0097"), "Formatting differences do not create identity conflicts.")
    run("invalid-orcid", "Invalid ORCID checksum cannot justify reassignment", lambda: normalize_orcid("0000-0002-1825-0098") is None and no_conflict("0000-0002-1825-0098", "0000-0002-1825-0097"), "Reject invalid comparison evidence; preserve the delivered value.")

    def same_name():
        work = synthetic_work("same-name")
        second = copy.deepcopy(work["authorships"][0])
        second["author"]["id"] = "synthetic:author:another-alex"
        work["authorships"].append(second)
        after, findings = review_record(work)
        return after == work and len(after["authorships"]) == 2 and not findings
    run("same-name", "Two authors with the same name never merge", same_name, "Distinct IDs remain distinct even when names and affiliation strings match.")

    def country_only():
        work = synthetic_work("country-only")
        work["authorships"][0]["affiliations"] = []
        work["authorships"][0]["raw_affiliation_strings"] = []
        result, findings = review_record(work)
        return result == work and not findings
    run("country-without-institution", "A valid country does not require an institution", country_only, "Country evidence is weaker than institutional identity.")

    def missing_fields():
        work = {"id": "synthetic:minimal"}
        normalized, log = normalize_record(work)
        result, findings = review_record(normalized)
        return result == work and not findings and not log
    run("minimal-record", "Missing optional fields are safe", missing_fields, "An identifiable sparse record is retained without guessing values.")

    def malformed_authorships():
        work = {"id": "synthetic:malformed", "authorships": "not-a-list"}
        result, findings = review_record(work)
        return result == work and [f["code"] for f in findings] == ["MALFORMED_AUTHORSHIPS"] and findings[0]["action"] == "abstain"
    run("malformed-authorships", "Malformed authorships are retained and flagged", malformed_authorships, "Unexpected shape cannot silently become a clean empty record.")

    def malformed_affiliations():
        work = synthetic_work("malformed-affiliations")
        work["authorships"][0]["affiliations"] = "not-a-list"
        result, findings = review_record(work)
        return result == work and findings[0]["code"] == "MALFORMED_AFFILIATION_FIELDS"
    run("malformed-affiliations", "Malformed affiliation fields abstain", malformed_affiliations, "No inferred fix or exception from unexpected field types.")

    def no_id():
        try:
            normalize_record({"doi": "https://doi.org/10.1234/example"})
        except RecordError:
            return True
        return False
    run("missing-stable-id", "DOI alone cannot become a materialization key", no_id, "Records without a stable work ID are rejected explicitly.")

    def source_unchanged():
        payload, source, provenance = load_source()
        original = canonical_bytes(source)
        changed = copy.deepcopy(source)
        changed["authorships"][2]["institutions"] = []
        review_record(changed, source)
        return canonical_bytes(source) == original and digest(payload) == provenance["sha256"]
    run("source-immutability", "Source objects and exact bytes stay immutable", source_unchanged, "A proposed repair does not mutate the intact source used as evidence.")

    def database_immutability():
        store = Store()
        try:
            sha = store.ingest(b'{"id":"synthetic:immutable"}', "synthetic")
            blocked = 0
            for sql in ["UPDATE bronze SET payload=x'00' WHERE sha256=?", "DELETE FROM bronze WHERE sha256=?",
                        "INSERT OR REPLACE INTO bronze(sha256,payload,source_kind) VALUES(?,x'00','replacement')"]:
                try:
                    store.connection.execute(sql, (sha,))
                except sqlite3.IntegrityError:
                    blocked += 1
                    store.connection.rollback()
            return blocked == 3 and store.count("bronze") == 1
        finally:
            store.close()
    run("bronze-sql-guards", "SQLite blocks bronze UPDATE, DELETE, and REPLACE", database_immutability, "Raw evidence immutability is enforced by storage triggers.")

    def duplicate_doi_distinct_ids():
        store = Store()
        try:
            for key in ["synthetic:work:one", "synthetic:work:two"]:
                work = {"id": key, "doi": "https://doi.org/10.1234/same"}
                sha = store.ingest(canonical_bytes(work), "synthetic")
                store.materialize(work, sha)
            return store.count("silver") == 2
        finally:
            store.close()
    run("shared-doi-distinct-works", "Same DOI across different work IDs never silently merges", duplicate_doi_distinct_ids, "DOI is a representation to normalize, not a unique database key.")

    def changed_payload():
        store = Store()
        try:
            work = {"id": "synthetic:versioned", "title": "Before"}
            sha = store.ingest(canonical_bytes(work), "synthetic")
            first = store.materialize(work, sha)
            repeat = store.materialize(work, sha)
            work["title"] = "Corrected"
            second_sha = store.ingest(canonical_bytes(work), "synthetic")
            changed = store.materialize(work, second_sha)
            version = store.connection.execute("SELECT version FROM silver").fetchone()[0]
            return first and not repeat and changed and version == 2 and store.count("silver") == 1 and store.count("bronze") == 2
        finally:
            store.close()
    run("versioned-replay", "Identical retries are no-ops; changed content advances the version", changed_payload, "Stable identity alone never suppresses a real metadata update.")

    def no_support():
        _, source, _ = load_source()
        work = copy.deepcopy(source)
        work["authorships"][2]["institutions"] = []
        after, findings = review_record(work)
        return after == work and len(findings) == 1 and findings[0]["action"] == "review-only"
    run("missing-source-support", "Missing membership without intact evidence stays review-only", no_support, "A mapped ID alone does not authorize constructing an institution object.")

    def different_source_identity():
        _, source, _ = load_source()
        work = copy.deepcopy(source)
        work["authorships"][2]["institutions"] = []
        source["id"] = "synthetic:other-work"
        after, findings = review_record(work, source)
        return after == work and findings[0]["action"] == "review-only"
    run("wrong-source-work", "Evidence from another work cannot authorize a repair", different_source_identity, "Source and materialized work IDs must agree.")

    def ambiguous_source_author():
        _, source, _ = load_source()
        work = copy.deepcopy(source)
        work["authorships"][2]["institutions"] = []
        source["authorships"].append(copy.deepcopy(source["authorships"][2]))
        after, findings = review_record(work, source)
        return after == work and findings[0]["action"] == "review-only"
    run("ambiguous-source-authorship", "Ambiguous matching source authorships block repair", ambiguous_source_author, "A unique author ID and raw-name match is required in the intact source.")

    def raw_unicode():
        work = synthetic_work("unicode")
        raw = "  École de recherche — Montréal\nIndependent scientist  "
        work["authorships"][0]["raw_affiliation_strings"] = [raw]
        work["authorships"][0]["affiliations"][0]["raw_affiliation_string"] = raw
        normalized, _ = normalize_record(work)
        result, _ = review_record(normalized)
        return result["authorships"][0]["raw_affiliation_strings"][0].encode() == raw.encode() and result == work
    run("raw-string-fidelity", "Unicode and whitespace in raw evidence survive byte-for-byte", raw_unicode, "Normalization never rewrites affiliation evidence.")

    run("invalid-doi", "Invalid DOI strings are retained unchanged", lambda: normalize_doi("not a DOI") == "not a DOI", "The normalizer does not fabricate a resolver URL for arbitrary text.")
    run("determinism", "Independent replays produce identical content", lambda: canonical_bytes(replay("affiliation-drop")) == canonical_bytes(replay("affiliation-drop")), "Pinned fixture and pure decisions produce deterministic output.")
    def missing_institution_key():
        _, source, _ = load_source()
        work = copy.deepcopy(source)
        del work["authorships"][2]["institutions"]
        after, findings = review_record(work, source)
        return after == source and findings[0]["action"] == "restore-from-bronze"
    run("missing-institutions-key", "Missing institution list recovers without a crash", missing_institution_key, "Exact matching source evidence can recover a missing optional container.")

    def changed_raw_evidence():
        _, source, _ = load_source()
        work = copy.deepcopy(source)
        work["authorships"][2]["institutions"] = []
        work["authorships"][2]["raw_affiliation_strings"] = ["A different affiliation"]
        work["authorships"][2]["affiliations"][0]["raw_affiliation_string"] = "A different affiliation"
        after, findings = review_record(work, source)
        return after == work and findings[0]["action"] == "review-only"
    run("changed-raw-evidence", "Changed raw affiliation evidence blocks automatic restoration", changed_raw_evidence, "Matching author identity alone cannot prove that source membership belongs to the delivered affiliation.")

    def mixed_identity_dispute():
        _, source, _ = load_source()
        source["authorships"][2]["raw_orcid"] = "0000-0002-1825-0097"
        work = copy.deepcopy(source)
        work["authorships"][2]["institutions"] = []
        after, findings = review_record(work, source)
        return after == work and len(findings) == 2 and all(f["action"] == "review-only" for f in findings)
    run("identity-dispute-and-missing-membership", "Identity disagreement blocks membership restoration", mixed_identity_dispute, "No automated patch is applied to an authorship whose identity is disputed.")

    def malformed_nested_institution():
        _, source, _ = load_source()
        work = copy.deepcopy(source)
        work["authorships"][2]["institutions"] = [None]
        after, findings = review_record(work, source)
        return after == work and findings[0]["action"] == "abstain"
    run("malformed-nested-institution", "Malformed list entries abstain instead of partial repair", malformed_nested_institution, "Unexpected nested evidence is retained for review.")

    passed = sum(1 for item in cases if item["passed"])
    return {"passed": passed, "total": len(cases), "failed": len(cases) - passed,
            "all_passed": passed == len(cases), "cases": cases,
            "scope": "Small deterministic fixture suite, not a statistical accuracy estimate or production-scale benchmark. No ML model is trained or evaluated."}
