# SourceCheck

**One OpenAlex ID. Conflicting sources. An evidence trail you can inspect.**

SourceCheck is a working, read-only audit tool built for Shrey Patel's OpenAlex application. It collects DOI-source metadata, flags title disagreements, displays creator and relationship context, and exports a review packet with captured HTTP evidence. It does not automatically decide publication identity.

[Try the live tool](https://openalex-repair-desk.vercel.app/) · [Read the evidence report](docs/SourceCheck-Evidence-Report.pdf) · [Full documentation](docs/REAL-PROBLEM.md) · [Source repository](https://github.com/Shreyp087/OpenAlex)

## The real problem

On September 17, 2026, [OpenAlex W4385245566](https://api.openalex.org/works/W4385245566) returned the primary DOI `10.4230/lipics.itp.2023.19` with the title **Exploiting Generative AI to Scale up Intelligent Tutoring Systems**. For that DOI, [DataCite](https://api.datacite.org/dois/10.4230/lipics.itp.2023.19) and [the publisher](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITP.2023.19) instead identify **MizAR 60 for Mizar 50**.

The record's nine author names and nine ORCIDs match the MizAR paper. Its five DOI locations describe three distinct title/author families, including legitimate Zenodo versions within one family. The observed OpenAlex title matches a different attached DOI's publication. A title-only overwrite would leave the source conflict unresolved.

This is preserved public data, not an injected fault. SourceCheck solves the detection and evidence-assembly step; it does **not** claim to have repaired OpenAlex, established the internal cause, or safely split the upstream work.

A follow-up check of the first 30 numbered DOI suffixes from ITP 2023 found **25 normalized-title agreements and five disagreements**. This was a targeted cohort chosen after discovery, not a random sample or an estimate of OpenAlex's error rate. Details, original responses, and limits are in [the technical documentation](docs/REAL-PROBLEM.md).

In plain language: the catalogue card mixes the barcode and authors of one paper with the title of another. SourceCheck helps an engineer follow those claims back to their sources before deciding how to correct the record.

## Where it fits, and where it may not

An engineer can paste the ID, run **Check live**, review the source-specific titles and creator context, and export the evidence. Internal investigation, deciding a safe correction, applying it, and checking downstream effects remain maintainer work. [Walk through the concrete support workflow](docs/REAL-PROBLEM.md#5-a-concrete-support-engineer-workflow).

OpenAlex already has an [agent-assisted correction process](https://help.openalex.org/access/fixing-errors/). This tool could contribute repeatable evidence collection; it has not established that an equivalent capability is missing or that another interface saves time. Legitimate versions can cause review flags, and same-title/wrong-author records can pass the automatic title check. The [critical assessment and proposed pilot](docs/REAL-PROBLEM.md#6-challenge-the-value) describe how to evaluate incremental usefulness, including when not to adopt it. No pilot has been run.

## Use it

Open [the site](https://openalex-repair-desk.vercel.app/) to inspect the captured case, enter an OpenAlex work ID or DOI, and explicitly run a live check. The browser reads the public OpenAlex, Crossref, and DataCite APIs directly. Report and evidence downloads are generated locally in the browser.

The Python CLI requires **Python 3.9+** and only the standard library:

```sh
python3 -m sourcecheck audit W4385245566 \
  --output /tmp/sourcecheck-report.json \
  --evidence-dir /tmp/sourcecheck-evidence
```

A raw DOI such as `10.4230/lipics.itp.2023.19` can replace the work ID. Supported identifier URLs are validated rather than fetched as arbitrary addresses. The CLI writes a JSON report and original response receipts, not changes to OpenAlex.

No paid service, API account, model, database, or backend hosting is required. The site is statically hosted on Vercel's free Hobby plan. A live audit still depends on the public APIs being reachable and within their free access limits; failed or incomplete checks are surfaced.

## Decisions and boundaries

| Outcome | Meaning |
| --- | --- |
| `aligned` | The primary title equals a registry main title, with no title conflict among the checked sources. This does not certify authorship or the entire work. |
| `review` | The sources contain a disagreement requiring investigation. The evidence identifies what differed. |
| `inconclusive` | There is insufficient usable evidence for a complete comparison. |

An audit checks at most six selected, canonical, or location DOI records. It queries Crossref first and uses DataCite after a Crossref 404. Registry failures and skipped sources remain visible. Titles and creator context are compared; alternate titles and typed relations are preserved. `Cites` relationships never establish identity. Different titles are review signals, not an instruction to merge or split records automatically.

DataCite and publisher metadata can share the same upstream feed. Their agreement is corroboration, not an independent two-vote truth score. Public records can change after capture; a subsequent correction should be reported as a new observation.

## Reproduce the evidence and tests

These commands run locally from the repository root:

```sh
# Recompute the archived case and cohort; network disabled.
python3 scripts/verify_evidence.py

# Independently verify eight case receipts and source-identity facts.
python3 docs/verify_collision_evidence.py

# Python tests, including evidence tampering and negative controls.
python3 -m unittest discover -s tests -v

# Build the static site, then verify the browser implementation.
python3 scripts/build_web.py
node scripts/verify_sourcecheck_web.mjs
```

The [GitHub Actions workflow](https://github.com/Shreyp087/OpenAlex/actions/workflows/verify.yml) runs the same checks on pushes and pull requests using a standard runner in this public repository. It requests read-only repository access, uploads no artifacts, and uses no cache or paid service.

Node is needed only for the optional browser-code verification. The full Python suite also includes legacy localhost HTTP tests; those need permission to bind a loopback socket in restricted environments. [The validation record](docs/validation.md) distinguishes automated checks from actual browser inspection.

The cohort counts are comparisons against DOI-registration metadata, not adjudicated error labels or detector precision/recall. Unit tests exercise deliberately constructed boundary conditions; those fixtures are not presented as real OpenAlex defects.

## Project map

| Path | Purpose |
| --- | --- |
| `sourcecheck/` | Standard-library Python audit implementation and CLI. |
| `data/evidence/` | Captured public responses, manifests, and cohort comparisons. |
| `web/sourcecheck.template.html` | Main site structure. |
| `web/sourcecheck-core.js` | Browser audit logic. |
| `web/sourcecheck-ui.js` | Evidence viewer and live-check interface. |
| `web/sourcecheck.css` | Black/chalk/vermilion visual system. |
| `scripts/build_web.py` | Build the checked-in static site. |
| `scripts/verify_evidence.py` | Verify hashes and recompute captured evidence without network access. |
| `tests/test_sourcecheck.py` | Audit behavior, transport, and conservative decision checks. |
| `tests/test_evidence.py` | Tamper detection and offline evidence verification. |
| [docs/REAL-PROBLEM.md](docs/REAL-PROBLEM.md) | Problem, solution, proof, reproduction, and limits. |
| [docs/SourceCheck-Evidence-Report.pdf](docs/SourceCheck-Evidence-Report.pdf) | Eight-page companion: plain explanation, evidence, workflow, critical assessment, and reproduction. |
| [docs/application-note.md](docs/application-note.md) | Submission note and draft application answers. |
| [docs/evidence-research.md](docs/evidence-research.md) | Discovery and sampling log, including a reported issue that no longer reproduced. |

## Hosting and authoring

The repository is connected to [the Vercel site](https://openalex-repair-desk.vercel.app/). `vercel.json` serves the checked-in `web/` directory as static files, with no install or build step. Rebuild and commit the generated HTML when changing the site. No environment variables or API keys are needed.

To preview locally:

```sh
python3 -m http.server 8765 --directory web --bind 127.0.0.1
```

Open [localhost:8765](http://127.0.0.1:8765/). This serves files; the live check still calls the public APIs from the browser.

The optional PDF authoring command requires the open-source `reportlab` package:

```sh
python3 docs/build_sourcecheck_report.py
```

ReportLab is not an application runtime dependency. Barlow Condensed, IBM Plex Sans, and IBM Plex Mono are included with their SIL Open Font Licenses in `assets/fonts/`. The interface uses a ruled research register layout.

## Earlier prototype and attribution

The earlier four-case synthetic replay remains at [web/archive/prototype.html](web/archive/prototype.html). Its Python code is in `repairdesk/`, with `scripts/build_legacy.py` preserving the prior build. It is a clearly labeled historical prototype and is not evidence for SourceCheck's real findings.

Built with AI assistance for Shrey Patel's application. Shrey's [portfolio](https://shrey-portforlio.netlify.app/) and [co-authored paper](https://doi.org/10.1007/s10163-025-02248-x) provide personal context; the real conflict investigated here concerns a different paper. This project is independent and does not imply OpenAlex endorsement. Application answers are drafts to review and own before submission.

Original code and documentation use the [MIT license](LICENSE). Source metadata and publisher pages retain their applicable terms and attribution, with retrieval URLs preserved in the manifests.
