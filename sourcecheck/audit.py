"""Compare public metadata sources without inferring or applying corrections.

Title equality is a reproducible text rule, not a probability of record identity.
All HTTP bodies, including 404s, become content-addressed evidence receipts.
"""
import hashlib
import html
from http.client import HTTPException
from html.parser import HTMLParser
import json
import re
import socket
import time
import unicodedata
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


SCHEMA_VERSION = "1.0"
RULE_VERSION = "title-equality-v1"
MAX_INPUT_LENGTH = 512
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 5
MAX_RETRY_WAIT_SECONDS = 2
MAX_REGISTRY_DOIS = 6
MAX_RELATIONS = 50
TRANSIENT_STATUSES = {408, 429, 500, 502, 503, 504}
ALLOWED_HOSTS = {"api.openalex.org", "api.crossref.org", "api.datacite.org"}
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s?#\\]+\Z", re.I)
WID_PATTERN = re.compile(r"W\d+\Z", re.I)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def valid_doi(value):
    return (isinstance(value, str) and len(value) <= MAX_INPUT_LENGTH
            and not any(ord(c) < 32 or ord(c) == 127 for c in value)
            and bool(DOI_PATTERN.fullmatch(value)))


def parse_input(value):
    """Accept one work ID or DOI; never accept an arbitrary fetch URL."""
    if not isinstance(value, str) or not value or len(value) > MAX_INPUT_LENGTH:
        raise ValueError("Input must contain 1 to 512 characters.")
    if value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("Whitespace padding and control characters are not accepted.")
    raw = value
    if WID_PATTERN.fullmatch(value):
        return {"raw": raw, "kind": "work_id", "normalized": value.upper(), "input_doi": None}
    if valid_doi(value):
        doi = value.lower()
        return {"raw": raw, "kind": "doi", "normalized": doi, "input_doi": doi}
    parts = urlsplit(value)
    if (parts.scheme != "https" or not parts.netloc or parts.username is not None
            or parts.password is not None or parts.query or parts.fragment
            or "?" in value or "#" in value or parts.netloc not in {"openalex.org", "api.openalex.org", "doi.org", "dx.doi.org"}):
        raise ValueError("Use a raw W ID, DOI, or plain HTTPS OpenAlex/doi.org URL without credentials, ports, queries, or fragments.")
    try:
        path = unquote(parts.path, errors="strict")
    except UnicodeError as exc:
        raise ValueError("Invalid URL encoding.") from exc
    if parts.netloc in {"openalex.org", "api.openalex.org"}:
        pattern = r"/works/(W\d+)" if parts.netloc == "api.openalex.org" else r"/(W\d+)"
        match = re.fullmatch(pattern, path, re.I)
        if not match:
            raise ValueError("OpenAlex URLs must identify one W-number work.")
        return {"raw": raw, "kind": "work_id", "normalized": match.group(1).upper(), "input_doi": None}
    doi = path[1:] if path.startswith("/") else ""
    if not valid_doi(doi):
        raise ValueError("The DOI URL does not contain a supported DOI.")
    return {"raw": raw, "kind": "doi", "normalized": doi.lower(), "input_doi": doi.lower()}


def doi_from_value(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = parse_input(value)
        return parsed["input_doi"]
    except ValueError:
        return None


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {"br", "p", "div", "li", "section", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        self.handle_starttag(tag, [])


def _complete_markup_prefix(text):
    """Drop an unfinished markup-like tail before HTMLParser sees it.

    HTMLParser.close() changed its treatment of unfinished tags between Python
    releases. Define that boundary here: '<' followed immediately by a letter,
    slash+letter, '!' or '?' starts markup, and a tag needs an unquoted '>'.
    A literal comparison such as 'x < y' or 'x < 3' remains text.
    """
    index = 0
    while True:
        start = text.find("<", index)
        if start < 0:
            return text
        if text.startswith("<!--", start):
            end = text.find("-->", start + 4)
            if end < 0:
                return text[:start]
            index = end + 3
            continue
        tag = re.match(r"</?[A-Za-z][\w:.-]*(?=[\s/>]|$)", text[start:])
        if not tag and not text.startswith(("<!", "<?"), start):
            index = start + 1
            continue
        quote_char = None
        end = start + 1
        while end < len(text):
            char = text[end]
            if quote_char:
                if char == quote_char:
                    quote_char = None
            elif char in {"\"", "'"}:
                quote_char = char
            elif char == ">":
                break
            end += 1
        if end == len(text):
            return text[:start]
        index = end + 1


def normalize_title(value):
    if not isinstance(value, str):
        return ""
    parser = _TextExtractor()
    parser.feed(_complete_markup_prefix(html.unescape(value)))
    parser.close()
    text = unicodedata.normalize("NFKC", html.unescape("".join(parser.parts))).casefold()
    text = "".join(" " if unicodedata.category(c)[0] in {"P", "S"} else c for c in text)
    return " ".join(text.split())


def token_jaccard(left, right):
    a, b = set(left.split()), set(right.split())
    return len(a & b) / len(a | b) if a and b else None


def _safe_url(url):
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc not in ALLOWED_HOSTS
            or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment):
        raise ValueError("Fetch URL is outside the fixed public API allowlist.")
    prefixes = {"api.openalex.org": "/works/", "api.crossref.org": "/works/", "api.datacite.org": "/dois/"}
    if not parts.path.startswith(prefixes[parts.netloc]):
        raise ValueError("Only fixed public work/DOI endpoints are permitted.")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Provider redirects are receipted as HTTP errors. Never follow an arbitrary Location.
        return None


class SourceFailure(Exception):
    def __init__(self, kind, message, status=None):
        super().__init__(message)
        self.kind = kind
        self.status = status


class EvidenceClient:
    """At most two attempts per URL, five seconds each, two MiB per body.

    A Retry-After longer than the two-second wait cap ends the request rather
    than retrying earlier than the provider asked. Redirects are not followed.
    """
    def __init__(self, evidence_dir, opener=None, sleeper=time.sleep, now=utc_now):
        self.evidence_dir = Path(evidence_dir)
        self.evidence = []
        self.opener = opener or build_opener(_NoRedirect())
        self.sleeper = sleeper
        self.now = now

    def _receipt(self, url, status, payload, attempt, truncated=False, error_kind=None):
        sha = hashlib.sha256(payload).hexdigest()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        path = self.evidence_dir / (sha + ".body")
        try:
            with path.open("xb") as handle:
                handle.write(payload)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise SourceFailure("evidence_collision", "Existing evidence does not match its content-addressed name.")
        receipt = {"url": url, "http_status": status, "retrieved_at": self.now(),
                   "sha256": sha, "bytes": len(payload), "path": str(path.resolve()),
                   "attempt": attempt, "truncated": truncated, "error_kind": error_kind}
        self.evidence.append(receipt)
        return receipt

    def _retry_wait(self, headers):
        value = headers.get("Retry-After") if headers else None
        if value is None:
            return 0.25
        try:
            wait = float(value)
        except (TypeError, ValueError):
            try:
                parsed = parsedate_to_datetime(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                wait = (parsed - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                return None
        return max(0, wait) if 0 <= wait <= MAX_RETRY_WAIT_SECONDS else None

    def get_json(self, url):
        _safe_url(url)
        for attempt in (1, 2):
            response = None
            try:
                request = Request(url, headers={"Accept": "application/json", "User-Agent": "RepairDeskSourceCheck/1.0 (read-only metadata audit)"})
                try:
                    response = self.opener.open(request, timeout=TIMEOUT_SECONDS)
                    status = response.status
                except HTTPError as exc:
                    response = exc
                    status = exc.code
                body = response.read(MAX_RESPONSE_BYTES + 1)
                truncated = len(body) > MAX_RESPONSE_BYTES
                body = body[:MAX_RESPONSE_BYTES]
                self._receipt(url, status, body, attempt, truncated)
                if truncated:
                    raise SourceFailure("response_too_large", "Response exceeds the two MiB evidence cap; saved prefix is marked truncated.", status)
                if status in TRANSIENT_STATUSES and attempt == 1:
                    wait = self._retry_wait(response.headers)
                    if wait is not None:
                        self.sleeper(wait)
                        continue
                if status != 200:
                    kind = "not_found" if status == 404 else ("rate_limited" if status == 429 else "http_error")
                    raise SourceFailure(kind, "Public API returned HTTP {}.".format(status), status)
                try:
                    return json.loads(body)
                except (UnicodeError, ValueError) as exc:
                    raise SourceFailure("invalid_json", "API response was not valid JSON.", status) from exc
            except (URLError, TimeoutError, socket.timeout, ConnectionError, OSError, HTTPException) as exc:
                self.evidence.append({"url": url, "http_status": None, "retrieved_at": self.now(),
                    "sha256": None, "bytes": 0, "path": None, "attempt": attempt,
                    "truncated": False, "error_kind": "network_error"})
                if attempt == 1:
                    self.sleeper(0.25)
                    continue
                raise SourceFailure("network_error", "Public API request failed after two bounded attempts.") from exc
            finally:
                if response is not None:
                    response.close()
        raise SourceFailure("network_error", "Public API request did not complete.")


def _strings(value):
    return [item for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def _unique(values):
    return list(dict.fromkeys(values))


def _registry_base(provider, doi):
    return {"provider": provider, "doi": doi, "status": "found", "main_titles": [], "alternate_titles": [],
            "alternate_title_details": [], "subtitles": [], "author_names": [], "author_family_names": [], "related_identifiers": [],
            "related_identifier_count": 0, "related_identifiers_truncated": False}


def _relation(identifier, identifier_type, relation_type):
    if not isinstance(identifier, str) or not isinstance(relation_type, str):
        return None
    return {"identifier": identifier, "identifier_type": identifier_type if isinstance(identifier_type, str) else "unknown",
            "relation_type": relation_type, "merge_evidence": False}


def parse_registry(provider, doi, document):
    item = _registry_base(provider, doi)
    relations = []
    if provider == "crossref":
        message = document.get("message") if isinstance(document, dict) else None
        if not isinstance(message, dict):
            raise SourceFailure("invalid_schema", "Crossref response has no message object.", 200)
        item["main_titles"] = _strings(message.get("title"))
        item["subtitles"] = _strings(message.get("subtitle"))
        item["alternate_titles"] = _strings(message.get("short-title"))
        item["alternate_title_details"] = [{"title": t, "type": "short-title"} for t in item["alternate_titles"]]
        authors = message.get("author", [])
        for author in authors if isinstance(authors, list) else []:
            if not isinstance(author, dict):
                continue
            family = author.get("family")
            name = " ".join(s for s in [author.get("given"), family] if isinstance(s, str) and s)
            if not name and isinstance(author.get("name"), str):
                name = author["name"]
            if name:
                item["author_names"].append(name)
            if isinstance(family, str) and family:
                item["author_family_names"].append(family)
        relationships = message.get("relation", {})
        for relation_type, identifiers in relationships.items() if isinstance(relationships, dict) else []:
            for identifier in identifiers if isinstance(identifiers, list) else []:
                if isinstance(identifier, dict):
                    relation = _relation(identifier.get("id"), identifier.get("id-type"), relation_type)
                    if relation:
                        relations.append(relation)
    else:
        data = document.get("data") if isinstance(document, dict) else None
        attributes = data.get("attributes") if isinstance(data, dict) else None
        if not isinstance(attributes, dict):
            raise SourceFailure("invalid_schema", "DataCite response has no attributes object.", 200)
        titles = attributes.get("titles", [])
        for title in titles if isinstance(titles, list) else []:
            if not isinstance(title, dict) or not isinstance(title.get("title"), str) or not title["title"].strip():
                continue
            kind = title.get("titleType")
            if not kind:
                item["main_titles"].append(title["title"])
            elif kind == "Subtitle":
                item["subtitles"].append(title["title"])
            else:
                item["alternate_titles"].append(title["title"])
                item["alternate_title_details"].append({"title": title["title"], "type": kind})
        creators = attributes.get("creators", [])
        for creator in creators if isinstance(creators, list) else []:
            if not isinstance(creator, dict):
                continue
            family = creator.get("familyName")
            name = creator.get("name")
            if not isinstance(name, str) or not name:
                name = " ".join(s for s in [creator.get("givenName"), family] if isinstance(s, str) and s)
            if name:
                item["author_names"].append(name)
            if isinstance(family, str) and family:
                item["author_family_names"].append(family)
            elif creator.get("nameType") != "Organizational" and isinstance(name, str) and "," in name:
                item["author_family_names"].append(name.split(",", 1)[0].strip())
        relationships = attributes.get("relatedIdentifiers", [])
        for relationship in relationships if isinstance(relationships, list) else []:
            if isinstance(relationship, dict):
                relation = _relation(relationship.get("relatedIdentifier"), relationship.get("relatedIdentifierType"), relationship.get("relationType"))
                if relation:
                    relations.append(relation)
    item["related_identifier_count"] = len(relations)
    item["related_identifiers"] = relations[:MAX_RELATIONS]
    item["related_identifiers_truncated"] = len(relations) > MAX_RELATIONS
    return item


def _failure(provider, failure, doi=None):
    return {"provider": provider, "doi": doi, "kind": failure.kind, "http_status": failure.status, "message": str(failure)}


def get_registry(doi, client, errors):
    for provider, prefix in (("crossref", "https://api.crossref.org/works/"), ("datacite", "https://api.datacite.org/dois/")):
        try:
            document = client.get_json(prefix + quote(doi, safe="/"))
            return parse_registry(provider, doi, document)
        except SourceFailure as exc:
            errors.append(_failure(provider, exc, doi))
            if provider == "crossref" and exc.status == 404:
                continue
            result = _registry_base(provider, doi)
            result["status"] = "not_found" if exc.status == 404 else "error"
            return result


def _extract_work(document):
    if not isinstance(document, dict) or not isinstance(document.get("id"), str):
        raise SourceFailure("invalid_schema", "OpenAlex response lacks an identifiable work.", 200)
    names, families, location_dois = [], [], []
    authorships = document.get("authorships", [])
    for authorship in authorships if isinstance(authorships, list) else []:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author")
        name = authorship.get("raw_author_name")
        if not isinstance(name, str) or not name:
            name = author.get("display_name") if isinstance(author, dict) else None
        if isinstance(name, str) and name.strip():
            names.append(name)
            # OpenAlex's work payload has display names, not reliable surname fields.
            # This fallback is explicitly labelled heuristic in the report.
            families.append(name.split(",", 1)[0].strip() if "," in name else name.strip().split()[-1])
    locations = document.get("locations", [])
    if isinstance(document.get("primary_location"), dict):
        locations = ([document["primary_location"]] + locations) if isinstance(locations, list) else [document["primary_location"]]
    for location in locations if isinstance(locations, list) else []:
        if not isinstance(location, dict):
            continue
        for field in ("doi", "landing_page_url", "pdf_url"):
            doi = doi_from_value(location.get(field))
            if doi:
                location_dois.append(doi)
    return {"id": document["id"], "doi": doi_from_value(document.get("doi")),
            "title": document.get("title") if isinstance(document.get("title"), str) else document.get("display_name"),
            "author_names": names, "author_family_names": families,
            "author_family_name_method": "Heuristic: comma-leading segment or last whitespace token; not verified personal identity.",
            "location_dois": _unique(location_dois)}


def _family_overlap(work, registry):
    a = {normalize_title(x) for x in work["author_family_names"] if normalize_title(x)}
    b = {normalize_title(x) for x in registry["author_family_names"] if normalize_title(x)}
    shared = sorted(a & b)
    return {"shared": shared, "work_count": len(a), "registry_count": len(b), "shared_count": len(shared),
            "work_fraction": len(shared) / len(a) if a and b else None,
            "registry_fraction": len(shared) / len(b) if a and b else None,
            "note": "Unique family-name token overlap is supporting or contradicting context, never an identity decision; OpenAlex names are parsed heuristically."}


def _source_conflicts(sources):
    titles = _unique(normalize_title(t) for s in sources for t in s["main_titles"] if normalize_title(t))
    pairs = []
    for index, left in enumerate(sources):
        left_titles = {normalize_title(t) for t in left["main_titles"] if normalize_title(t)}
        for right in sources[index + 1:]:
            right_titles = {normalize_title(t) for t in right["main_titles"] if normalize_title(t)}
            if left_titles and right_titles and not left_titles & right_titles:
                pairs.append([left["doi"], right["doi"]])
    related = {}
    for source in sources:
        for relation in source["related_identifiers"]:
            key = (relation["identifier"].casefold(), relation["relation_type"].casefold())
            if key not in related:
                related[key] = dict(relation, source_dois=[])
            if source["doi"] not in related[key]["source_dois"]:
                related[key]["source_dois"].append(source["doi"])
    common = [value for value in related.values() if len(value["source_dois"]) > 1]
    return {"distinct_normalized_main_titles": titles,
            "divergent_source_doi_pairs": pairs,
            "common_related_identifiers": common,
            "note": "Shared citation targets are never identity evidence. Version relations are review hints only. Distinct titles can be legitimate versions or translations; this audit does not establish conflation or its cause."}


def audit(value, evidence_dir, client=None):
    parsed = parse_input(value)
    client = client or EvidenceClient(evidence_dir)
    report = {"schema_version": SCHEMA_VERSION, "rule_version": RULE_VERSION, "checked_at": utc_now(),
              "status": "inconclusive", "summary": "Source evidence is insufficient for a title comparison.",
              "input": parsed, "work": None, "registry": None, "registry_sources": [], "comparison": None,
              "signals": [], "evidence": client.evidence, "errors": [], "source_conflicts": None,
              "scope": {"registry_doi_limit": MAX_REGISTRY_DOIS, "registry_dois_checked": [], "registry_dois_omitted": [],
                        "all_selected_registry_sources_read": False},
              "policy": "Read-only comparison. Review is a request for investigation, not an error verdict. No correction, merge, or identity assignment is generated."}
    identity = parsed["normalized"] if parsed["kind"] == "work_id" else "https://doi.org/" + parsed["input_doi"]
    url = "https://api.openalex.org/works/" + quote(identity, safe=":/")
    try:
        work = _extract_work(client.get_json(url))
    except SourceFailure as exc:
        report["errors"].append(_failure("openalex", exc))
        report["summary"] = "OpenAlex evidence could not be read; no comparison decision was made."
        return report
    report["work"] = work
    selected_doi = parsed["input_doi"] or work["doi"]
    if not selected_doi:
        report["signals"].append("no_comparable_doi")
        report["summary"] = "No comparable DOI was supplied or present on the OpenAlex work."
        return report
    doi_mismatch = bool(parsed["input_doi"] and work["doi"] and parsed["input_doi"] != work["doi"])
    if doi_mismatch:
        report["signals"].append("input_doi_differs_from_openalex_canonical_doi")
    candidates = _unique([selected_doi] + ([work["doi"]] if work["doi"] else []) + work["location_dois"])
    report["scope"]["registry_dois_checked"] = candidates[:MAX_REGISTRY_DOIS]
    report["scope"]["registry_dois_omitted"] = candidates[MAX_REGISTRY_DOIS:]
    sources = [get_registry(doi, client, report["errors"]) for doi in candidates[:MAX_REGISTRY_DOIS]]
    report["registry_sources"] = sources
    report["scope"]["all_selected_registry_sources_read"] = all(s["status"] == "found" for s in sources)
    if not report["scope"]["all_selected_registry_sources_read"]:
        report["signals"].append("registry_source_unavailable")
    report["registry"] = primary = sources[0]
    report["source_conflicts"] = _source_conflicts(sources)
    work_title = normalize_title(work["title"])
    registry_titles = [normalize_title(t) for t in primary["main_titles"]]
    usable_titles = [t for t in registry_titles if t]
    matched = next((t for t in primary["main_titles"] if work_title and normalize_title(t) == work_title), None)
    scores = [token_jaccard(work_title, t) for t in usable_titles]
    report["comparison"] = {"selected_doi": selected_doi, "input_doi_differs_from_canonical": doi_mismatch,
        "normalized_work_title": work_title, "normalized_registry_main_titles": registry_titles,
        "matched_main_title": matched, "token_jaccard": max((s for s in scores if s is not None), default=None),
        "token_jaccard_note": "Descriptive overlap of normalized word sets; not confidence, probability, or an identity rule.",
        "author_family_overlap": _family_overlap(work, primary)}
    if primary["status"] != "found" or not work_title or not usable_titles:
        report["signals"].append("missing_usable_main_title_or_registry")
        return report
    if matched:
        report["status"] = "aligned"
        report["summary"] = "The OpenAlex title equals a registry main title under the documented text rule. This does not prove record identity."
    else:
        report["status"] = "review"
        report["signals"].append("title_divergence")
        report["summary"] = "The OpenAlex and requested DOI registry main titles differ. Review the source records; no error verdict or automatic correction is made."
    if doi_mismatch:
        report["status"] = "review"
        report["summary"] = "The requested DOI differs from OpenAlex's canonical DOI. Source relationships need review; version families can legitimately have multiple DOIs."
    if report["source_conflicts"]["divergent_source_doi_pairs"]:
        report["signals"].append("multiple_registry_main_titles_across_location_dois")
        report["status"] = "review"
        report["summary"] = "The bounded DOI source set contains differing registry main titles. Review their authors and relationships; versions or translations may explain differences."
    elif report["status"] == "aligned" and not report["scope"]["all_selected_registry_sources_read"]:
        report["status"] = "inconclusive"
        report["summary"] = "The primary title matches, but one or more selected registry sources could not be read. The bounded source audit is incomplete."
    return report
