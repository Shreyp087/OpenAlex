"""Build the five-page evidence report. Optional authoring dependency: reportlab."""
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from verify_collision_evidence import verify

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EVIDENCE = ROOT / "data/evidence/source-collision"
MANIFEST = json.loads((EVIDENCE / "manifest.json").read_text())
SUMMARY = json.loads((ROOT / "data/evidence/title-divergence/summary.json").read_text())
FACTS = verify()
assert SUMMARY["counts"]["comparable"] == 30
assert SUMMARY["counts"]["title_agreements"] == 25
assert SUMMARY["counts"]["title_disagreements"] == 5

for name, filename in [("Display", "barlow-condensed-700.ttf"), ("Sans", "ibm-plex-sans-400.ttf"), ("SansBold", "ibm-plex-sans-600.ttf"), ("Mono", "ibm-plex-mono-400.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(ROOT / "assets/fonts" / filename)))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="SansBold", italic="Sans", boldItalic="SansBold")

W, H = 612, 792
BG, INK, RED, GRAY, LINE, WHITE = map(HexColor, ["#F4F3ED", "#171715", "#E84427", "#565651", "#BBBAB3", "#FFFFFF"])
OUT = DOCS / "SourceCheck-Evidence-Report.pdf"
C = canvas.Canvas(str(OUT), pagesize=(W, H), pageCompression=1)
C.setTitle("SourceCheck: one ID, conflicting sources")
C.setAuthor("Shrey Patel; research and implementation assisted by AI")
C.setSubject("A reproducible, read-only OpenAlex source integrity audit with raw public evidence")


def rect(x, y, w, h, color):
    C.setFillColor(color)
    C.rect(x, y, w, h, fill=1, stroke=0)


def txt(text, x, y, size=10, font="Sans", color=INK):
    C.setFillColor(color)
    C.setFont(font, size)
    C.drawString(x, y, text)


def rule(y, x1=36, x2=576, color=INK, thickness=.6):
    C.setStrokeColor(color)
    C.setLineWidth(thickness)
    C.line(x1, y, x2, y)


def para(text, x, top, width=540, size=10.5, leading=15, color=INK, font="Sans", gap=9):
    style = ParagraphStyle("body", fontName=font, fontSize=size, leading=leading, textColor=color)
    p = Paragraph(text, style)
    _, height = p.wrap(width, H)
    assert top - height > 56, (text[:55], top, height)
    p.drawOn(C, x, top - height)
    return top - height - gap


def section(label, y):
    txt(label, 36, y, 8.1, "Mono", RED)
    return y - 17


def link(label, url, x, y, size=8.4, color=INK):
    txt(label, x, y, size, "Mono", color)
    width = pdfmetrics.stringWidth(label, "Mono", size)
    C.linkURL(url, (x, y - 3, x + width, y + size + 2), relative=0, thickness=0)
    C.setStrokeColor(color)
    C.setLineWidth(.35)
    C.line(x, y - 2, x + width, y - 2)


def page(n, label):
    rect(0, 0, W, H, BG)
    rect(0, 0, 7, H, RED)
    txt("SOURCECHECK / THE REPAIR DESK", 36, 758, 8.2, "Mono")
    txt(label, 380, 758, 8.2, "Mono", RED)
    rule(747, thickness=1.2)
    rule(49)
    txt("SHREY PATEL / OPENALEX APPLICATION / 17 SEPT 2026", 36, 32, 7.1, "Mono", GRAY)
    txt(f"{n:02d} / 05", 537, 32, 7.1, "Mono", GRAY)


# 01: Lead with a real, reviewable finding.
page(1, "EVIDENCE REPORT")
txt("ONE ID.", 30, 655, 90, "Display")
txt("CONFLICTING", 30, 575, 90, "Display")
txt("SOURCES", 30, 495, 90, "Display")
rect(388, 500, 11, 11, RED)
txt("W4385245566", 36, 469, 11, "Mono", RED)
para("A real public work record combines the DOI and authors of one paper, the title of another, and locations for a third publication family.", 36, 445, 516, 13.5, 19)
rule(383, thickness=1.2)
txt("OBSERVED OPENALEX TITLE", 36, 365, 8, "Mono", GRAY)
para("Exploiting Generative AI to Scale up Intelligent Tutoring Systems", 36, 350, 520, 17, 21, font="SansBold")
txt("TITLE REGISTERED FOR ITS PRIMARY DOI", 36, 290, 8, "Mono", RED)
txt("MizAR 60 for Mizar 50", 36, 262, 22, "SansBold")
txt("10.4230/lipics.itp.2023.19", 36, 240, 10, "Mono")
rect(36, 153, 540, 65, INK)
for x, number, label in [(49, "5", "DOI LOCATIONS"), (219, "3", "TITLE FAMILIES"), (399, "9/9", "AUTHOR ORCIDS MATCH")]:
    txt(number, x, 180, 30, "Display", WHITE)
    txt(label, x, 163, 7.5, "Mono", WHITE)
para("<b>What is built:</b> a free, read-only source audit that exposes conflicts and exports the evidence needed to review them. Detection and evidence assembly are implemented; no upstream correction is claimed.", 36, 136, 540, 10, 14)
link("LIVE TOOL", "https://openalex-repair-desk.vercel.app/", 36, 65)
link("SOURCE + EVIDENCE", "https://github.com/Shreyp087/OpenAlex", 202, 65)
C.showPage()

# 02: Show why this is more than a title typo, and preserve real versions.
page(2, "01 / SOURCE LEDGER")
txt("THREE FAMILIES, ONE RECORD", 36, 704, 35, "Display")
para("Every DOI below is present in the captured OpenAlex locations. Titles and creators come from each DOI's DataCite record. The two Dagstuhl publisher pages corroborate their own DOI, title, and creator metadata.", 36, 680, 540, 10.5, 15)

y = 610
for label, title, doistr, names, detail in [
    ("A / 2023", "MizAR 60 for Mizar 50", "10.4230/lipics.itp.2023.19", "Jan Jakubův + 8 coauthors", "Primary DOI. All nine OpenAlex author names and all nine ORCIDs match this family."),
    ("B / 2026", "Exploiting Generative AI to Scale up Intelligent Tutoring Systems", "10.4230/oasics.icpec.2026.2", "Miguel Ferreira; José Paulo Leal", "This title exactly matches OpenAlex's observed title. No creator ORCID overlaps family A."),
    ("C / 2026", "Inline Hardware KV-Cache Compression for Long-Context Transformer Inference: An Architectural Case for a Memory-Path Compression Engine", "10.5281/zenodo.21230429 / .21230430 / .21230434", "Alexander Novickis", "Three DOI records with explicit HasVersion / IsVersionOf relations. No creator ORCID overlaps A or B."),
]:
    rule(y, thickness=1)
    txt(label, 36, y - 20, 9, "Mono", RED)
    yy = para(escape(title), 132, y - 10, 444, 13, 17, font="SansBold", gap=7)
    txt(doistr, 132, yy - 7, 8, "Mono")
    yy = para(escape(names), 132, yy - 19, 444, 10, 14, font="SansBold", gap=4)
    yy = para(detail, 132, yy, 444, 10, 14, color=GRAY)
    y = yy - 11

y = section("MULTIPLE DOIS ARE NOT AUTOMATICALLY AN ERROR", y - 3)
y = para("The Zenodo links are a useful control: explicit version relations explain why its three DOI records belong to a family. They do not link that family to either Dagstuhl paper. Titles and author sets reinforce the distinction, but the family split remains a review proposal.", 36, y, 540, 10.5, 15)
y = section("WHY A TITLE-ONLY PATCH IS INSUFFICIENT", y - 3)
para("Overwriting the title would leave unrelated locations attached. A maintainer must examine the source associations and any affected citations, topics, or extracted text. This investigation has not established which downstream fields need rebuilding.", 36, y, 540, 10.5, 15)
C.showPage()

# 03: Explain actual product behavior and the point of conservative decisions.
page(3, "02 / THE SOLUTION")
txt("MAKE THE CONFLICT REVIEWABLE", 36, 704, 35, "Display")
y = para("SourceCheck accepts a DOI or OpenAlex work ID. The Python CLI runs locally; the shared site performs live checks in the browser. Both preserve a clear boundary between source disagreement and a decision to edit a scholarly record.", 36, 680, 540, 11, 16)

steps = [
    ("01", "CAPTURE", "Fetch the OpenAlex work and at most six selected, canonical, or location DOI records. Query Crossref first; fall back to DataCite after a Crossref 404."),
    ("02", "COMPARE", "Compare registered titles and creator context per DOI. Keep typed relationships visible. A citation, reference, or container link is not an identity claim."),
    ("03", "CLASSIFY", "Return aligned, review, or inconclusive. An aligned result covers the checked evidence only. Missing sources, failed requests, and truncated coverage are limitations."),
    ("04", "EXPORT", "Produce a read-only review packet with source claims and HTTP evidence. It gives a maintainer a reproducible starting point without guessing a global replacement title."),
]
for n, title, body in steps:
    rule(y - 2, color=LINE)
    txt(n, 36, y - 24, 21, "Display", RED)
    txt(title, 78, y - 20, 10, "SansBold")
    y = para(body, 78, y - 29, 498, 10.2, 14.5, gap=15)

rule(y, thickness=1.2)
y = section("A LEAD TO INVESTIGATE, NOT A PROVEN ROOT CAUSE", y - 23)
y = para("All five DOI records contain a <b>Cites</b> relation to <b>arXiv:1706.03762</b>. One hypothesis is that a cited identifier was treated as an identity signal during ingestion or merging. A shared citation alone does not prove that happened.", 36, y, 540, 10.5, 15)
y = para("The invariant is still clear: a Cites edge must not, on its own, equate works. DataCite distinguishes citation relationships from identity and version relationships. Internal production logs are needed to establish the cause.", 36, y, 540, 10.5, 15)
link("DATACITE RELATIONSHIP SEMANTICS", "https://support.datacite.org/docs/connecting-to-works", 36, y - 3, 8)
C.showPage()

# 04: A measured cohort, honest denominator, executable reproduction.
page(4, "03 / REPRODUCTION")
txt("30 RECORDS. FIVE DISAGREEMENTS.", 36, 704, 33, "Display")
para("A targeted check of ITP 2023 DOI suffixes 1-30 found 25 normalized-title agreements and five disagreements. All 60 singleton responses ultimately returned HTTP 200; five transient failures were retried once and logged.", 36, 680, 540, 10.5, 15)
rect(36, 584, 450, 29, INK)
rect(486, 584, 90, 29, RED)
txt("25 AGREE", 48, 594, 9, "Mono", WHITE)
txt("5 DIFFER", 494, 594, 9, "Mono", WHITE)
txt("DOI SUFFIXES WITH TITLE DIFFERENCES: 13 / 17 / 18 / 19 / 26", 36, 565, 8.2, "Mono")
y = para("Selection followed discovery of the problem in this volume. It is a contiguous subset of 38 numbered contributions, not a random sample. <b>These counts are not an OpenAlex-wide error rate or a precision/recall evaluation.</b> They identify five review candidates, not five adjudicated merge failures.", 36, 546, 540, 10.5, 15)
y = para("Comparison used Unicode NFKC, case folding, and punctuation/whitespace normalization. Eleven creator-name lists also differed, but name formats can explain that; they are not counted as author errors. The cohort archive contains 70 raw receipts, including discovery and control checks.", 36, y, 540, 10.2, 14.5)
y = section("RUN THE LIVE AUDIT / PYTHON STANDARD LIBRARY", y - 9)
rect(36, y - 67, 540, 70, INK)
for k, line in enumerate([
    "python3 -m sourcecheck audit W4385245566 \\",
    "  --output /tmp/sourcecheck-report.json \\",
    "  --evidence-dir /tmp/sourcecheck-evidence",
]):
    txt(line, 48, y - 15 - k * 17, 9.1, "Mono", WHITE)
y = y - 91
y = section("REPLAY THE ARCHIVED EVIDENCE / NO NETWORK", y)
txt("python3 scripts/verify_evidence.py", 36, y - 3, 9.6, "Mono")
txt("python3 docs/verify_collision_evidence.py", 36, y - 23, 9.6, "Mono")
y = para("The case verifier checks all eight receipt hashes and byte lengths, the publisher metadata, the five DOI locations, nine matching author ORCIDs, and the typed version/citation relations. The full verifier checks the archived cases and cohort calculations.", 36, y - 43, 540, 10.2, 14.5)
y = para("A later live response may differ because the public record has been corrected. Preserve the new receipt and report the change; do not force the live result to match this captured case.", 36, y, 540, 10.2, 14.5)
link("COHORT + DISCOVERY LOG", "https://github.com/Shreyp087/OpenAlex/blob/main/docs/evidence-research.md", 36, y - 3, 8.2)
C.showPage()

# 05: The exact receipts; complete hashes remain copyable and links actionable.
page(5, "04 / RECEIPTS + LIMITS")
txt("PROOF YOU CAN INSPECT", 36, 704, 36, "Display")
para("Eight original response bodies independently captured on 17 September 2026, 17:22:15-17:22:17 UTC. All returned HTTP 200. Click a filename to inspect its live source. The repository manifest retains exact timestamps, URLs, status, byte counts, and hashes.", 36, 680, 540, 10.2, 14.5)
y = 609
for item in MANIFEST["responses"]:
    rule(y, color=LINE)
    link(item["file"], item["url"], 36, y - 18, 8.1)
    txt(f'{item["bytes"]:,} bytes', 486, y - 18, 8, "Mono", GRAY)
    txt(item["sha256"], 36, y - 34, 7.7, "Mono", GRAY)
    y -= 48

y = section("WHAT THIS EVIDENCE DOES - AND DOES NOT - ESTABLISH", y - 7)
y = para("The captured work contains conflicting bibliographic identities. Registry and publisher agree on their DOI-specific claims, but may share the same metadata feed. Hashes verify captured bytes, not source truth. The exact internal cause, affected downstream fields, and appropriate upstream split require maintainer investigation.", 36, y, 540, 10.2, 14.5)
y = para("No OpenAlex data was edited and no ticket was submitted. This is an independent application artifact, built with AI assistance. Public metadata, local Python, and free Vercel Hobby hosting are sufficient; no paid model or service is required.", 36, y, 540, 10.2, 14.5)
link("FULL TECHNICAL DOCUMENTATION", "https://github.com/Shreyp087/OpenAlex/blob/main/docs/REAL-PROBLEM.md", 36, y - 3, 8)
C.showPage()
C.save()
print(OUT)
