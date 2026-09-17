"""Deterministic normalization, evidence checks, and append-only raw storage.

This prototype consumes public API-shaped JSON. It does not implement or claim
access to OpenAlex's production ETL, disambiguation models, or support queue.
"""
import copy
import hashlib
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RecordError(ValueError):
    pass


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def normalize_doi(value):
    """Canonicalize a DOI identifier, without changing the delivered evidence."""
    if not isinstance(value, str):
        return value
    clean = value.strip()
    clean = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", clean, flags=re.I)
    if re.fullmatch(r"10\.\d{4,9}/\S+", clean, flags=re.I):
        return "https://doi.org/" + clean.lower()
    return value


def normalize_orcid(value):
    """Return an ORCID only if its ISO 7064 MOD 11-2 checksum is valid."""
    if not isinstance(value, str):
        return None
    clean = re.sub(r"^https?://(?:www\.)?orcid\.org/", "", value.strip(), flags=re.I).upper()
    if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", clean):
        return None
    digits = clean.replace("-", "")
    total = 0
    for digit in digits[:15]:
        total = (total + int(digit)) * 2
    check = (12 - total % 11) % 11
    if digits[-1] != ("X" if check == 10 else str(check)):
        return None
    return "https://orcid.org/" + clean


def finding(code, severity, summary, path, before=None, after=None, action="review-only", evidence=None):
    return {"code": code, "severity": severity, "summary": summary, "path": path,
            "before": before, "after": after, "action": action, "evidence": evidence or []}


def normalize_record(raw):
    if not isinstance(raw, dict):
        raise RecordError("record must be a JSON object")
    if not isinstance(raw.get("id"), str) or not raw["id"].strip():
        raise RecordError("a nonempty work id is required; DOI is not a safe identity key")
    record = copy.deepcopy(raw)
    log = []
    old_doi = record.get("doi")
    new_doi = normalize_doi(old_doi)
    if old_doi != new_doi:
        record["doi"] = new_doi
        log.append({"path": "doi", "before": old_doi, "after": new_doi,
                    "reason": "Canonical DOI URL; source bytes retained in bronze."})
    return record, log


def review_record(record, source=None):
    """Return a repaired COPY and evidence. Identity conflicts are never repaired.

    Membership restoration is allowed only when the matching unique authorship
    in an intact source has the same mapped institution. It is a replay of
    source-supported metadata, not a new institutional disambiguation judgment.
    """
    repaired = copy.deepcopy(record)
    findings = []
    authorships = record.get("authorships", [])
    if not isinstance(authorships, list):
        findings.append(finding("MALFORMED_AUTHORSHIPS", "warning", "Authorships is not a list; inspection is deferred.",
                                "authorships", authorships, action="abstain"))
        return repaired, findings
    for index, authorship in enumerate(authorships):
        path = "authorships[{}]".format(index)
        if not isinstance(authorship, dict):
            findings.append(finding("MALFORMED_AUTHORSHIP", "warning", "Malformed authorship retained for review.", path,
                                    authorship, action="abstain"))
            continue
        author = authorship.get("author")
        author = author if isinstance(author, dict) else {}
        raw_orcid = normalize_orcid(authorship.get("raw_orcid"))
        resolved_orcid = normalize_orcid(author.get("orcid"))
        identity_conflict = bool(raw_orcid and resolved_orcid and raw_orcid != resolved_orcid)
        if identity_conflict:
            findings.append(finding("ORCID_CONFLICT", "warning",
                "Two valid ORCIDs disagree. Preserve the record and request identity review.", path + ".author.orcid",
                author.get("orcid"), author.get("orcid"), "review-only",
                [{"label": "Delivered raw ORCID", "path": path + ".raw_orcid", "value": authorship.get("raw_orcid")},
                 {"label": "Resolved author ORCID", "path": path + ".author.orcid", "value": author.get("orcid")},
                 {"label": "Decision boundary", "path": path, "value": "Neither identifier proves which identity is correct."}]))
        affiliations = authorship.get("affiliations", [])
        institutions = authorship.get("institutions", [])
        if (not isinstance(affiliations, list) or not isinstance(institutions, list)
                or any(not isinstance(a, dict) or not isinstance(a.get("institution_ids", []), list)
                       or any(not isinstance(i, str) or not i for i in a.get("institution_ids", [])) for a in affiliations)
                or any(not isinstance(i, dict) or not isinstance(i.get("id"), str) or not i["id"] for i in institutions)):
            findings.append(finding("MALFORMED_AFFILIATION_FIELDS", "warning",
                "Affiliations or institutions has an unexpected shape; no repair is safe.", path,
                action="abstain"))
            continue
        mapped_ids = set()
        for affiliation in affiliations:
            if isinstance(affiliation, dict) and isinstance(affiliation.get("institution_ids"), list):
                mapped_ids.update(i for i in affiliation["institution_ids"] if isinstance(i, str) and i)
        present_ids = {i.get("id") for i in institutions if isinstance(i, dict) and isinstance(i.get("id"), str)}
        missing = sorted(mapped_ids - present_ids)
        for institution_id in missing:
            source_institution = None
            if not identity_conflict and source and source.get("id") == record.get("id") and isinstance(source.get("authorships"), list):
                matches = [a for a in source["authorships"] if isinstance(a, dict)
                           and isinstance(a.get("author"), dict) and author.get("id")
                           and a["author"].get("id") == author.get("id")
                           and a.get("raw_author_name") == authorship.get("raw_author_name")
                           and a.get("raw_affiliation_strings") == authorship.get("raw_affiliation_strings")
                           and a.get("affiliations") == authorship.get("affiliations")
                           and a.get("raw_orcid") == authorship.get("raw_orcid")]
                if len(matches) == 1 and isinstance(matches[0].get("institutions"), list):
                    source_institution = next((i for i in matches[0]["institutions"]
                        if isinstance(i, dict) and i.get("id") == institution_id), None)
            safe = source_institution is not None
            prior = copy.deepcopy(repaired["authorships"][index].get("institutions", []))
            if safe:
                repaired["authorships"][index].setdefault("institutions", []).append(copy.deepcopy(source_institution))
            after = copy.deepcopy(repaired["authorships"][index].get("institutions", []))
            findings.append(finding("MAPPED_INSTITUTION_MISSING", "error",
                "An explicit affiliation mapping lost its institution membership." if safe else
                "An explicit affiliation mapping has no matching institution; intact source evidence is unavailable.",
                path + ".institutions", prior, after,
                "restore-from-bronze" if safe else "review-only",
                [{"label": "Mapped institution", "path": path + ".affiliations[].institution_ids", "value": institution_id},
                 {"label": "Materialized institution IDs", "path": path + ".institutions[].id", "value": sorted(present_ids)},
                 {"label": "Intact source institution", "path": "bronze." + path + ".institutions", "value": source_institution}]))
    return repaired, findings


class Store:
    def __init__(self, path=":memory:"):
        self.connection = sqlite3.connect(str(path))
        self.connection.executescript((ROOT / "schema.sql").read_text())

    def close(self):
        self.connection.close()

    def ingest(self, payload, source_kind):
        sha = digest(payload)
        self.connection.execute("INSERT OR IGNORE INTO bronze(sha256,payload,source_kind) VALUES (?,?,?)", (sha, payload, source_kind))
        self.connection.commit()
        return sha

    def materialize(self, record, bronze_sha):
        data = canonical_bytes(record)
        sha = digest(data)
        existing = self.connection.execute("SELECT content_sha256 FROM silver WHERE work_id=?", (record["id"],)).fetchone()
        if existing and existing[0] == sha:
            return False
        self.connection.execute("""INSERT INTO silver(work_id,content_sha256,normalized_json,bronze_sha256)
          VALUES(?,?,?,?) ON CONFLICT(work_id) DO UPDATE SET
          content_sha256=excluded.content_sha256,normalized_json=excluded.normalized_json,
          bronze_sha256=excluded.bronze_sha256,version=silver.version+1""", (record["id"], sha, data.decode(), bronze_sha))
        self.connection.commit()
        return True

    def record_run(self, scenario):
        result = self.connection.execute("INSERT INTO replay_runs(scenario_id,result_json) VALUES (?,?)", (scenario["id"], canonical_bytes(scenario).decode()))
        for item in scenario["findings"]:
            self.connection.execute("INSERT INTO findings(run_id,code,severity,evidence_json) VALUES (?,?,?,?)",
                (result.lastrowid, item["code"], item["severity"], canonical_bytes(item).decode()))
        self.connection.commit()

    def count(self, table):
        if table not in {"bronze", "silver", "findings", "replay_runs"}:
            raise ValueError("unsupported table")
        return self.connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
