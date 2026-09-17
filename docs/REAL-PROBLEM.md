# SourceCheck: a real OpenAlex source conflict

**Prepared for Shrey Patel's OpenAlex application. Evidence captured September 17, 2026 (UTC).**

SourceCheck checks a practical question: **do the source records attached to one OpenAlex work describe the same research?** It produces a review packet with the original responses, the conflicting fields, and the evidence needed to investigate. It does not change OpenAlex.

This project started with a real public record, not an injected error. The earlier Repair Desk's synthetic replay scenarios are not evidence for the findings below.

## 1. The verified problem

At capture time, [OpenAlex work W4385245566](https://api.openalex.org/works/W4385245566) had:

- Primary DOI: `10.4230/lipics.itp.2023.19`.
- Title: **Exploiting Generative AI to Scale up Intelligent Tutoring Systems**.
- Nine author names and nine ORCIDs matching a different title: **MizAR 60 for Mizar 50**.
- Seven locations, including five DOI locations describing three distinct title/author families.

For the primary DOI, [DataCite's registry record](https://api.datacite.org/dois/10.4230/lipics.itp.2023.19) and [the publisher's page](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITP.2023.19) agree on **MizAR 60 for Mizar 50**. The publisher's `citation_doi`, `citation_title`, and all nine `citation_author` values are machine-readable. The nine OpenAlex author ORCIDs match the nine registered creator ORCIDs.

The OpenAlex title is not simply an unexplained spelling variation. It exactly matches a second DOI location's registered title and publisher page, with a different set of authors and a different publication year.

### Source ledger

| Family | Registered DOI(s) | Registered title | Creators / year | Relationship evidence |
| --- | --- | --- | --- | --- |
| A | `10.4230/lipics.itp.2023.19` | MizAR 60 for Mizar 50 | Jan Jakubův and eight coauthors / 2023 | Primary OpenAlex DOI; all nine author names and ORCIDs agree. |
| B | `10.4230/oasics.icpec.2026.2` | Exploiting Generative AI to Scale up Intelligent Tutoring Systems | Miguel Ferreira; José Paulo Leal / 2026 | Its title is the current OpenAlex title; neither creator ORCID overlaps family A. |
| C | `10.5281/zenodo.21230429`, `10.5281/zenodo.21230430`, `10.5281/zenodo.21230434` | Inline Hardware KV-Cache Compression for Long-Context Transformer Inference: An Architectural Case for a Memory-Path Compression Engine | Alexander Novickis / 2026 | The three DOIs have explicit `HasVersion` / `IsVersionOf` relations. No creator ORCID overlaps family A or B. |

The Zenodo records are an important control: **multiple DOIs do not, by themselves, prove an error.** The version relations explain why those three belong together. Those relations do not connect them to either Dagstuhl paper.

DataCite and the Dagstuhl landing pages are two corroborating retrieval surfaces, not two independent publishers: the publisher deposits its DOI metadata in the registry. We therefore preserve their provenance and describe agreement, not an independent two-vote truth score.

## 2. Why this matters

A reader, citation exporter, or agent trusting only the OpenAlex work's primary DOI and title can produce a citation with one paper's DOI and another paper's title. The attached source links can also send a reader to materially different publications. This example demonstrates that risk directly; it does not measure how often it occurs across OpenAlex.

A title-only repair would hide part of the problem. Changing the title to “MizAR 60 for Mizar 50” would leave the unrelated tutoring and hardware-compression locations attached. Citation edges, topics, authorship assignments, and extracted text might also require review, but this investigation has not established which derived fields are affected.

**The safe actionable output is a source-conflict review packet.** A maintainer can use it to inspect source association, decide whether a work split is appropriate, and rebuild affected derived data. This artifact does not make that upstream decision.

## 3. The solution

SourceCheck is a read-only audit tool and evidence viewer. It accepts a work identifier or DOI, obtains the public work record, checks registered DOI metadata, and exposes incompatible bibliographic identities instead of silently selecting a title.

The Python CLI runs locally with the standard library. The shared website runs the audit in the browser and offers the captured case before a live recheck. The available outcomes are **aligned**, **review**, and **inconclusive**; aligned means the compared titles agree, not that authorship or every property of the work has been validated. An audit checks at most six selected/canonical/location DOI records. Crossref is queried first; a Crossref 404 falls back to DataCite. Network failures, missing evidence, and the DOI cap limit coverage.

The implementation follows these rules:

1. **Preserve the input.** Keep original HTTP response bytes, source URL, retrieval time, HTTP status, byte count, and SHA-256 digest. A hash proves the captured bytes have not changed; it does not prove the source was correct or immutable.
2. **Separate identifiers from relations.** The work's DOI and DOI locations identify source records. `Cites`, `References`, and `IsPartOf` are not evidence that two resources are the same work.
3. **Compare DOI-specific claims.** The live tool compares registered titles and displays creator-name and relationship context. The independent case verifier additionally checks all nine ORCIDs in the preserved raw metadata. Normalize DOI casing and URI prefixes without rewriting titles into agreement.
4. **Respect version links.** `HasVersion` and `IsVersionOf` are evidence of a family relationship, not permission to erase versions or merge their identifiers blindly.
5. **Explain disagreements.** Report which DOI supplies each title and author set. Distinguish a title difference from a multi-source identity conflict.
6. **Escalate ambiguous corrections.** Produce a review packet. Do not overwrite a global title or split records automatically on title similarity or creator overlap alone.

The useful fix is at the decision boundary: conflicting source evidence is made visible before a downstream consumer trusts the record or a repair process overwrites it. Upstream data repair still requires OpenAlex's own curation and pipeline access.

### Investigative lead, not a proven cause

All five registered DOI records contain `relationType: Cites` with `relatedIdentifier: arXiv:1706.03762`. That common citation is an observable fact. The [DataCite relationship documentation](https://support.datacite.org/docs/connecting-to-works) distinguishes reference relationships from identity and version relationships.

One plausible hypothesis is that a citation identifier was treated as an identity signal somewhere in ingestion or merging. **This is not a demonstrated root cause.** A shared citation is common in research metadata, and there is no access here to OpenAlex's internal merge logs or production pipeline. The proposed invariant remains useful regardless: a `Cites` edge must not, on its own, equate two works.

## 4. Proof and reproducibility

### A bounded investigation beyond one case

After discovering the conflict and a neighboring mismatch, we checked the first 30 numbered DOI suffixes (`1` through `30`) from [LIPIcs volume 268: ITP 2023](https://drops.dagstuhl.de/entities/volume/LIPIcs-volume-268). The volume lists 38 numbered contributions plus front matter; this is a contiguous targeted subset, not the whole volume.

All 30 OpenAlex and 30 DataCite lookups eventually returned HTTP 200. Five transient failures were retried once and their failed-attempt metadata was retained. Titles were compared after Unicode NFKC normalization, case folding, and collapsing punctuation/whitespace into word boundaries. **25 pairs agreed and five differed.** The five suffixes were `13`, `17`, `18`, `19`, and `26`.

| DOI suffix | OpenAlex title | DataCite registered title |
| --- | --- | --- |
| 13 | Formalising the Krull Topology in Lean | Formalizing Norm Extensions and Applications to Number Theory |
| 17 | Isabelle: The Next 700 Theorem Provers | LISA - A Modern Proof System |
| 18 | Robust Mean Estimation by All Means (Short Paper) | Semantic Foundations of Higher-Order Probabilistic Programs in Isabelle/HOL |
| 19 | Exploiting Generative AI to Scale up Intelligent Tutoring Systems | MizAR 60 for Mizar 50 |
| 26 | Automatic Repair of Real Bugs: An Experience Report on the Defects4J Dataset | Proof Repair Infrastructure for Supervised Models: Building a Large Proof Repair Dataset |

These are five title disagreements, not five fully adjudicated merge errors. This cohort was chosen after finding a problem in the volume. It provides additional reproducible review candidates, **not an OpenAlex-wide error rate, detector precision, or recall estimate**. Eleven ordered name lists also differed, but name ordering and formatting make that unsuitable as an error count.

The [cohort summary](../data/evidence/title-divergence/summary.json) contains each comparison. Its [manifest](../data/evidence/title-divergence/manifest.json) holds 70 successful original-response receipts for the cohort, initial discovery, publisher checks, and controls. These include two useful controls: suffix 20 agrees on title and names, and a supposedly missing IEEE DOI from an open public issue now resolves and matches Crossref. Open issues were treated as leads to recheck, not proof of a current defect. The [discovery log](evidence-research.md) records that process.

The independently captured case is in [`data/evidence/source-collision/`](../data/evidence/source-collision/). The [manifest](../data/evidence/source-collision/manifest.json) records eight unmodified HTTP response bodies: one OpenAlex response, five DataCite responses, and two publisher pages. All returned HTTP 200. Requests were captured between `2026-09-17T17:22:15Z` and `2026-09-17T17:22:17Z`.

### Reproduce the archived facts without network access

From the repository root:

```bash
python3 docs/verify_collision_evidence.py
```

This verifies all eight byte counts and SHA-256 hashes, the two publisher DOI/title/author metadata sets, the five DOI locations, nine matching author names and ORCIDs, the three distinct registered titles, the Zenodo version links, and the shared typed citation. It does not contact any service.

Expected key outputs:

```json
{
  "verified_receipts": 8,
  "location_count": 7,
  "doi_locations": 5,
  "title_families": 3,
  "mizar_author_names_matched": 9,
  "mizar_author_orcids_matched": 9,
  "other_family_author_orcid_overlap": 0,
  "root_cause_proven": false,
  "correction_applied": false
}
```

### Recheck current public sources

Run the actual audit from the repository root:

```bash
python3 -m sourcecheck audit W4385245566 \
  --output /tmp/sourcecheck-report.json \
  --evidence-dir /tmp/sourcecheck-evidence
```

A raw DOI such as `10.4230/lipics.itp.2023.19` can replace the work ID. The output is a JSON review packet and captured HTTP evidence, not a change request to OpenAlex. To verify the complete archived case and cohort calculations without network access:

```bash
python3 scripts/verify_evidence.py
```

For direct source inspection:

```bash
curl 'https://api.openalex.org/works/W4385245566'
curl 'https://api.datacite.org/dois/10.4230/lipics.itp.2023.19'
curl 'https://api.datacite.org/dois/10.4230/oasics.icpec.2026.2'
```

The public records may be corrected after capture. If a live recheck differs, preserve the new receipt and report that change rather than forcing it to match this report. The captured evidence supports a statement about the capture time.

### Integrity ledger

| Captured file | Bytes | SHA-256 |
| --- | ---: | --- |
| `openalex-work.json` | 28,800 | `5529440446752467ff2c6b6f41e0f2098d8cf67aab1cd9673e1d6d35f146b69e` |
| `datacite-mizar.json` | 31,620 | `dd3bd127b81660f435ce82674cbb416bcbf886f55dfb073380bf5f89bf0658cc` |
| `datacite-tutoring.json` | 22,514 | `3e5299e95990dabd7dd13c57545a3dde9b2a9c8f49a29084662b2bab48ecc1fe` |
| `datacite-zenodo-concept.json` | 12,251 | `5451b1fd0d7f92a54538a796043a53c5961e8bc2eafca244dfb78fc372c7a0e3` |
| `datacite-zenodo-v1.json` | 12,190 | `f64eda439bb712006cc06e49d142eb01a04faa7972dc758542e14ba245b7868e` |
| `datacite-zenodo-v2.json` | 12,242 | `add0cedee675ad00f1fd8a5135912788f3294fb57a61beebffcf4cec7969a323` |
| `publisher-mizar.html` | 176,794 | `65f9b50e26d765df5a540c073b77ff8d1075538a743903047835a7ab7d364a2e` |
| `publisher-tutoring.html` | 108,186 | `f9df38c84ab9fe791d5c039e5c4164647fe14c47d61ccffee6b55e8b78dbff01` |

The SHA-256 values cover complete raw response bodies, not normalized fields. Independently fetched responses can differ in volatile metadata or serialization while agreeing on the bibliographic facts.

## 5. Scope and limits

- This is an externally verified case and a working audit workflow, not an upstream fix or a claim of affiliation with OpenAlex.
- The case was found during targeted investigation. It is not a random sample and cannot establish an error rate.
- The automatic decision is title-based; creator-name overlap is descriptive context. Matching titles alone do not prove identity, and matching titles with conflicting authors can still return `aligned`. Different titles alone do not prove unrelated works. Version relations, translations, corrected metadata, and incomplete authorship data all matter.
- DOI discovery recognizes raw DOIs and DOI resolver URLs in supported location fields. It does not extract every DOI embedded in arbitrary publisher paths.
- Registry records can be incomplete or incorrect. Missing registry evidence is an inconclusive result, not evidence of source conflict.
- No claim is made about OpenAlex's existing internal quality checks, exact merge implementation, date of introduction, or unseen production data.
- A maintainer must review any proposed split and downstream consequences. No correction was submitted and no upstream record was altered.
- Public metadata and local processing are used. No paid API account, model, database, or hosted compute service is required. The shared site uses Vercel's free Hobby plan.

## 6. Sources

1. [OpenAlex work W4385245566](https://api.openalex.org/works/W4385245566): the observed aggregate record.
2. [DataCite: MizAR 60 for Mizar 50](https://api.datacite.org/dois/10.4230/lipics.itp.2023.19): DOI-specific title, nine creators/ORCIDs, and relations.
3. [Dagstuhl: MizAR 60 for Mizar 50](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITP.2023.19): publisher title and citation metadata.
4. [DataCite: tutoring paper](https://api.datacite.org/dois/10.4230/oasics.icpec.2026.2) and [Dagstuhl publisher page](https://drops.dagstuhl.de/entities/document/10.4230/OASIcs.ICPEC.2026.2): different creators; exact match to OpenAlex's observed title.
5. [DataCite: Zenodo family](https://api.datacite.org/dois/10.5281/zenodo.21230429), [v1](https://api.datacite.org/dois/10.5281/zenodo.21230430), and [v2](https://api.datacite.org/dois/10.5281/zenodo.21230434): hardware-compression title, creator, and explicit version relations.
6. [DataCite: connecting to works](https://support.datacite.org/docs/connecting-to-works) and [contributing citations and references](https://support.datacite.org/docs/contributing-citations-and-references): typed relationship semantics.

Implementation, tests, and evidence are in [Shrey Patel's public repository](https://github.com/Shreyp087/OpenAlex). AI assistance was used for research and implementation; claims are grounded in the preserved public evidence and executable checks.
