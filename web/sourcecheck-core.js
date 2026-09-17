/* Read-only source audit. No mutation endpoint, secret, model, or external script. */
const SourceCheck = (() => {
  'use strict';
  const MAX_DOIS = 6, MAX_BYTES = 2 * 1024 * 1024;
  const allowed = new Set(['api.openalex.org', 'api.crossref.org', 'api.datacite.org']);
  const unique = xs => [...new Set(xs)];
  const strings = xs => Array.isArray(xs) ? xs.filter(x => typeof x === 'string' && x.trim()) : [];
  const fold = x => [...x.toLowerCase()].map(c => NORMALIZATION.casefold[c] || c).join('');
  const pySpace = /[\p{White_Space}\u001c-\u001f]/u;
  const collapseSpace = x => x.replace(/[\p{White_Space}\u001c-\u001f]+/gu,' ').replace(/^ | $/g,'');
  const numericReplacements = {'0':'\ufffd','13':'\r','128':'€','129':'\u0081','130':'‚','131':'ƒ','132':'„','133':'…','134':'†','135':'‡','136':'ˆ','137':'‰','138':'Š','139':'‹','140':'Œ','141':'\u008d','142':'Ž','143':'\u008f','144':'\u0090','145':'‘','146':'’','147':'“','148':'”','149':'•','150':'–','151':'—','152':'˜','153':'™','154':'š','155':'›','156':'œ','157':'\u009d','158':'ž','159':'Ÿ'};
  function unescapeHTML(s) {
    return s.replace(/&(#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?)/g, (whole, key) => {
      if (key[0] === '#') {
        let n = key[1].toLowerCase() === 'x' ? parseInt(key.slice(2),16) : parseInt(key.slice(1),10);
        if (Object.prototype.hasOwnProperty.call(numericReplacements,n)) return numericReplacements[n];
        if (!Number.isFinite(n) || n > 0x10ffff || (n >= 0xd800 && n <= 0xdfff)) return '\ufffd';
        if ((n>=1&&n<=8)||n===11||(n>=14&&n<=31)||(n>=127&&n<=159)||(n>=0xfdd0&&n<=0xfdef)||(n&0xffff)===0xfffe||(n&0xffff)===0xffff) return '';
        return String.fromCodePoint(n);
      }
      if (Object.prototype.hasOwnProperty.call(NORMALIZATION.entities,key)) return NORMALIZATION.entities[key];
      for(let i=key.length-1;i>1;i--)if(Object.prototype.hasOwnProperty.call(NORMALIZATION.entities,key.slice(0,i)))return NORMALIZATION.entities[key.slice(0,i)]+key.slice(i);
      return whole;
    });
  }
  function markupText(s) {
    // Small text-only tokenizer matching HTMLParser's relevant behavior. Quotes
    // inside attributes do not terminate a tag; mathematical '<' is text.
    const out=[],blocks=new Set(['br','p','div','li','section','h1','h2','h3']);let i=0;
    while(i<s.length){
      const at=s.indexOf('<',i);if(at<0){out.push(unescapeHTML(s.slice(i)));break;}
      out.push(unescapeHTML(s.slice(i,at)));
      if(s.startsWith('<!--',at)){const end=s.indexOf('-->',at+4);if(end<0)break;i=end+3;continue;}
      const tag=/^<\/?([a-zA-Z][\w:.-]*)(?=[\s/>])/.exec(s.slice(at));
      if(!tag&&!s.startsWith('<!',at)&&!s.startsWith('<?',at)){out.push('<');i=at+1;continue;}
      let end=at+1,quote=null;for(;end<s.length;end++){const c=s[end];if(quote){if(c===quote)quote=null;}else if(c==='"'||c==="'")quote=c;else if(c==='>')break;}
      if(end===s.length){out.push(unescapeHTML(s.slice(at)));break;}
      if(tag){const name=tag[1].toLowerCase();if(blocks.has(name))out.push(' ');
        if((name==='script'||name==='style')&&s[at+1]!=='/'&&!s.slice(at,end).endsWith('/')){const close=new RegExp('</'+name+'\\s*>','ig');close.lastIndex=end+1;const found=close.exec(s);if(!found)break;out.push(s.slice(end+1,found.index));i=close.lastIndex;continue;}}
      i=end+1;
    }
    return out.join('');
  }
  function normalizeTitle(value) {
    if (typeof value !== 'string') return '';
    const s=markupText(unescapeHTML(value));
    return collapseSpace(fold(unescapeHTML(s).normalize('NFKC')).replace(/[\p{P}\p{S}]/gu,' '));
  }
  function validDOI(s) { return typeof s === 'string' && [...s].length <= 512 && !/[\x00-\x1f\x7f?#\\]/.test(s) && !pySpace.test(s) && /^10\.\p{Nd}{4,9}\/.+$/iu.test(s); }
  function parseInput(value) {
    if (typeof value !== 'string' || !value || [...value].length > 512 || pySpace.test(value[0]) || pySpace.test(value.at(-1)) || /[\x00-\x1f\x7f\\]/.test(value)) throw new Error('Enter one DOI or OpenAlex work ID, without whitespace or control characters.');
    if (/^W\p{Nd}+$/iu.test(value)) return {raw:value,kind:'work_id',normalized:value.toUpperCase(),input_doi:null};
    if (validDOI(value)) return {raw:value,kind:'doi',normalized:value.toLowerCase(),input_doi:value.toLowerCase()};
    // Read the original path: WHATWG URL would silently normalize backslashes
    // and dot segments, changing the DOI the person actually supplied.
    const parts=/^https:\/\/([^/]+)(\/[^?#]*)$/.exec(value),netloc=parts?.[1];
    if (!parts || !['openalex.org','api.openalex.org','doi.org','dx.doi.org'].includes(netloc)) throw new Error('Only plain HTTPS OpenAlex or doi.org URLs are supported. Remove credentials, ports, query strings, and fragments.');
    let path; try { path = decodeURIComponent(parts[2].replace(/%(?![0-9a-f]{2})/gi,'%25')); } catch { throw new Error('The URL contains invalid encoding.'); }
    if (netloc.includes('openalex.org')) {
      const match = (netloc === 'api.openalex.org' ? /^\/works\/(W\p{Nd}+)$/iu : /^\/(W\p{Nd}+)$/iu).exec(path);
      if (!match) throw new Error('OpenAlex URLs must identify one W-number work.');
      return {raw:value,kind:'work_id',normalized:match[1].toUpperCase(),input_doi:null};
    }
    const doi = path.slice(1); if (!validDOI(doi)) throw new Error('The URL does not contain a supported DOI.');
    return {raw:value,kind:'doi',normalized:doi.toLowerCase(),input_doi:doi.toLowerCase()};
  }
  const doiFrom = value => { try { return parseInput(value).input_doi; } catch { return null; } };
  function emptyRegistry(provider,doi) { return {provider,doi,status:'found',main_titles:[],alternate_titles:[],alternate_title_details:[],subtitles:[],author_names:[],author_family_names:[],related_identifiers:[],related_identifier_count:0,related_identifiers_truncated:false}; }
  function parseRegistry(provider,doi,document) {
    const item=emptyRegistry(provider,doi), relations=[];
    if (provider === 'crossref') {
      const m=document?.message; if (!m || typeof m !== 'object' || Array.isArray(m)) throw Object.assign(new Error('Crossref response has no message object.'),{kind:'invalid_schema',status:200});
      item.main_titles=strings(m.title); item.subtitles=strings(m.subtitle); item.alternate_titles=strings(m['short-title']);
      item.alternate_title_details=item.alternate_titles.map(title=>({title,type:'short-title'}));
      for (const a of Array.isArray(m.author)?m.author:[]) {
        if (!a || typeof a !== 'object') continue;
        const name=[a.given,a.family].filter(s=>typeof s==='string'&&s).join(' ') || a.name;
        if (typeof name==='string'&&name) item.author_names.push(name);
        if (typeof a.family==='string'&&a.family) item.author_family_names.push(a.family);
      }
      for (const [type,values] of Object.entries(m.relation||{})) for(const v of Array.isArray(values)?values:[]) if(typeof v?.id==='string') relations.push({identifier:v.id,identifier_type:v['id-type']||'unknown',relation_type:type,merge_evidence:false});
    } else {
      const a=document?.data?.attributes; if (!a || typeof a!=='object' || Array.isArray(a)) throw Object.assign(new Error('DataCite response has no attributes object.'),{kind:'invalid_schema',status:200});
      for(const t of Array.isArray(a.titles)?a.titles:[]) {
        if(typeof t?.title!=='string'||!t.title.trim()) continue;
        if(!t.titleType) item.main_titles.push(t.title);
        else if(t.titleType==='Subtitle') item.subtitles.push(t.title);
        else { item.alternate_titles.push(t.title); item.alternate_title_details.push({title:t.title,type:t.titleType}); }
      }
      for(const c of Array.isArray(a.creators)?a.creators:[]) {
        if(!c||typeof c!=='object') continue;
        const name=(typeof c.name==='string'&&c.name)?c.name:[c.givenName,c.familyName].filter(s=>typeof s==='string'&&s).join(' ');
        if(name) item.author_names.push(name);
        if(typeof c.familyName==='string'&&c.familyName) item.author_family_names.push(c.familyName);
        else if(c.nameType!=='Organizational'&&name.includes(',')) item.author_family_names.push(name.split(',')[0].trim());
      }
      for(const r of Array.isArray(a.relatedIdentifiers)?a.relatedIdentifiers:[]) if(typeof r?.relatedIdentifier==='string'&&typeof r?.relationType==='string') relations.push({identifier:r.relatedIdentifier,identifier_type:r.relatedIdentifierType||'unknown',relation_type:r.relationType,merge_evidence:false});
    }
    item.related_identifier_count=relations.length;item.related_identifiers=relations.slice(0,50);item.related_identifiers_truncated=relations.length>50;return item;
  }
  function extractWork(doc) {
    if(!doc||typeof doc.id!=='string') throw Object.assign(new Error('OpenAlex response lacks an identifiable work.'),{kind:'invalid_schema',status:200});
    const names=[],families=[],dois=[];
    for(const a of Array.isArray(doc.authorships)?doc.authorships:[]) {
      const name=(typeof a?.raw_author_name==='string'&&a.raw_author_name)?a.raw_author_name:a?.author?.display_name;
      if(typeof name==='string'&&name.trim()) { names.push(name);families.push(name.includes(',')?name.split(',')[0].trim():name.trim().split(/\s+/).at(-1)); }
    }
    for(const l of [doc.primary_location,...(Array.isArray(doc.locations)?doc.locations:[])]) if(l&&typeof l==='object') for(const k of ['doi','landing_page_url','pdf_url']) {const doi=doiFrom(l[k]);if(doi)dois.push(doi);}
    return {id:doc.id,doi:doiFrom(doc.doi),title:typeof doc.title==='string'?doc.title:doc.display_name??null,author_names:names,author_family_names:families,author_family_name_method:'Heuristic: comma-leading segment or last whitespace token; not verified personal identity.',location_dois:unique(dois)};
  }
  function sourceConflicts(sources) {
    const pairs=[],related=new Map();
    sources.forEach((left,i)=>{
      const lt=new Set(left.main_titles.map(normalizeTitle).filter(Boolean));
      for(const right of sources.slice(i+1)){const rt=right.main_titles.map(normalizeTitle).filter(Boolean);if(lt.size&&rt.length&&!rt.some(t=>lt.has(t)))pairs.push([left.doi,right.doi]);}
      for(const r of left.related_identifiers){const key=fold(r.identifier)+'\n'+fold(r.relation_type);if(!related.has(key))related.set(key,{...r,source_dois:[]});const v=related.get(key);if(!v.source_dois.includes(left.doi))v.source_dois.push(left.doi);}
    });
    return {distinct_normalized_main_titles:unique(sources.flatMap(s=>s.main_titles).map(normalizeTitle).filter(Boolean)),divergent_source_doi_pairs:pairs,common_related_identifiers:[...related.values()].filter(r=>r.source_dois.length>1),note:'Shared citation targets are never identity evidence. Version relations are review hints only. Distinct titles can be legitimate versions or translations; this audit does not establish conflation or its cause.'};
  }
  function assemble(parsed,work,sources,evidence=[],errors=[],checkedAt=new Date().toISOString()) {
    const selected=parsed.input_doi||work?.doi, all=work?unique([selected,work.doi,...work.location_dois].filter(Boolean)):[];
    const r={schema_version:'1.0',rule_version:'title-equality-v1',checked_at:checkedAt,status:'inconclusive',summary:'Source evidence is insufficient for a title comparison.',input:parsed,work,registry:sources[0]||null,registry_sources:sources,comparison:null,signals:[],evidence,errors,source_conflicts:sources.length?sourceConflicts(sources):null,scope:{registry_doi_limit:6,registry_dois_checked:all.slice(0,6),registry_dois_omitted:all.slice(6),all_selected_registry_sources_read:false},policy:'Read-only comparison. Review is a request for investigation, not an error verdict. No correction, merge, or identity assignment is generated.'};
    if(!work){r.summary='OpenAlex evidence could not be read; no comparison decision was made.';return r;}
    if(!selected){r.signals.push('no_comparable_doi');r.summary='No comparable DOI was supplied or present on the OpenAlex work.';return r;}
    const primary=sources[0];if(!primary)return r;
    const wt=normalizeTitle(work.title),rt=primary.main_titles.map(normalizeTitle),usable=rt.filter(Boolean),matched=primary.main_titles.find(t=>wt&&normalizeTitle(t)===wt)||null;
    const mismatch=Boolean(parsed.input_doi&&work.doi&&parsed.input_doi!==work.doi);
    if(mismatch)r.signals.push('input_doi_differs_from_openalex_canonical_doi');
    r.scope.all_selected_registry_sources_read=sources.length===Math.min(all.length,MAX_DOIS)&&sources.every(s=>s.status==='found');
    if(!r.scope.all_selected_registry_sources_read)r.signals.push('registry_source_unavailable');
    const wa=new Set(work.author_family_names.map(normalizeTitle).filter(Boolean)),ra=new Set(primary.author_family_names.map(normalizeTitle).filter(Boolean));
    const shared=[...wa].filter(x=>ra.has(x)).sort(),scores=usable.map(t=>{const a=new Set(wt.split(' ')),b=new Set(t.split(' '));return wt&&t?[...a].filter(x=>b.has(x)).length/new Set([...a,...b]).size:null;}).filter(x=>x!==null);
    r.comparison={selected_doi:selected,input_doi_differs_from_canonical:mismatch,normalized_work_title:wt,normalized_registry_main_titles:rt,matched_main_title:matched,token_jaccard:scores.length?Math.max(...scores):null,token_jaccard_note:'Descriptive overlap of normalized word sets; not confidence, probability, or an identity rule.',author_family_overlap:{shared,work_count:wa.size,registry_count:ra.size,shared_count:shared.length,work_fraction:wa.size&&ra.size?shared.length/wa.size:null,registry_fraction:wa.size&&ra.size?shared.length/ra.size:null,note:'Unique family-name token overlap is supporting or contradicting context, never an identity decision; OpenAlex names are parsed heuristically.'}};
    if(primary.status!=='found'||!wt||!usable.length){r.signals.push('missing_usable_main_title_or_registry');return r;}
    if(matched){r.status='aligned';r.summary='The OpenAlex title equals a registry main title under the documented text rule. This does not prove record identity.';}
    else{r.status='review';r.signals.push('title_divergence');r.summary='The OpenAlex and requested DOI registry main titles differ. Review the source records; no error verdict or automatic correction is made.';}
    if(mismatch){r.status='review';r.summary="The requested DOI differs from OpenAlex's canonical DOI. Source relationships need review; version families can legitimately have multiple DOIs.";}
    if(r.source_conflicts.divergent_source_doi_pairs.length){r.status='review';r.signals.push('multiple_registry_main_titles_across_location_dois');r.summary='The bounded DOI source set contains differing registry main titles. Review their authors and relationships; versions or translations may explain differences.';}
    else if(r.status==='aligned'&&!r.scope.all_selected_registry_sources_read){r.status='inconclusive';r.summary='The primary title matches, but one or more selected registry sources could not be read. The bounded source audit is incomplete.';}
    return r;
  }
  const encodeDOI = doi => encodeURIComponent(doi).replace(/%2F/gi,'/');
  async function audit(value,onProgress=()=>{},fetcher=fetch) {
    const parsed=parseInput(value), evidence=[],errors=[];
    async function getJSON(url) {
      const u=new URL(url),prefix=u.hostname==='api.datacite.org'?'/dois/':'/works/';if(!allowed.has(u.host)||u.protocol!=='https:'||u.search||u.hash||u.username||u.password||!u.pathname.startsWith(prefix))throw new Error('Blocked URL outside public API allowlist.');
      for(let attempt=1;attempt<=2;attempt++) {
        const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),5000);let response=null,bytes;
        try {
          onProgress('Reading '+u.hostname+u.pathname+' · attempt '+attempt);
          response=await fetcher(url,{signal:ctl.signal,credentials:'omit',redirect:'error',headers:{Accept:'application/json'},cache:'no-store'});
          const reader=response.body.getReader(),chunks=[];let total=0,truncated=false;
          try{while(true){const {done,value:chunk}=await reader.read();if(done)break;const room=MAX_BYTES-total;if(chunk.length>room){chunks.push(chunk.slice(0,room));total=MAX_BYTES;truncated=true;await reader.cancel();break;}chunks.push(chunk);total+=chunk.length;}}finally{reader.releaseLock();}
          bytes=new Uint8Array(total);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
          const sha=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
          let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
          evidence.push({url,http_status:response.status,retrieved_at:new Date().toISOString(),sha256:sha,bytes:total,attempt,truncated,body_base64:btoa(binary),error_kind:null});
          if(truncated)throw Object.assign(new Error('Response exceeded the two MiB cap; only a marked prefix was kept.'),{kind:'response_too_large',status:response.status});
          if([408,429,500,502,503,504].includes(response.status)&&attempt===1){const retry=response.headers.get('Retry-After');const wait=retry===null?250:/^\d+(\.\d+)?$/.test(retry)?Number(retry)*1000:Date.parse(retry)-Date.now();if(Number.isFinite(wait)&&wait>=0&&wait<=2000){clearTimeout(timer);await new Promise(resolve=>setTimeout(resolve,wait));continue;}}
          if(response.status!==200)throw Object.assign(new Error('Public API returned HTTP '+response.status+'.'),{kind:response.status===404?'not_found':response.status===429?'rate_limited':'http_error',status:response.status});
          try{return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw Object.assign(new Error('API response was not valid JSON.'),{kind:'invalid_json',status:200});}
        } catch(error) {
          if(error.kind)throw error;
          evidence.push({url,http_status:null,retrieved_at:new Date().toISOString(),sha256:null,bytes:0,attempt,truncated:false,error_kind:'network_error'});
          if(attempt===1){clearTimeout(timer);await new Promise(resolve=>setTimeout(resolve,250));continue;}
          throw Object.assign(new Error('The public API could not be read. It may be unavailable, blocked by the network, or not allowing browser access.'),{kind:'network_error',status:null});
        } finally{clearTimeout(timer);}
      }
    }
    async function registry(doi){
      for(const [provider,base] of [['crossref','https://api.crossref.org/works/'],['datacite','https://api.datacite.org/dois/']]){
        try{return parseRegistry(provider,doi,await getJSON(base+encodeDOI(doi)));}
        catch(e){errors.push({provider,doi,kind:e.kind||'invalid_schema',http_status:e.status||null,message:e.message});if(provider==='crossref'&&e.status===404)continue;return {...emptyRegistry(provider,doi),status:e.status===404?'not_found':'error'};}
      }
    }
    let work;
    try{work=extractWork(await getJSON('https://api.openalex.org/works/'+(parsed.kind==='work_id'?parsed.normalized:'https://doi.org/'+encodeDOI(parsed.input_doi))));}
    catch(e){errors.push({provider:'openalex',kind:e.kind||'invalid_schema',http_status:e.status||null,message:e.message});return assemble(parsed,null,[],evidence,errors);}
    const selected=parsed.input_doi||work.doi;if(!selected)return assemble(parsed,work,[],evidence,errors);
    const candidates=unique([selected,work.doi,...work.location_dois].filter(Boolean)).slice(0,MAX_DOIS),sources=[];
    for(const doi of candidates)sources.push(await registry(doi));
    return assemble(parsed,work,sources,evidence,errors);
  }
  return {parseInput,normalizeTitle,parseRegistry,extractWork,sourceConflicts,assemble,audit};
})();
if(typeof module!=='undefined')module.exports=SourceCheck;
