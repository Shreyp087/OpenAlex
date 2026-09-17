# SourceCheck validation record

Verified on September 17, 2026. The current artifact audits real public metadata. Legacy synthetic fixture results are not evidence for real OpenAlex defects.

## Completed checks

- The full Python unittest suite passed: **42 tests**, covering SourceCheck, archived-evidence checks, and the retained legacy engine. Tests include malformed inputs, identifier allowlists, bounded retries, redirects, response-size caps, registry fallbacks, missing evidence, alternate titles, creator-context limits, six-DOI coverage, evidence tampering, and a shared citation that must not establish identity.
- `python3 scripts/verify_evidence.py` verified **89 captured HTTP receipts**, recomputed the 30-record cohort as 25 title agreements and five disagreements, and replayed the full real conflict through the Python audit with **zero network requests**. The result was `review`, with five registry DOIs and three distinct title groups. Receipt totals include repeated captures of some sources; they are not counts of unique publications.
- `python3 docs/verify_collision_evidence.py` independently verified eight case receipts, seven OpenAlex locations, five DOI locations, three distinct registered titles, all nine MizAR author names and ORCIDs, publisher citation metadata, explicit Zenodo version relations, and the shared typed citation. This ran without network access.
- The five-page evidence PDF was rendered and every page visually reviewed. No clipping or overlap was found. All eight full SHA-256 values were extracted from the PDF and verified; all eight receipt URLs are clickable. There are 13 actionable links in the report.
- Live Python audit execution was verified against the real public work. Its result is point-in-time evidence; public records can change.

The first full-suite attempt in a restricted shell could not bind a localhost socket for the legacy HTTP integration class. Re-running with loopback access passed all 42 tests. This was an environment restriction, not a failing audit assertion.

## Final browser and deployment checks

- The final browser verifier passes **336 assertions**, validates 89 receipt hashes, matches 77 API-response parses against Python, and checks 28 Unicode/HTML edge cases. It reproduces the full 11-response audit, tests transport failures and response caps, and verifies all three captured cases and six export callbacks. Every exported raw body is checked against its SHA-256. Malicious HTML/Markdown is escaped and generated shell commands quote identifiers safely.
- Actual browser checks on localhost verified the conflict and aligned control against the live APIs: 11 and two response receipts respectively. Both results were explicitly labelled live and showed fresh timestamps. All three captured cases render and retain their original timestamps and scope.
- Desktop and 390px mobile layouts were visually inspected. At 390px, document width equals viewport width; no horizontal overflow was present. Browser console checks returned no errors or warnings.
- The downloadable evidence ZIP was extracted into a clean temporary directory and its offline verifier passed, independently of the working repository.
- Production deployment verification is recorded after publication; no earlier prototype deployment is treated as proof for SourceCheck.

## Reproduction

From the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/verify_evidence.py
python3 docs/verify_collision_evidence.py
python3 scripts/build_web.py
node scripts/verify_sourcecheck_web.mjs
```

Live audit:

```sh
python3 -m sourcecheck audit W4385245566 \
  --output /tmp/sourcecheck-report.json \
  --evidence-dir /tmp/sourcecheck-evidence
```

Python 3.9+ is sufficient for the CLI and offline evidence checks. Node is only needed for the browser-code verification. The optional PDF builder uses ReportLab. The full suite includes localhost tests and therefore needs permission to bind a loopback socket.

## Interpretation

Automated tests establish behavior for specified cases and failure conditions; they do not measure production throughput or corpus-wide accuracy. The cohort was selected after a problem was found in that volume. Its five title disagreements are review candidates, not five adjudicated merge errors or a precision/recall estimate. Eleven ordered creator-name lists differ, but formatting differences make that unsuitable as an author-error count.

The tool makes no upstream edits. A `review` result identifies a source disagreement; an `aligned` result covers only the checked fields and sources. Registry failures, absent fields, and the six-DOI cap can leave an audit incomplete. Root cause and any upstream split require OpenAlex's internal context.

The earlier synthetic prototype remains in `web/archive/prototype.html`, with its separate engine and verification script. Its old 28-case fixture evaluation is intentionally excluded from SourceCheck's real-evidence claims.
