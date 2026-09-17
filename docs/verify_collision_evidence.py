#!/usr/bin/env python3
"""Verify the archived real case without making network requests."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/evidence/source-collision"


class Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag.lower() == "meta" and a.get("name"):
            self.tags.setdefault(a["name"].lower(), []).append(a.get("content", ""))


def doi(value):
    return value.lower().removeprefix("https://doi.org/")


def orcid(value):
    return value.lower().removeprefix("https://orcid.org/")


def verify():
    manifest = json.loads((EVIDENCE / "manifest.json").read_text())
    for receipt in manifest["responses"]:
        raw = (EVIDENCE / receipt["file"]).read_bytes()
        assert len(raw) == receipt["bytes"], receipt["file"]
        assert hashlib.sha256(raw).hexdigest() == receipt["sha256"], receipt["file"]
        assert receipt["http_status"] == 200, receipt["file"]
    work = json.loads((EVIDENCE / "openalex-work.json").read_text())
    registries = {
        name: json.loads((EVIDENCE / ("datacite-" + name + ".json")).read_text())["data"]["attributes"]
        for name in ("mizar", "tutoring", "zenodo-concept", "zenodo-v1", "zenodo-v2")
    }
    assert work["id"] == "https://openalex.org/W4385245566"
    assert doi(work["doi"]) == registries["mizar"]["doi"]
    assert work["title"] == registries["tutoring"]["titles"][0]["title"]
    assert work["title"] != registries["mizar"]["titles"][0]["title"]
    names = [a["raw_author_name"] for a in work["authorships"]]
    assert names == [c["name"] for c in registries["mizar"]["creators"]]
    oa_orcids = {orcid(a["author"]["orcid"]) for a in work["authorships"]}
    registry_orcids = {
        name: {orcid(i["nameIdentifier"]) for c in r["creators"] for i in c.get("nameIdentifiers", []) if i.get("nameIdentifierScheme") == "ORCID"}
        for name, r in registries.items()
    }
    assert len(oa_orcids & registry_orcids["mizar"]) == 9
    assert not oa_orcids & registry_orcids["tutoring"]
    assert not oa_orcids & registry_orcids["zenodo-concept"]
    assert not registry_orcids["tutoring"] & registry_orcids["zenodo-concept"]
    locations = {doi(l["id"][4:]) for l in work["locations"] if l["id"].startswith("doi:")}
    assert locations == {r["doi"] for r in registries.values()}
    for name in ("mizar", "tutoring"):
        parser = Meta()
        parser.feed((EVIDENCE / ("publisher-" + name + ".html")).read_text())
        assert doi(parser.tags["citation_doi"][0]) == registries[name]["doi"]
        assert parser.tags["citation_title"][0] == registries[name]["titles"][0]["title"]
        assert parser.tags["citation_author"] == [c["name"] for c in registries[name]["creators"]]
    for record in registries.values():
        assert any(r["relationType"] == "Cites" and r["relatedIdentifier"] == "arXiv:1706.03762" for r in record["relatedIdentifiers"])
    for name in ("zenodo-v1", "zenodo-v2"):
        assert any(r["relationType"] == "IsVersionOf" and r["relatedIdentifier"] == registries["zenodo-concept"]["doi"] for r in registries[name]["relatedIdentifiers"])
    return {
        "verified_receipts": len(manifest["responses"]),
        "http_status": 200,
        "work_id": work["id"],
        "location_count": len(work["locations"]),
        "doi_locations": len(locations),
        "title_families": len({r["titles"][0]["title"] for r in registries.values()}),
        "mizar_author_names_matched": len(names),
        "mizar_author_orcids_matched": len(oa_orcids & registry_orcids["mizar"]),
        "other_family_author_orcid_overlap": 0,
        "shared_cites_identifier": "arXiv:1706.03762",
        "root_cause_proven": False,
        "correction_applied": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
