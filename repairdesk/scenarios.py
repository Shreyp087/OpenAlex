"""Four deliberately small, labelled incidents; none is a production allegation."""
import copy
import json
from .engine import ROOT, Store, canonical_bytes, digest, normalize_record, review_record

SCENARIO_IDS = ("affiliation-drop", "orcid-conflict", "sparse-metadata", "doi-replay")


def load_source():
    payload = (ROOT / "data/source/openalex-work.json").read_bytes()
    provenance = json.loads((ROOT / "data/source/provenance.json").read_text())
    if digest(payload) != provenance["sha256"]:
        raise ValueError("source fixture hash mismatch: refusing to replay modified evidence")
    return payload, json.loads(payload), provenance


def synthetic_work(kind):
    return {
        "id": "synthetic:work:" + kind,
        "title": "Fictional fixture — " + kind.replace("-", " "),
        "doi": None,
        "authorships": [{
            "author_position": "first",
            "author": {"id": "synthetic:author:alex-example", "display_name": "Alex Example", "orcid": None},
            "raw_author_name": "Alex Example", "raw_orcid": None,
            "raw_affiliation_strings": ["Independent researcher, Ahmedabad, India"],
            "affiliations": [{"raw_affiliation_string": "Independent researcher, Ahmedabad, India", "institution_ids": []}],
            "institutions": [], "countries": ["IN"]
        }]
    }


def check(name, passed, detail):
    return {"name": name, "passed": bool(passed), "detail": detail}


def raw_affiliations(record):
    return [{"raw_author_name": a.get("raw_author_name"),
             "raw_affiliation_strings": a.get("raw_affiliation_strings"),
             "affiliations": a.get("affiliations"), "raw_orcid": a.get("raw_orcid")}
            for a in record.get("authorships", []) if isinstance(a, dict)]


def replay(scenario_id, db_path=":memory:"):
    if scenario_id not in SCENARIO_IDS:
        raise ValueError("unknown scenario; choose one of: " + ", ".join(SCENARIO_IDS))
    source_payload, observed, provenance = load_source()
    source_kind = "observed-fixture-with-injected-fault"
    source_record = copy.deepcopy(observed)
    title = "The affiliation that fell out"
    kind = "Recover"
    description = "A deliberate transform fault removes Shrey Patel’s mapped Nirma University membership from a copy of his paper’s metadata. The intact public snapshot stays untouched."
    ticket = {"subject": "Why is the institution missing from my authorship?", "persona": "Illustrative university librarian",
              "body": "The affiliation text still says Nirma University, but this replay copy no longer includes Shrey’s institution membership. The coauthors still retain it. Can you explain the local mismatch and recover Shrey’s mapping?"}
    expected = "Restore only the lost source-supported membership; preserve all raw strings."
    if scenario_id == "orcid-conflict":
        source_kind = "synthetic"
        source_record = synthetic_work(scenario_id)
        source_record["authorships"][0]["raw_orcid"] = "https://orcid.org/0000-0002-1825-0097"
        source_record["authorships"][0]["author"]["orcid"] = "https://orcid.org/0000-0003-1613-5981"
        title, kind = "One name. Two identifiers.", "Escalate"
        description = "An entirely fictional authorship carries two different checksum-valid ORCID examples. The disagreement warrants review, but neither value establishes the correct identity."
        ticket = {"subject": "This publication may be attached to the wrong person", "persona": "Illustrative researcher",
                  "body": "The imported authorship has a different ORCID from its resolved author. Can you switch it to the other author?"}
        expected = "Flag the conflict for review; never reassign or merge an author."
    elif scenario_id == "sparse-metadata":
        source_kind = "synthetic-negative-control"
        source_record = synthetic_work(scenario_id)
        title, kind = "Missing is not wrong", "Abstain"
        description = "A fictional independent researcher has a useful raw affiliation and country, with no mapped institution. Sparse metadata alone supplies no evidence of a defect."
        ticket = {"subject": "Should every affiliation have an institution ID?", "persona": "Illustrative data consumer",
                  "body": "I see a raw affiliation and an India country code, but no mapped institution. Should we fill in an institution from the city?"}
        expected = "Keep the legitimate empty mapping. Abstain from inventing an institution."
    elif scenario_id == "doi-replay":
        source_kind = "observed-fixture-with-synthetic-deliveries"
        title, kind = "The same work, twice", "Deduplicate"
        description = "Two fabricated deliveries of the same observed work vary only in DOI case and prefix. Work identity and canonical content yield one materialization."
        ticket = {"subject": "Did a retry create a duplicate work?", "persona": "Illustrative repository operator",
                  "body": "Our delivery was retried with an uppercase DOI and a different prefix. Will this create another work or overwrite the evidence?"}
        expected = "Retain both delivery payloads and materialize one work, using the work ID rather than DOI as identity."

    store = Store(db_path)
    try:
        # For observed scenarios, first bronze object is the untouched public file.
        is_observed = scenario_id in ("affiliation-drop", "doi-replay")
        bronze_payload = source_payload if is_observed else canonical_bytes(source_record)
        bronze_sha = store.ingest(bronze_payload, "observed-public-snapshot" if is_observed else source_kind)
        normalized, logs = normalize_record(source_record)
        before = copy.deepcopy(normalized)
        if scenario_id == "affiliation-drop":
            target = before["authorships"][2]
            target["institutions"] = target["institutions"][1:]
        findings = []
        materialization_writes = 0
        deliveries = 1
        delivery_evidence = [{"sha256": bronze_sha, "role": "intact source snapshot" if is_observed else "synthetic delivered fixture"}]
        if scenario_id == "doi-replay":
            # The untouched public snapshot is evidence, not a third fabricated delivery.
            deliveries = 2
            normalized_deliveries = []
            delivery_evidence = []
            doi_suffix = observed["doi"].split("doi.org/", 1)[1]
            for doi in [" DOI:" + doi_suffix.upper() + " ", "http://dx.doi.org/" + doi_suffix]:
                delivery = copy.deepcopy(observed)
                delivery["doi"] = doi
                payload = canonical_bytes(delivery)
                delivery_sha = store.ingest(payload, source_kind)
                normalized_delivery, log = normalize_record(delivery)
                logs.extend(log)
                normalized_deliveries.append(normalized_delivery)
                materialization_writes += int(store.materialize(normalized_delivery, delivery_sha))
                delivery_evidence.append({"sha256": delivery_sha, "role": "fabricated delivery", "raw_doi": doi})
            before = copy.deepcopy(observed)
            before["doi"] = " DOI:" + doi_suffix.upper() + " "
            after = normalized_deliveries[-1]
            findings = [{"code": "IDEMPOTENT_REPLAY", "severity": "info", "summary": "Two differently encoded deliveries produce one identical work materialization.",
                "evidence": [{"label": "Stable identity key", "path": "id", "value": observed["id"]},
                             {"label": "Raw delivered DOI values", "path": "doi", "value": [x["raw_doi"] for x in delivery_evidence]},
                             {"label": "Normalized content SHA-256", "path": "silver.content_sha256", "value": digest(canonical_bytes(after))}],
                "path": "doi", "before": [x["raw_doi"] for x in delivery_evidence], "after": after["doi"], "action": "normalize-and-deduplicate"}]
        else:
            after, findings = review_record(before, source_record if scenario_id == "affiliation-drop" else None)
            materialization_writes = int(store.materialize(after, bronze_sha))
        statuses = {
            "affiliation-drop": {"status": "recovered", "label": "Source-backed repair", "summary": "One lost institution membership restored from immutable evidence.", "decision": "Restore the exact institution object present in the intact source snapshot.", "repair_applied": True},
            "orcid-conflict": {"status": "review", "label": "Human review needed", "summary": "One identity disagreement flagged. Zero author reassignments.", "decision": "Keep both identifiers as evidence and ask for identity review.", "repair_applied": False},
            "sparse-metadata": {"status": "abstained", "label": "Abstain", "summary": "No unsupported institution inferred. Zero false alarms.", "decision": "Preserve the empty mapping; a country and a string do not prove institutional identity.", "repair_applied": False},
            "doi-replay": {"status": "deduplicated", "label": "Idempotent replay", "summary": "Two fabricated deliveries. One work materialization.", "decision": "Canonicalize DOI representation; deduplicate only within the same work ID and identical canonical content.", "repair_applied": False}
        }
        replies = {
            "affiliation-drop": "Thanks for the clear report. In this deliberately faulted local replay, the affiliation text and explicit mapping were intact, but Shrey’s Nirma University membership had dropped out of the materialized authorship. The intact source snapshot contains that exact membership, so the replay restores it. The raw affiliation is unchanged, and the regression check now verifies that every explicit mapped ID survives. This fixture affects one authorship in one work; it does not establish a wider production incident.",
            "orcid-conflict": "Thanks for flagging the disagreement. This fictional example contains two different valid ORCIDs, so I’ve marked it for identity review and retained both values. I have not switched or merged the author: the available metadata does not establish which identity is correct. The next useful evidence would be a publisher correction or author-confirmed identifier, followed by a reviewed decision.",
            "sparse-metadata": "An empty institution mapping can be legitimate. This example retains the researcher’s exact affiliation text and country, but those fields do not identify an institution. I’ve left the record unchanged and have not raised a defect. If stronger institutional evidence becomes available, it can support a separate reviewed mapping.",
            "doi-replay": "The two fabricated deliveries resolve to the same stable work ID and identical normalized content, so this replay keeps one materialization. Both raw delivery payloads remain available for inspection. DOI formatting is standardized only in the normalized view. A matching DOI on a different work ID would remain a separate record; this prototype never merges works on DOI alone."
        }
        checks = [check("Bronze evidence matches its SHA-256", digest(bronze_payload) == bronze_sha, "Exact raw bytes are content-addressed."),
                  check("Raw affiliation and identifier evidence is unchanged", raw_affiliations(before) == raw_affiliations(after), "No raw affiliation string, raw author name, or raw ORCID was rewritten."),
                  check("Work identity preserved", before["id"] == after["id"], "No work ID replacement or DOI-only merge.")]
        if scenario_id == "affiliation-drop":
            checks.append(check("Exact source membership restored", after == normalized, "The repaired record equals the normalized intact source."))
            checks.append(check("One deliberately affected authorship", len(findings) == 1 and findings[0]["path"] == "authorships[2].institutions", "Only Shrey’s authorship is patched."))
        elif scenario_id == "orcid-conflict":
            checks.append(check("Conflict is review-only", before == after and [f["code"] for f in findings] == ["ORCID_CONFLICT"], "No identity reassignment."))
        elif scenario_id == "sparse-metadata":
            checks.append(check("Sparse metadata produces no false alarm", before == after and not findings, "Empty mappings and a country are legitimate."))
        else:
            checks.append(check("Two deliveries, one materialization", store.connection.execute("SELECT COUNT(*) FROM silver WHERE work_id=?", (after["id"],)).fetchone()[0] == 1 and materialization_writes <= 1, "Canonical content is compared within a work ID."))
            checks.append(check("Both raw deliveries retained", all(store.connection.execute("SELECT 1 FROM bronze WHERE sha256=?", (d["sha256"],)).fetchone() for d in delivery_evidence), "Different DOI representations retain separate raw hashes."))
        result = {
            "id": scenario_id, "title": title, "kind": kind, "source_kind": source_kind,
            "description": description, "ticket": ticket, "expected_outcome": expected,
            "source": {"id": source_record["id"], "title": source_record["title"],
                       "url": provenance["url"] if is_observed else None, "doi": source_record.get("doi"),
                       "license": "CC0 metadata" if is_observed else "Synthetic fixture"},
            "bronze": {"sha256": bronze_sha, "source_sha256": provenance["sha256"] if is_observed else bronze_sha,
                       "immutable": True, "delivery_count": deliveries, "deliveries": delivery_evidence,
                       "record": source_record},
            "silver": {"record": after, "before": before, "after": after,
                       "materialization_count": 1, "materialization_writes_this_run": materialization_writes,
                       "content_sha256": digest(canonical_bytes(after))},
            "findings": findings, "outcome": statuses[scenario_id],
            "regression": {"passed": all(c["passed"] for c in checks), "checks": checks},
            "support_reply": replies[scenario_id],
            "metrics": {"deliveries": deliveries, "materializations": 1, "findings": len(findings),
                        "repairs": 1 if scenario_id == "affiliation-drop" else 0,
                        "abstentions": 1 if scenario_id == "sparse-metadata" else 0,
                        "affected_authorships": 1 if scenario_id in ("affiliation-drop", "orcid-conflict") else 0,
                        "fixture_authorships": len(source_record["authorships"]), "fixture_works": 1},
            "normalization_log": logs
        }
        store.record_run(result)
        return result
    finally:
        store.close()


def build_demo():
    from .evaluation import evaluate
    _, _, provenance = load_source()
    return {"meta": {"name": "The Repair Desk", "version": "1.0.0", "built_at": provenance["retrieved_at"],
            "license": "MIT code; CC0 source metadata",
            "disclosure": "Independent applicant-built prototype. Public OpenAlex metadata, deliberately injected faults, and fictional tickets. Not an OpenAlex product, production incident, or disambiguation model. No full-text paper content is included.",
            "determinism": "Output is deterministic for the pinned source hash and code version; built_at is the snapshot retrieval time.",
            "sources": [provenance]}, "scenarios": [replay(s) for s in SCENARIO_IDS], "evaluation": evaluate()}
