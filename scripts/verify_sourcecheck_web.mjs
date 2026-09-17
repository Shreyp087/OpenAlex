#!/usr/bin/env node
/* Offline Python/browser parity and failure-boundary checks. No network access. */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash, webcrypto} from 'node:crypto';
import vm from 'node:vm';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const exporter=String.raw`
import hashlib, html.entities, json
from pathlib import Path
from urllib.parse import urlsplit, unquote
from sourcecheck.audit import _extract_work, parse_registry, normalize_title, parse_input, audit, SourceFailure
root=Path.cwd()
records=[]
receipt_count=0
for manifest_path in sorted((root/'data/evidence').rglob('manifest.json')):
    manifest=json.loads(manifest_path.read_text())
    for receipt in manifest.get('receipts',manifest.get('responses',[])):
        body=(manifest_path.parent/receipt['file']).read_bytes()
        assert hashlib.sha256(body).hexdigest()==receipt['sha256'], receipt['file']
        assert len(body)==receipt['bytes'], receipt['file']
        receipt_count+=1
        if receipt.get('http_status',receipt.get('status'))!=200: continue
        try: document=json.loads(body)
        except (ValueError,UnicodeError): continue
        host=urlsplit(receipt['url']).hostname
        if host=='api.openalex.org':
            expected=_extract_work(document);provider='openalex';doi=expected['doi']
            titles=[expected['title']]
        elif host in {'api.crossref.org','api.datacite.org'}:
            provider='crossref' if host=='api.crossref.org' else 'datacite'
            doi=unquote(urlsplit(receipt['url']).path.split('/',2)[2]).lower()
            expected=parse_registry(provider,doi,document)
            titles=expected['main_titles']+expected['alternate_titles']+expected['subtitles']
        else: continue
        records.append({'file':str((manifest_path.parent/receipt['file']).relative_to(root)),
            'provider':provider,'doi':doi,'document':document,'expected':expected,
            'normalizations':[[title,normalize_title(title)] for title in titles]})
edges=['<i>ＭｉｚＡＲ</i>&nbsp;60: for Mizar—50','<p>First</p><p>Second</p>',
 'ÉTUDE &amp; café','cafe\u0301','Straße STRASSE','ΟΣ Σ ς','İ ı I','ﬀ ﬁ Ａ',
 'A < B > C','A < B and C','<span title="a>b">Hello</span> world',
 '&amp;amp;amp;','&nbsp between','&notit;','&#x80; model','&#0; x','&#x1f; y',
 '&#xD800; z','&#x110000; z','<!-- comment -->title','<script>a<b</script>',
 '\ufeffLeading BOM','space\u0085next\u001cend','<i unfinished','A &copy text',
 '<sup>2</sup>-D <sub>x</sub>','<div>x<br/>y</div>','x &unknown; y']
inputs=['W4385245566','w123','10.4230/LIPIcs.ITP.2023.19','https://doi.org/10.4230%2FLIPICS.ITP.2023.19',
 'https://api.openalex.org/works/W123','https://openalex.org/W123','https://dx.doi.org/10.1234/a/../b',
 'https://doi.org/10.1234/a%ZZ','https://evil.example/W123','https://openalex.org.evil/W123',
 'https://evil@openalex.org/W123','https://openalex.org:443/W123','http://openalex.org/W123',
 'https://openalex.org/W123?','https://openalex.org/W123#','https://doi.org/10.1234/a%3Fkey=1',
 'https://doi.org/10.1234/a\u005cb','https://doi.org/10.1234/%0aevil','W123\n',' W123','x'*513]
input_results=[]
for value in inputs:
    try: expected=parse_input(value)
    except ValueError: expected=None
    input_results.append([value,expected])
live=root/'data/evidence/live-audit'
receipts=json.loads((live/'manifest.json').read_text())['receipts']
class CachedClient:
    def __init__(self): self.evidence=[]
    def get_json(self,url):
        receipt=next(r for r in receipts if r['url']==url)
        self.evidence.append(receipt)
        if receipt['http_status']!=200:
            raise SourceFailure('not_found' if receipt['http_status']==404 else 'http_error',
                'Public API returned HTTP {}.'.format(receipt['http_status']),receipt['http_status'])
        return json.loads((live/receipt['file']).read_bytes())
report=audit('W4385245566',live,client=CachedClient())
normalization={'casefold':{chr(i):chr(i).casefold() for i in range(0x110000) if chr(i).casefold()!=chr(i).lower()},'entities':html.entities.html5}
print(json.dumps({'receipt_count':receipt_count,'records':records,'edges':[[x,normalize_title(x)] for x in edges],
 'inputs':input_results,'normalization':normalization,'live_report':report},ensure_ascii=False))
`;
const python=spawnSync(process.env.SOURCECHECK_PYTHON||'python3',['-c',exporter],{cwd:root,encoding:'utf8',maxBuffer:32*1024*1024});
assert.equal(python.status,0,python.stderr);
const fixtures=JSON.parse(python.stdout);
const normalizationContext={};
vm.runInNewContext(readFileSync(resolve(root,'web/normalization-data.js'),'utf8')+'\nglobalThis.TABLE=NORMALIZATION;',normalizationContext);
assert.deepEqual(JSON.parse(JSON.stringify(normalizationContext.TABLE)),fixtures.normalization,'Bundled Unicode/HTML tables must equal the Python export');
const coreCode=readFileSync(resolve(root,'web/sourcecheck-core.js'),'utf8');
function makeCore(fastTimers=false){
  const context={NORMALIZATION:normalizationContext.TABLE,module:{exports:{}},URL,AbortController,
    TextDecoder,TextEncoder,Uint8Array,crypto:webcrypto,btoa:s=>Buffer.from(s,'binary').toString('base64'),
    setTimeout:fastTimers?((fn,ms)=>setTimeout(fn,ms===5000?1:ms===250?0:ms)):setTimeout,clearTimeout,
    fetch:()=>{throw new Error('Network is forbidden in this verifier.');}};
  vm.runInNewContext(coreCode,context,{filename:'sourcecheck-core.js'});
  return context.module.exports;
}
const core=makeCore(),plain=x=>JSON.parse(JSON.stringify(x));
let assertions=0;
function same(actual,expected,message){assert.deepEqual(plain(actual),expected,message);assertions++;}
for(const record of fixtures.records){
  const actual=record.provider==='openalex'?core.extractWork(record.document):core.parseRegistry(record.provider,record.doi,record.document);
  same(actual,record.expected,'Parser parity: '+record.file);
  for(const [title,expected] of record.normalizations)same(core.normalizeTitle(title),expected,'Title parity: '+record.file);
}
for(const [title,expected] of fixtures.edges)same(core.normalizeTitle(title),expected,'Normalization edge: '+JSON.stringify(title));
for(const [title,expected] of [['<i unfinished',''],['<i',''],['Title <span data-x="unfinished','title'],['Title <span data-x="a>b" unfinished','title'],['Title &lt;span unfinished','title'],['x < y and y > 0','x y and y 0'],['x < 3','x 3'],['x <span title="a>b">y</span>','x y']])same(core.normalizeTitle(title),expected,'Version-independent incomplete markup rule');
for(const [input,expected] of fixtures.inputs){
  if(expected===null){assert.throws(()=>core.parseInput(input),undefined,'Reject '+input);assertions++;}
  else same(core.parseInput(input),expected,'Input parity: '+input);
}

const liveDir=resolve(root,'data/evidence/live-audit');
const receipts=JSON.parse(readFileSync(resolve(liveDir,'manifest.json'),'utf8')).receipts;
const calls=[];
const replayFetch=async(url,options)=>{
  calls.push(url);assert.equal(options.credentials,'omit');assert.equal(options.redirect,'error');
  const receipt=receipts.find(r=>r.url===url);assert.ok(receipt,'Only archived URL allowed: '+url);
  return new Response(readFileSync(resolve(liveDir,receipt.file)),{status:receipt.http_status});
};
const live=await core.audit('W4385245566',()=>{},replayFetch);
for(const field of ['schema_version','rule_version','status','summary','input','work','registry','registry_sources','comparison','signals','source_conflicts','scope','policy'])same(live[field],fixtures.live_report[field],'Full live-receipt replay parity: '+field);
assert.equal(calls.length,11);assertions++;
for(const receipt of live.evidence){
  const bytes=Buffer.from(receipt.body_base64,'base64');
  assert.equal(createHash('sha256').update(bytes).digest('hex'),receipt.sha256);
  assert.equal(bytes.length,receipt.bytes);assertions+=2;
}
same(live.status,'review','Observed collision remains review');
same(live.registry_sources.length,5,'Five distinct source DOIs');
same(live.source_conflicts.distinct_normalized_main_titles.length,3,'Three title families');
assert.ok(live.source_conflicts.common_related_identifiers.some(r=>r.relation_type==='Cites'&&r.source_dois.length===5&&!r.merge_evidence));assertions++;

const doi='10.1234/example',oa='https://api.openalex.org/works/W123',cr='https://api.crossref.org/works/'+doi,dc='https://api.datacite.org/dois/'+doi;
const own={id:'https://openalex.org/W123',doi:'https://doi.org/'+doi,title:'A title',authorships:[],locations:[]};
const registry={message:{title:['A title'],author:[]}};
function scriptedFetch(script){
  const seen=[];
  const fetcher=async(url,options)=>{
    seen.push(url);const next=script.shift();assert.ok(next,'Unexpected request '+url);assert.equal(url,next.url);
    assert.equal(options.credentials,'omit');assert.equal(options.redirect,'error');
    if(next.fail)throw new TypeError('Simulated network failure');
    const body=next.body instanceof Uint8Array?next.body:typeof next.body==='string'?next.body:JSON.stringify(next.body);
    return new Response(body,{status:next.status??200,headers:next.headers});
  };
  return {fetcher,seen,done(){assert.equal(script.length,0,'Unused scripted response');}};
}
async function runCase(script,expected,value='W123',engine=core){
  const mock=scriptedFetch(script),report=await engine.audit(value,()=>{},mock.fetcher);mock.done();same(report.status,expected,'Scripted outcome');return {report,mock};
}
await runCase([{url:oa,body:own},{url:cr,body:registry}],'aligned');
await runCase([{url:oa,body:own},{url:cr,body:{message:{title:['Different']}}}],'review');
await runCase([{url:oa,body:{...own,title:null}},{url:cr,body:registry}],'inconclusive');
await runCase([{url:oa,body:{...own,doi:null}}],'inconclusive');
const fallback=await runCase([{url:oa,body:own},{url:cr,status:404,body:'not found'},{url:dc,body:{data:{attributes:{titles:[{title:'A title'}],creators:[]}}}}],'aligned');
same(fallback.report.registry.provider,'datacite','Only 404 triggers DataCite fallback');
same(fallback.report.errors[0].kind,'not_found','404 receipt is distinct');
const throttled=await runCase([{url:oa,body:own},{url:cr,status:429,body:'slow',headers:{'Retry-After':'0'}},{url:cr,status:429,body:'slow'}],'inconclusive');
same(throttled.report.errors.at(-1).kind,'rate_limited','429 remains rate-limit failure, not 404');
assert.ok(!throttled.mock.seen.some(x=>x.includes('datacite')));assertions++;
await runCase([{url:oa,body:own},{url:cr,status:429,body:'slow',headers:{'Retry-After':'60'}}],'inconclusive');
await runCase([{url:oa,body:own},{url:cr,status:403,body:'denied'}],'inconclusive');
await runCase([{url:oa,body:own},{url:cr,status:404,body:'missing'},{url:dc,status:404,body:'missing'}],'inconclusive');
await runCase([{url:oa,body:own},{url:cr,body:'not json'}],'inconclusive');
const alternative=await runCase([{url:oa,body:own},{url:cr,status:404,body:'missing'},{url:dc,body:{data:{attributes:{titles:[{title:'Different main'},{title:'A title',titleType:'AlternativeTitle'}]}}}}],'review');
same(alternative.report.registry.alternate_titles,['A title'],'Alternate title stays explicit');
const secondary='10.1234/second';
const partial=await runCase([{url:oa,body:{...own,locations:[{landing_page_url:'https://doi.org/'+secondary}]}},{url:cr,body:registry},{url:'https://api.crossref.org/works/'+secondary,status:403,body:'denied'}],'inconclusive');
same(partial.report.scope.all_selected_registry_sources_read,false,'Partial source audit cannot claim alignment');
assert.ok(partial.report.signals.includes('registry_source_unavailable'));assertions++;
const requested='10.1234/requested';
const differing=await runCase([{url:'https://api.openalex.org/works/https://doi.org/'+requested,body:own},{url:'https://api.crossref.org/works/'+requested,body:registry},{url:cr,body:registry}],'review',requested);
same(differing.report.comparison.selected_doi,requested,'Requested DOI is compared before canonical DOI');
const huge=await runCase([{url:oa,body:new Uint8Array(2*1024*1024+1)}],'inconclusive');
same(huge.report.errors[0].kind,'response_too_large','Response cap errors preserve evidence');
same(huge.report.evidence[0].truncated,true,'Saved prefix is marked');
same(huge.report.evidence[0].bytes,2*1024*1024,'Two MiB body maximum');

const timeoutEngine=makeCore(true);let timeoutCalls=0;
const timeoutReport=await timeoutEngine.audit('W123',()=>{},(_url,{signal})=>new Promise((_resolve,reject)=>{
  timeoutCalls++;signal.addEventListener('abort',()=>reject(new Error('Aborted')),{once:true});
}));
same(timeoutCalls,2,'Timeout retries at most once');same(timeoutReport.status,'inconclusive','Timeout cannot become alignment');
same(timeoutReport.errors[0].kind,'network_error','Timeout is receipted as network failure');
for(const [input,expected] of fixtures.inputs.filter(([,expected])=>expected===null)){
  let touched=false;await assert.rejects(core.audit(input,()=>{},()=>{touched=true;throw new Error('must not fetch');}));assert.equal(touched,false);assertions++;
}

// Exercise the three captured cases and their actual download listeners through
// a minimal DOM. This checks generated artifacts without executing a browser.
const page=readFileSync(resolve(root,'web/index.html'),'utf8');
const dataMatch=/<script id="sourcecheck-data" type="application\/json">([^]*?)<\/script>/.exec(page);
assert.ok(dataMatch,'Bundled case data must be present');
const bundledData=JSON.parse(dataMatch[1]);
function uiHarness(data){
  const elements=new Map(),downloads=[],blobs=new Map();let nextBlob=1;
  class Element{
    constructor(id=''){this.id=id;this.dataset={};this.handlers={};this.attributes={};this.textContent='';this.value='';this.classList={toggle(){}};this._html='';}
    addEventListener(type,fn){(this.handlers[type]??=[]).push(fn);}
    setAttribute(name,value){this.attributes[name]=value;}
    removeAttribute(name){delete this.attributes[name];}
    focus(){}
    appendChild(){}
    remove(){}
    click(){if(this.download)downloads.push({name:this.download,blob:blobs.get(this.href)});for(const fn of this.handlers.click||[])fn({preventDefault(){}});}
    set innerHTML(value){this._html=value;if(this.id==='audit-output')for(const id of ['download-json','download-triage'])elements.set(id,new Element(id));}
    get innerHTML(){return this._html;}
  }
  const get=id=>{if(!elements.has(id))elements.set(id,new Element(id));return elements.get(id);};
  get('sourcecheck-data').textContent=JSON.stringify(data);
  const buttons=['collision','identity','aligned'].map(id=>{const el=new Element();el.dataset.case=id;return el;});
  const document={getElementById:get,querySelectorAll:selector=>selector==='[data-case]'?buttons:[],createElement:()=>new Element(),body:new Element('body')};
  class LocalURL extends URL{}
  LocalURL.createObjectURL=blob=>{const id='blob:test/'+nextBlob++;blobs.set(id,blob);return id;};LocalURL.revokeObjectURL=()=>{};
  const context={document,SourceCheck:core,structuredClone,Blob,URL:LocalURL,setTimeout:()=>0,clearTimeout:()=>{}};
  vm.runInNewContext(readFileSync(resolve(root,'web/sourcecheck-ui.js'),'utf8'),context,{filename:'sourcecheck-ui.js'});
  return {elements,get,buttons,downloads,context};
}
const ui=uiHarness(bundledData);
for(const button of ui.buttons){
  button.click();assert.ok(ui.get('audit-output').innerHTML.includes('Audit result'));assertions++;
  ui.get('download-json').click();ui.get('download-triage').click();
}
same(ui.downloads.length,6,'All captured cases expose both download actions');
for(const download of ui.downloads){
  assert.ok(download.blob,'Download has a concrete Blob');assertions++;
  const text=await download.blob.text();
  if(download.name.endsWith('.json')){
    const report=JSON.parse(text);assert.ok(report.evidence.length);assertions++;
    for(const receipt of report.evidence){
      if(!receipt.sha256)continue;
      assert.equal(typeof receipt.body_base64,'string','Evidence export includes raw captured bytes');
      assert.equal(createHash('sha256').update(Buffer.from(receipt.body_base64,'base64')).digest('hex'),receipt.sha256);assertions+=2;
    }
  }else{assert.ok(text.includes('No automatic correction')||text.includes('No correction'));assertions++;}
}
const poisoned=structuredClone(bundledData),badTitle='<img src=x onerror="globalThis.PWNED=true">Unsafe <script>alert(1)</script>\n# Injected';
const badInput="10.1234/evil'$(echo${IFS}bad)";
poisoned.cases.collision.report.work.title=badTitle;
poisoned.cases.collision.report.input.normalized=badInput;
const hostileUI=uiHarness(poisoned);
assert.equal(hostileUI.context.PWNED,undefined);assertions++;
assert.ok(!hostileUI.get('audit-output').innerHTML.includes('<img src=x'));assertions++;
assert.ok(hostileUI.get('audit-output').innerHTML.includes('&lt;img'));assertions++;
hostileUI.get('download-triage').click();
const markdown=await hostileUI.downloads[0].blob.text();
assert.ok(!markdown.includes('<img src=x'),'Markdown exports must escape source-supplied HTML');assertions++;
assert.ok(!markdown.includes('\n# Injected'),'Metadata newlines cannot introduce Markdown headings');assertions++;
const shellQuote=value=>"'"+value.replaceAll("'","'\"'\"'")+"'";
const escapedQuote=value=>"'"+value.replaceAll("'","'\\''")+"'";
assert.ok([shellQuote(badInput),escapedQuote(badInput)].some(value=>markdown.includes('python3 -m sourcecheck audit '+value+' --output')),'Reproduce command safely quotes even DOI shell metacharacters');assertions++;
console.log(JSON.stringify({passed:true,raw_receipts_verified:fixtures.receipt_count,parsed_receipts:fixtures.records.length,normalization_edges:fixtures.edges.length,assertions,live_replay_requests:calls.length,ui_downloads:ui.downloads.length,network_requests:0},null,2));
