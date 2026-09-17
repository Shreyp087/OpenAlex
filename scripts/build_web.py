"""Build the live SourceCheck website and its reproducible evidence downloads."""
import base64
import hashlib
import html.entities
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sourcecheck.audit import _extract_work, parse_registry


def read_json(path):
    return json.loads(path.read_text())


def embed_receipt(receipt, folder):
    item = dict(receipt)
    body = (folder / receipt['path']).read_bytes()
    assert hashlib.sha256(body).hexdigest() == receipt['sha256']
    assert len(body) == receipt['bytes']
    item['body_base64'] = base64.b64encode(body).decode()
    return item


live = ROOT / 'data/evidence/live-audit'
main_report = read_json(live / 'report.json')
main_report['evidence'] = [embed_receipt(r, live) for r in main_report['evidence']]
main_report['scope']['all_selected_registry_sources_read'] = all(s['status'] == 'found' for s in main_report['registry_sources'])
case_dir = ROOT / 'data/evidence/title-divergence'
manifest = read_json(case_dir / 'manifest.json')
receipts = {r['label']: r for r in manifest['receipts']}


def primary_case(label, provider, doi, note):
    oa, registry = receipts[label + '-openalex'], receipts[label + '-' + provider]
    evidence = []
    for r in (oa, registry):
        converted = {'url': r['url'], 'http_status': r['status'], 'retrieved_at': r['captured_at'],
                     'sha256': r['sha256'], 'bytes': r['bytes'], 'path': r['file'], 'attempt': 1,
                     'truncated': False, 'error_kind': None}
        evidence.append(embed_receipt(converted, case_dir))
    return {'input': doi, 'scope': 'primary', 'note': note,
            'checked_at': max(oa['captured_at'], registry['captured_at']),
            'work': _extract_work(read_json(case_dir / oa['file'])),
            'registries': [parse_registry(provider, doi, read_json(case_dir / registry['file']))],
            'evidence': evidence}


cases = {
    'collision': {'input': 'W4385245566', 'scope': 'full', 'report': main_report,
                  'note': 'Five DOI sources captured from real API responses. Use Check live to fetch them again.'},
    'identity': primary_case('itp18', 'datacite', '10.4230/lipics.itp.2023.18',
                            'Primary DOI comparison only; other location DOIs were not audited in this capture.'),
    'aligned': primary_case('shrey', 'crossref', '10.1007/s10163-025-02248-x',
                           'Shrey’s paper: primary DOI titles agree. This is a control, not a claim that every field is correct.')
}
data = {'cases': cases, 'cohort': read_json(case_dir / 'summary.json')}
(ROOT / 'data/sourcecheck-web.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
# Ship an explicit Unicode case-fold and HTML-entity map, keeping Python and browser text rules inspectable.
casefold = {chr(i): chr(i).casefold() for i in range(sys.maxunicode + 1) if chr(i).casefold() != chr(i).lower()}
normalization = 'const NORMALIZATION = ' + json.dumps({'casefold': casefold, 'entities': html.entities.html5}, ensure_ascii=True, separators=(',', ':')) + ';\n'
(ROOT / 'web/normalization-data.js').write_text(normalization)
font_rules = []
for f in read_json(ROOT / 'assets/fonts/manifest.json'):
    path = ROOT / 'assets/fonts' / f['file']
    encoded = base64.b64encode(path.read_bytes()).decode()
    font_rules.append("@font-face{font-family:'%s';font-style:normal;font-weight:%s;font-display:swap;src:url(data:font/ttf;base64,%s) format('truetype');}" % (f['family'], f['weight'], encoded))
licenses = '\n'.join('/* ' + p.name + '\n' + p.read_text().replace('*/', '* /') + '\n*/' for p in sorted((ROOT / 'assets/fonts').glob('*OFL.txt')))
serialized = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
page = (ROOT / 'web/sourcecheck.template.html').read_text()
for token, replacement in {
    'FONTS': '\n'.join(font_rules) + '\n' + licenses,
    'STYLE': (ROOT / 'web/sourcecheck.css').read_text(),
    'DATA': serialized,
    'NORMALIZATION': normalization,
    'CORE': (ROOT / 'web/sourcecheck-core.js').read_text(),
    'APP': (ROOT / 'web/sourcecheck-ui.js').read_text()
}.items():
    page = page.replace('/*__' + token + '__*/', replacement)
assert '/*__' not in page
(ROOT / 'web/index.html').write_text(page)
downloads = ROOT / 'web/downloads'
downloads.mkdir(exist_ok=True)
shutil.copyfile(ROOT / 'docs/SourceCheck-Evidence-Report.pdf', downloads / 'SourceCheck-Evidence-Report.pdf')
with zipfile.ZipFile(downloads / 'SourceCheck-Evidence.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for path in sorted((ROOT / 'data/evidence').rglob('*')):
        if path.is_file():
            z.write(path, str(path.relative_to(ROOT)))
    for name in ['docs/REAL-PROBLEM.md', 'docs/evidence-research.md', 'scripts/verify_evidence.py',
                 'docs/verify_collision_evidence.py', 'sourcecheck/__init__.py', 'sourcecheck/audit.py',
                 'sourcecheck/__main__.py', 'LICENSE']:
        p = ROOT / name
        if p.exists():
            z.write(p, name)
print('Built SourceCheck: {:,} bytes; {} real captured cases; {} cohort records.'.format(len(page.encode()), len(cases), len(data['cohort']['records'])))
