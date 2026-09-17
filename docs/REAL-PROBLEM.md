# SourceCheck: a real OpenAlex source conflict

**Prepared for Shrey Patel's OpenAlex application. Evidence captured September 17, 2026 (UTC).**

SourceCheck helps investigate a practical question: **do the source records attached to one OpenAlex work describe the same research?** Its automatic rules flag title disagreements; creator names and typed relationships provide context for a reviewer. It produces a review packet with original responses and the evidence needed to investigate. It does not decide publication identity or change OpenAlex.

This project started with a real public record, not an injected error. The earlier Repair Desk's synthetic replay scenarios are not evidence for the findings below.

## 1. The problem in plain language

Think of OpenAlex as a library catalogue. Each research paper has a catalogue card listing its title, authors, DOI, and places to read it. A DOI is like a permanent barcode for a research object: it lets us look up which publication the identifier belongs to.

We found a card with **paper A's DOI and authors, paper B's title, and links to a third publication family**. A person or research agent trusting that combination could produce a citation that does not describe one coherent paper.

We followed the links back to the DOI registration records and the publisher. Those checks established the disagreement in the captured case. We also found legitimate version links: three different DOIs really did describe versions of the same publication. That is why counting DOIs or comparing spelling alone cannot settle identity.

Replacing the title would leave the conflicting links attached. The solution we could responsibly build from outside OpenAlex was therefore a **source comparison and evidence-collection tool**: enter a work ID or DOI, fetch its sources, inspect disagreements, and download a packet another engineer can verify. The maintainer still decides whether and how to correct the catalogue.

This is a working investigation aid. We have not established that no similar tool exists, that OpenAlex needs another curation platform, or that this implementation should be adopted in production.

## 2. The verified problem

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

## 3. How this could help OpenAlex

A reader, citation exporter, or agent trusting only the OpenAlex work's primary DOI and title can produce a citation with one paper's DOI and another paper's title. The attached source links can also send a reader to materially different publications. This example demonstrates that risk directly; it does not measure how often it occurs across OpenAlex.

A title-only repair would hide part of the problem. Changing the title to “MizAR 60 for Mizar 50” would leave the unrelated tutoring and hardware-compression locations attached. Citation edges, topics, authorship assignments, and extracted text might also require review, but this investigation has not established which derived fields are affected.

**The safe actionable output is a source-conflict review packet.** A maintainer can use it to inspect source association, decide whether a work split is appropriate, and rebuild affected derived data. This artifact does not make that upstream decision.

| Team task | What SourceCheck provides today | What would need to be demonstrated |
| --- | --- | --- |
| Understand a vague metadata complaint | A work ID, DOI-specific titles, creator context, and direct source links in one view. | Whether this adds information beyond the team's current ticket tooling. |
| Collect evidence for a reproducible report | Bounded public API retrieval, timestamps, raw bodies, hashes, and JSON/Markdown exports. | Whether engineers spend less active time reaching a correct disposition. |
| Avoid a title-only patch to a deeper source conflict | Visibility into differing DOI source titles and legitimate version relationships. | Whether this reduces incomplete corrections in an actual workflow. |
| Keep a useful regression example | A captured case that replays without network access, with explicit limits. | Which internal source-association test should use it after the cause is understood. |

OpenAlex already asks for specific records, fields, proposed corrections, and source evidence. Its documented correction workflow uses agents to verify reports and apply changes, with broader problems escalated for investigation. SourceCheck would supply an inspectable input to that process. It is not a replacement for it. [Existing OpenAlex correction workflow](https://help.openalex.org/access/fixing-errors/).

The direct benefit delivered is automated evidence collection and repeatable comparison. Faster support, fewer incomplete fixes, and more trustworthy downstream citations are **potential outcomes**, not measured results of this project.

## 4. The implemented solution

SourceCheck is a read-only audit tool and evidence viewer. It accepts a work identifier or DOI, obtains the public work record, checks registered DOI metadata, flags title disagreements, and displays creator and relationship context. The stronger conclusion about conflicting publication families in the demonstrated case came from the additional documented investigation, not from title equality alone.

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

## 5. A concrete support-engineer workflow

**Illustrative ticket, real captured record:** “The DOI and authors on W4385245566 point to MizAR, but the title and some source links point to different papers.” This is an example of how the tool could be used; no actual support ticket has been submitted or resolved.

| Step | What the engineer does | What is available now / decision boundary |
| --- | --- | --- |
| 1. Identify the record | Paste `W4385245566` into the website, or use the Python CLI. | Implemented. A saved ID gives the investigation a specific target. |
| 2. Fetch fresh evidence | Select **Check live**. Keep the captured example available for comparison. | Implemented. The tool retrieves public OpenAlex and DOI registry records. A changed result is a new observation; unavailable data is not proof of a defect. |
| 3. Examine the disagreement | Compare the main DOI's registered title and names with the OpenAlex values. Inspect the other DOI sources and explicit version relationships. | Implemented comparison and display. At capture time the main DOI described MizAR, another DOI supplied the displayed tutoring title, and the three Zenodo DOIs formed a version family. The report's nine-ORCID and publisher checks are separate archived-case verification, not automatic live checks. |
| 4. Hand off a review packet | Download **evidence JSON** and the **review packet**. Include the exact record, observed disagreement, source-specific values, and the remaining uncertainty. | Implemented exports. They include timestamps and raw response evidence. The tool does not submit the packet or prescribe a global replacement title. |
| 5. Investigate and correct internally | A maintainer checks harvested records, matching decisions, and any affected derived data; decides whether a split or another correction is warranted; uses the team's existing correction process. | Maintainer action outside this tool. Internal cause, safe correction, and downstream impact have not been established here. |
| 6. Verify and retain a regression | After the maintainer's change reaches the public API, run a fresh check, compare it with the preserved evidence, and test the actual corrected behavior internally. | A manual recheck is supported. Scheduling, before/after diffing, verification of citation edges, and integration into internal regression suites are not implemented. An `aligned` title result alone cannot certify the repair. |

A useful handoff would say: “The captured source claims conflict; please investigate source association before replacing the title.” It would not say: “Automatically split this ID into three,” because the safe identifiers, lineage, and downstream consequences need internal review.

## 6. Challenge the value

### What is established, and what is not

The evidence establishes a concrete public-record conflict at the capture time. The implementation establishes that a small tool can retrieve, compare, preserve, and export those sources. Neither establishes a novel research method, an unmet internal tooling need, a production-ready disambiguation system, or savings for OpenAlex.

The strongest present use is **a focused investigation companion and a reproducible case contribution**. A generic “metadata repair platform” would overstate the implementation. OpenAlex's agents may already gather equivalent evidence; if so, a small case fixture or reusable check may be more useful than another interface. This is an assessment, not knowledge of their private tools.

### Failure modes that matter

| Challenge | Why it matters | Current response / remaining limitation |
| --- | --- | --- |
| Legitimate versions, translations, or changed titles | Related publications can have different titles and receive a review flag even when the association is acceptable. | Show the titles and typed relationships. The tool does not automatically adjudicate versions, translations, or alternate-title equivalence. |
| Same title, wrong authors | An identity error can be invisible to a title-based rule. | Creator-name overlap is descriptive only. `aligned` can coexist with incorrect authorship; it is not an identity certificate. |
| Normalization and subtitle handling | Removing punctuation makes “C++ for Biology” and “C for Biology” compare equal; a separately stored subtitle can cause a harmless disagreement. | These are analytical counterexamples, not observed OpenAlex defects. Inspect original titles and fields before deciding what the flag means. |
| Correlated or incorrect source metadata | Publisher and registry may share one feed, or a registry record can itself be wrong. | Keep source provenance; their agreement is not two independent votes. A reviewer needs context. |
| Incomplete coverage | No DOI, unsupported DOI links, the six-DOI limit, and failed requests leave gaps. | Expose scope and failures. The tool does not scan the entire work graph, verify all publisher pages, or handle every research object. |
| Review work may increase | Title flags can create noise. Capturing many responses can add API latency and storage. | No measured time saving or precision/recall claim. The flag volume needs evaluation against the existing process. |
| Cause remains unknown | Shared `Cites` identifiers are an investigative lead, not evidence of a particular ingestion bug. | No internal merge logs were inspected. A displayed `merge_evidence: false` is this tool's policy, not a production fix or test of OpenAlex's matcher. |

### A small pilot worth running before adoption

**Proposed evaluation only; not performed.** With the team's permission and existing ticket access, select the next 20 eligible DOI-bearing work-metadata tickets. Define eligibility and ten matched pairs using ticket type and apparent complexity before inspecting SourceCheck's outputs. Randomly assign one ticket per pair to the current workflow and the other to the current workflow plus SourceCheck. Balance engineer assignments; no engineer should process the same ticket twice. The baseline includes the team's existing agents and tools, not an artificially slow manual process.

Record active engineer minutes through a defensible disposition, separately record waiting time, count confirmed useful findings absent from the initial ticket, count unhelpful review flags, and check whether another reviewer can reproduce the evidence. An independent reviewer blinded to the method should assess the dispositions against source evidence and any necessary internal context. With only 20 tickets, report individual results, group differences, and uncertainty; do not generalize to the whole support queue.

Continue only if the tool preserves decision quality and either reduces active review effort or provides confirmed additional findings whose value justifies the effort. **If it adds review time without useful new evidence, do not adopt the extra interface.** Keep the verified case, reusable checks, and evidence format if they are independently useful. No effectiveness result or pilot completion is claimed.

## 7. Proof and reproducibility

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

## 8. Scope and limits

- This is an externally verified case and a working audit workflow, not an upstream fix or a claim of affiliation with OpenAlex.
- The case was found during targeted investigation. It is not a random sample and cannot establish an error rate.
- The automatic decision is title-based; creator-name overlap is descriptive context. Matching titles alone do not prove identity, and matching titles with conflicting authors can still return `aligned`. Different titles alone do not prove unrelated works. Version relations, translations, corrected metadata, and incomplete authorship data all matter.
- DOI discovery recognizes raw DOIs and DOI resolver URLs in supported location fields. It does not extract every DOI embedded in arbitrary publisher paths.
- Registry records can be incomplete or incorrect. Missing registry evidence is an inconclusive result, not evidence of source conflict.
- No claim is made about OpenAlex's existing internal quality checks, exact merge implementation, date of introduction, or unseen production data.
- A maintainer must review any proposed split and downstream consequences. No correction was submitted and no upstream record was altered.
- Public metadata and local processing are used. No paid API account, model, database, or hosted compute service is required. The shared site uses Vercel's free Hobby plan.

## 9. Sources

1. [OpenAlex work W4385245566](https://api.openalex.org/works/W4385245566): the observed aggregate record.
2. [DataCite: MizAR 60 for Mizar 50](https://api.datacite.org/dois/10.4230/lipics.itp.2023.19): DOI-specific title, nine creators/ORCIDs, and relations.
3. [Dagstuhl: MizAR 60 for Mizar 50](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITP.2023.19): publisher title and citation metadata.
4. [DataCite: tutoring paper](https://api.datacite.org/dois/10.4230/oasics.icpec.2026.2) and [Dagstuhl publisher page](https://drops.dagstuhl.de/entities/document/10.4230/OASIcs.ICPEC.2026.2): different creators; exact match to OpenAlex's observed title.
5. [DataCite: Zenodo family](https://api.datacite.org/dois/10.5281/zenodo.21230429), [v1](https://api.datacite.org/dois/10.5281/zenodo.21230430), and [v2](https://api.datacite.org/dois/10.5281/zenodo.21230434): hardware-compression title, creator, and explicit version relations.
6. [DataCite: connecting to works](https://support.datacite.org/docs/connecting-to-works) and [contributing citations and references](https://support.datacite.org/docs/contributing-citations-and-references): typed relationship semantics.
7. [OpenAlex: existing correction workflow](https://help.openalex.org/access/fixing-errors/): the current process this external evidence tool could complement.

Implementation, tests, and evidence are in [Shrey Patel's public repository](https://github.com/Shreyp087/OpenAlex). AI assistance was used for research and implementation; claims are grounded in the preserved public evidence and executable checks.
