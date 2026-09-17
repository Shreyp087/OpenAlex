# The Repair Desk

**My research is in this library. I made something small to help keep its records trustworthy.**

An independent OpenAlex application prototype for Shrey Patel: follow a synthetic support case from preserved source evidence through a local pipeline replay, an explicit decision, and a regression test.

The proposal is simple: **every resolved ticket should leave behind a regression test.** OpenAlex already has agent-assisted curation. This is a small engineering replay harness that explores the handoff from a report to a durable check, not a replacement for that workflow.

## Try it in two minutes

For a zero-setup walkthrough, open `web/index.html` in a browser. It is one self-contained file with no CDN, network font request, API key, or external script dependency. The typefaces are embedded in the file. It displays recorded, verified Python outputs and clearly labels that mode. The buttons let a reviewer inspect source/transform/decision evidence and export case bundles, executable regression tests, and illustrative replies.

For live execution, use the local server below. The same interface detects the Python engine and runs each scenario through its API.

Requires **Python 3.9+**. The application uses only the Python standard library; no package installation, API key, or network access is needed for the bundled demonstration.

From this directory:

```sh
python3 -m repairdesk serve --port 8765
```

Open [localhost:8765](http://127.0.0.1:8765). The service binds to loopback. Stop it with `Ctrl-C`.

Then try the executable backend directly:

```sh
python3 -m repairdesk replay --scenario affiliation-drop --output /tmp/repair-desk-replay.json
python3 -m repairdesk evaluate --output /tmp/repair-desk-evaluation.json
python3 -m unittest discover -s tests -v
```

To retain replay state in SQLite:

```sh
python3 -m repairdesk replay --scenario doi-replay --db /tmp/repair-desk.sqlite
```

To rebuild the precomputed casebook data from the same Python engine:

```sh
python3 -m repairdesk build --output data/demo.json
python3 scripts/build_web.py
```

The second command embeds the verified results, CSS, and JavaScript into `web/index.html`. Commit the rebuilt HTML when changing the casebook or interface. No Node build is required. Vercel serves the checked-in `web/` directory using `vercel.json`. The hosted walkthrough displays recorded Python outputs; the Python API runs only through the local server.

To use an exported regression, save the downloaded `test_*.py` in `tests/` and run the same unittest command above.

## Publish on Vercel

The source repository is [Shreyp087/OpenAlex](https://github.com/Shreyp087/OpenAlex).

1. Open [Vercel's new-project page](https://vercel.com/new) and import `Shreyp087/OpenAlex` from GitHub.
2. Keep the Root Directory at the repository root. The checked-in `vercel.json` selects **Other** as the framework, skips installation and building, and serves **web** as the Output Directory.
3. Select **Deploy**. Once connected, pushes to the production branch deploy automatically; other branches receive preview deployments.

No environment variables or API keys are required. The published demo uses the same recorded evidence as the standalone HTML. Download buttons generate files in the browser. Only `web/` is served as static content; the Python engine, tests, source snapshots, and documentation remain available in the GitHub repository.

To deploy from an authenticated Vercel CLI instead, run `vercel --prod` from the repository root. See Vercel's [Git deployment guide](https://vercel.com/docs/git) and [static configuration reference](https://vercel.com/docs/project-configuration/vercel-json).

## Start with four decisions

| Scenario ID | What to inspect | Useful outcome |
| --- | --- | --- |
| `affiliation-drop` | The preserved affiliation versus an injected transform loss | Diagnose the local regression and reproduce its repair. |
| `orcid-conflict` | Fictional conflicting identity evidence | Require review rather than merge people by name. |
| `sparse-metadata` | A legitimate metadata gap | Preserve uncertainty and leave the record unchanged. |
| `doi-replay` | Repeated deliveries with different DOI formatting | Retain stable work identity without a duplicate materialization. |

**All tickets and faults are synthetic.** The seed is a real public snapshot of [W4410234973](https://openalex.org/W4410234973), the paper *IoT-enabled smart waste management: applications, adoption barriers, and mitigation strategies in the Indian scenario*, co-authored by Shrey Patel. The snapshot does not demonstrate a live OpenAlex bug. The artifact never submits a correction to OpenAlex.

## What is inside

| Path | Purpose |
| --- | --- |
| `repairdesk/` | Standard-library Python replay engine, CLI, and local API. |
| `schema.sql` | SQLite evidence and materialization tables. |
| `data/source/` | Public source snapshot and its provenance. |
| `data/demo.json` | Precomputed casebook output from the engine. |
| `web/` | Interactive demonstration. |
| `tests/` | Executable checks for the local engine and its failure boundaries. |
| [docs/Repair-Desk-Brief.pdf](docs/Repair-Desk-Brief.pdf) | One-page application companion with clickable source links. |
| [docs/application-note.md](docs/application-note.md) | Submission note, 90-second demo script, and draft application answers. |
| [docs/engineering-notes.md](docs/engineering-notes.md) | Architecture, evaluation limits, and a proposed route to a larger pipeline. |

## Why this shape

The bronze layer retains delivered payload bytes and a content hash. Silver keeps work identity separate from formatting differences in incoming metadata. The case output makes findings, evidence, and decisions inspectable. A negative control matters as much as a repaired failure: an empty field is not by itself evidence that a record is wrong.

This is a deliberately small local implementation. The bronze/silver/gold terminology describes responsibilities; it does not imply a Databricks deployment. No learned model, production-scale benchmark, or corpus-wide accuracy claim is included. Local counts describe local fixtures. See the engineering notes before interpreting results.

## Sources and authorship

- [Shrey Patel's portfolio](https://shrey-portforlio.netlify.app/)
- [Seed work in OpenAlex](https://openalex.org/W4410234973) and [published paper](https://doi.org/10.1007/s10163-025-02248-x)
- [OpenAlex's existing correction workflow](https://help.openalex.org/access/fixing-errors/)
- [AI curation guide](https://help.openalex.org/access/fixing-errors/ai-curation-guide/)
- [Raw affiliation data and provenance](https://help.openalex.org/data/raw-affiliation-strings/)

Created with AI assistance for Shrey's application. The candidate should run it, review the implementation, and own the choices before submitting. Application answers are drafts, not assertions of unverified experience. The project makes no claim of affiliation with or endorsement by OpenAlex.

Original project code and documentation are available under the [MIT license](LICENSE). OpenAlex source metadata is CC0.

The optional PDF builder, `docs/build_brief.py`, requires `reportlab`; this is an authoring dependency only. The application itself has no third-party dependencies.

## Visual system

The interface is arranged as a repair register: Barlow Condensed display type, IBM Plex Sans for reading, IBM Plex Mono for record fields, and a black/chalk/vermilion palette. Original records, injected faults, and review decisions remain explicitly labelled. Font files and SIL Open Font Licenses are included in `assets/fonts/`; the HTML builder embeds them for offline use.
