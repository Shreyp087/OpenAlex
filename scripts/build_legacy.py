"""Build a self-contained, offline HTML artifact from verified Python output."""
import json
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / 'data/demo.json').read_text())
assert data['evaluation']['all_passed'], 'Do not publish a demo with failing checks'
serialized = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
# Source text is untrusted metadata: keep it inside the inert JSON script element.
serialized = serialized.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
html = (ROOT / 'web/index.template.html').read_text()
font_rules = []
for font in json.loads((ROOT / 'assets/fonts/manifest.json').read_text()):
    font_path = ROOT / 'assets/fonts' / font['file']
    compact = font_path.with_suffix('.woff2')
    font_path = compact if compact.exists() else font_path
    font_format = 'woff2' if font_path.suffix == '.woff2' else 'truetype'
    mime = 'font/woff2' if font_path.suffix == '.woff2' else 'font/ttf'
    encoded = base64.b64encode(font_path.read_bytes()).decode()
    font_rules.append("@font-face{font-family:'%s';font-style:normal;font-weight:%s;font-display:swap;src:url(data:%s;base64,%s) format('%s');}" %
                      (font['family'], font['weight'], mime, encoded, font_format))
font_licenses = '\n'.join('/* ' + p.name + '\n' + p.read_text().replace('*/', '* /') + '\n*/'
                          for p in sorted((ROOT / 'assets/fonts').glob('*OFL.txt')))
html = html.replace('/*__FONTS__*/', '\n'.join(font_rules) + '\n' + font_licenses)
html = html.replace('/*__BRIEF__*/', base64.b64encode((ROOT / 'docs/Repair-Desk-Brief.pdf').read_bytes()).decode())
html = html.replace('/*__STYLE__*/', (ROOT / 'web/styles.css').read_text())
html = html.replace('/*__DATA__*/', serialized)
html = html.replace('/*__APP__*/', (ROOT / 'web/app.js').read_text())
assert '/*__' not in html
(ROOT / 'web/archive/prototype.html').write_text(html)
print('Built web/index.html: {:,} bytes, {} scenarios, {}/{} evaluation checks'.format(
    len(html.encode()), len(data['scenarios']), data['evaluation']['passed'], data['evaluation']['total']))
