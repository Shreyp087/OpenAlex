"""Rebuild the one-page PDF. Optional authoring dependency: reportlab."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent
FONTS = ROOT.parent / 'assets' / 'fonts'
for name, filename in [('Display', 'barlow-condensed-700.ttf'),
                       ('Sans', 'ibm-plex-sans-400.ttf'),
                       ('SansBold', 'ibm-plex-sans-600.ttf'),
                       ('Mono', 'ibm-plex-mono-400.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONTS / filename)))

W, H = 612, 792
C = canvas.Canvas(str(ROOT / 'Repair-Desk-Brief.pdf'), pagesize=(W, H))
C.setTitle('The Repair Desk | Shrey Patel | OpenAlex application prototype')
C.setAuthor('Shrey Patel; created with AI assistance')
C.setSubject('An independent local replay harness: one report, one evidence trail, one regression.')
BG = HexColor('#F4F3ED')
INK = HexColor('#171715')
GRAY = HexColor('#565651')
RED = HexColor('#E84427')
LINE = HexColor('#BBBAB3')
WHITE = HexColor('#FFFFFF')

def rect(x,y,w,h,color):
    C.setFillColor(color); C.rect(x,y,w,h,fill=1,stroke=0)

def text(s,x,y,size=10,font='Sans',color=INK):
    C.setFillColor(color); C.setFont(font,size); C.drawString(x,y,s)

def lines(s,x,y,width,size=10,leading=14,font='Sans',color=INK):
    words=s.split(); row=''
    for word in words:
        trial=(row+' '+word).strip()
        if pdfmetrics.stringWidth(trial,font,size)>width and row:
            text(row,x,y,size,font,color); y-=leading; row=word
        else: row=trial
    if row: text(row,x,y,size,font,color); y-=leading
    return y

def rule(y,color=INK,width=.6,x1=36,x2=576):
    C.setStrokeColor(color); C.setLineWidth(width); C.line(x1,y,x2,y)

def link(label,url,x,y,size=8):
    text(label,x,y,size,'Mono')
    width=pdfmetrics.stringWidth(label,'Mono',size)
    C.linkURL(url,(x,y-4,x+width,y+size+4),relative=0,thickness=0)
    C.setStrokeColor(INK); C.setLineWidth(.45); C.line(x,y-3,x+width,y-3)

rect(0,0,W,H,BG)
rect(0,0,9,H,RED)
text('SHREY PATEL / OPENALEX',36,760,8,'Mono')
text('APPLICATION EDITION / 09.2026',376,760,8,'Mono')
rule(748,INK,1.2)

text('REPAIR',30,634,137,'Display')
text('DESK',30,530,137,'Display')
rect(344,543,16,16,RED)

text('FILE 001',406,719,8,'Mono',RED)
text('MY RESEARCH',404,687,27,'Display')
text('IS IN THIS',404,657,27,'Display')
text('LIBRARY.',404,627,27,'Display')
lines('A small tool for keeping its records trustworthy.',406,601,170,10.3,14,'SansBold')
lines('Public source. Synthetic faults. Inspectable decisions.',406,563,166,9.2,13,'Sans',GRAY)

rect(36,482,540,32,RED)
text('Every resolved ticket should leave behind a regression test.',48,493,11,'SansBold',WHITE)

text('01 PRESERVE  /  02 REPLAY  /  03 DECIDE  /  04 EXPLAIN',36,459,8.2,'Mono')
rule(446,INK,1.2)
text('CASE',36,431,7.5,'Mono',GRAY)
text('THE EVIDENCE QUESTION',75,431,7.5,'Mono',GRAY)
text('DISPOSITION',477,431,7.5,'Mono',GRAY)

rows=[
 ('01','REPAIR','Dropped affiliation','Compare the injected transform loss with preserved source evidence.'),
 ('02','ESCALATE','Conflicting ORCIDs','Conflicting identifiers require review before any reassignment.'),
 ('03','LEAVE ALONE','Sparse metadata','Missing source evidence is a limit, not an invitation to invent it.'),
 ('04','DEDUPLICATE','Repeated delivery','Repeat deliveries of the same work ID should not create duplicates.'),
]
for i,(n,badge,title,body) in enumerate(rows):
    y=407-i*45
    text(n,36,y,10,'Mono',RED)
    text(title,75,y,11,'SansBold')
    text(badge,477,y+1,7.3,'Mono')
    text(body,75,y-15,9.1,'Sans',GRAY)
    rule(y-25,LINE,.5)

text('SOURCE / W4410234973',36,229,8,'Mono',RED)
lines('The seed is a paper I co-authored on IoT-enabled smart waste management. Its live record is not alleged to be broken: every demonstrated fault is injected locally.',36,211,250,9.3,12.5)

text('BOUNDARY / LOCAL PROTOTYPE',322,229,8,'Mono',RED)
lines('Python + SQLite. Immutable inputs and repeatable checks. No production-scale claim, no trained model, no writes to OpenAlex. Built with AI assistance.',322,211,254,9.3,12.5)

rect(36,102,540,42,INK)
text('RUN THE REPLAY',47,128,7.3,'Mono',WHITE)
text('python3 -m repairdesk serve --port 8765',47,112,10.1,'Mono',WHITE)

link('SOURCE CODE', 'https://github.com/Shreyp087/OpenAlex',36,78)
link('PORTFOLIO', 'https://shrey-portforlio.netlify.app/',174,78)
link('OPENALEX RECORD', 'https://openalex.org/W4410234973',294,78)
link('PUBLISHED PAPER', 'https://doi.org/10.1007/s10163-025-02248-x',456,78)
rule(62,INK,.6)
text('INDEPENDENT PROTOTYPE / COMPANION TO EXISTING OPENALEX CURATION',36,46,7,'Mono')
text('Sources and limits: docs/engineering-notes.md',36,32,7.5,'Sans',GRAY)
C.showPage(); C.save()
print(ROOT / 'Repair-Desk-Brief.pdf')
