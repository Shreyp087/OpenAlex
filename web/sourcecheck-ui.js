(() => {
  'use strict';
  const DATA=JSON.parse(document.getElementById('sourcecheck-data').textContent);
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  // Metadata is untrusted in Markdown too; preserve exact raw values in JSON.
  const md=value=>String(value??'').replace(/[\r\n\u2028\u2029]/g,' ').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/[\\`*_{}\[\]()#+.!|~-]/g,'\\$&');
  const shellQuote=value=>"'"+String(value).replace(/'/g,"'\\''")+"'";
  const byId=id=>document.getElementById(id), input=byId('record-input'), output=byId('audit-output'), status=byId('audit-status');
  let active=null, busy=false;
  const external=(url,label)=>`<a href="${esc(url)}" target="_blank" rel="noopener">${esc(label)} ↗</a>`;
  const doiLink=doi=>external('https://doi.org/'+encodeURIComponent(doi).replace(/%2F/gi,'/'),doi);
  const apiLink=id=>/^https:\/\/openalex.org\/W\d+$/.test(id||'')?external(id,id.split('/').at(-1)):esc(id||'Unavailable');
  const safeAPI=url=>{try{const u=new URL(url);return u.protocol==='https:'&&['api.openalex.org','api.datacite.org','api.crossref.org'].includes(u.host)&&!u.username&&!u.password?u.href:null;}catch{return null;}};
  function setStatus(text,error=false){status.textContent=text;status.classList.toggle('error',error);}
  function downloadable(name,text,type='application/json'){
    const blob=new Blob([text],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);
  }
  function triage(report){
    const r=report, lines=['# SourceCheck review packet','','Status: '+md(r.status),'Observed: '+md(r.checked_at),'Rule: '+md(r.rule_version),'Input: '+md(r.input.normalized),'',md(r.summary),'','## Observations',''];
    if(r.work)lines.push('- OpenAlex: '+md(r.work.id),'- OpenAlex main DOI: '+md(r.work.doi||'none'),'- OpenAlex title: '+md(r.work.title||'missing'));
    for(const s of r.registry_sources||[])lines.push('- '+md(s.provider)+' / '+md(s.doi)+' ['+md(s.status)+']: '+md(s.main_titles.join(' | ')||'No main title'));
    lines.push('','## Scope and uncertainty','',r.policy,'','Requested DOI sources checked: '+r.scope.registry_dois_checked.length,'Sources omitted by this run: '+r.scope.registry_dois_omitted.length,'Shared Cites targets are not identity evidence. Version relations are review hints. No automatic correction or split is proposed.');
    if(r.capture_note)lines.push('',r.capture_note);
    lines.push('','## Reproduce live','','    python3 -m sourcecheck audit '+shellQuote(r.input.normalized)+' --output report.json --evidence-dir receipts','','A new run observes current data and may differ. Captured bodies and timestamps accompany the JSON export.','','## Evidence receipts','');
    for(const e of r.evidence||[])lines.push('- '+md(e.url),'  - HTTP '+md(e.http_status??'unavailable')+'; '+md(e.retrieved_at),'  - SHA-256 '+md(e.sha256||'no response body'));
    lines.push('','## Maintainer review','', 'Verify which harvested source records describe the same publication. Check authors, version relationships, references, and publisher records before changing identity or splitting records. Review dependent citations, topics, and full text.','','This packet is a draft for inspection. SourceCheck does not submit it to OpenAlex.');
    return lines.join('\n');
  }
  function render(r,mode){
    active={report:r,mode};const primary=r.registry,work=r.work,compare=r.comparison;
    const titles={review:'SOURCES NEED REVIEW.',aligned:'PRIMARY TITLES ALIGN.',inconclusive:'EVIDENCE IS INCOMPLETE.'};
    let html=`<section aria-label="Audit result"><div class="result-head"><div><span class="result-tag">${esc(r.status.toUpperCase())} / ${mode==='live'?'LIVE API CHECK':'CAPTURED PUBLIC RESPONSES'}</span><h3>${titles[r.status]||titles.inconclusive}</h3><p>${esc(r.summary)}</p></div><div class="meta">${esc(r.checked_at.slice(0,19).replace('T',' '))} UTC<br>${esc(r.rule_version)}<br>${r.evidence.length} response / attempt receipts</div></div>`;
    if(work){
      html+=`<div class="comparison"><div><span class="field-label">OPENALEX / ${apiLink(work.id)}</span><h4>${esc(work.title||'Title not supplied')}</h4><p class="doi">Main DOI: ${work.doi?doiLink(work.doi):'not supplied'}</p><p class="authors">${esc(work.author_names.join(' · ')||'Author names not supplied')}</p></div><div><span class="field-label">${esc(primary?.provider?.toUpperCase()||'DOI REGISTRY')} / REQUESTED DOI</span><h4>${esc(primary?.main_titles?.join(' / ')||'No usable registered title')}</h4><p class="doi">${primary?.doi?doiLink(primary.doi):'No comparable DOI'}</p><p class="authors">${esc(primary?.author_names?.join(' · ')||'Author names not supplied')}</p>${primary?.alternate_titles?.length?`<p>Other registered titles: ${esc(primary.alternate_titles.join(' / '))}</p>`:''}</div></div>`;
    }
    if(compare){
      const overlap=compare.author_family_overlap;
      html+=`<div class="finding-row"><span>TITLE COMPARISON</span><p>${compare.matched_main_title?'Normalized main titles are equal.':'Normalized main titles differ or one is unavailable.'} Normalization removes markup and punctuation and applies Unicode case folding.</p></div>`;
      html+=`<div class="finding-row"><span>AUTHOR CONTEXT</span><p>${overlap.work_fraction===null?'Insufficient family-name fields for overlap.':`${overlap.shared_count} shared unique family-name tokens; ${overlap.work_count} in OpenAlex, ${overlap.registry_count} in the primary registry source.`} This is a name-parsing heuristic, not verified author identity.</p></div>`;
    }
    if(r.registry_sources.length){
      const omitted=r.scope.registry_dois_omitted.length;
      html+=`<div class="source-heading"><h4>FOLLOW THE DOI LOCATIONS.</h4><span>${r.registry_sources.length} source DOIs read / ${omitted} not checked${r.capture_scope==='primary'?' / PRIMARY-ONLY CAPTURE':''}</span></div><div class="source-register">`;
      r.registry_sources.forEach((s,i)=>{
        const normalized=s.main_titles.map(SourceCheck.normalizeTitle),same=work&&normalized.includes(SourceCheck.normalizeTitle(work.title));
        const label=s.status!=='found'?s.status.toUpperCase():!normalized.filter(Boolean).length?'NO MAIN TITLE':same?'MATCHES OA TITLE':'DIFFERENT FROM OA TITLE';
        html+=`<article class="source-entry"><span class="source-num">${String(i+1).padStart(2,'0')}</span><div><h5>${esc(s.main_titles.join(' / ')||'Registry evidence unavailable')}</h5><p>${esc(s.author_names.join(' · ')||'No author names read')}</p></div><div class="source-meta">${doiLink(s.doi)}<b>${label}</b></div></article>`;
      });html+='</div>';
      const cited=r.source_conflicts?.common_related_identifiers?.filter(x=>x.relation_type.toLowerCase()==='cites')||[];
      const lead=cited.find(x=>x.identifier.includes('1706.03762'))||cited[0];
      if(lead)html+=`<div class="relation-note"><strong>A shared citation is not a shared identity.</strong><p>${lead.source_dois.length} checked DOI sources carry a <code>Cites</code> relation to <code>${esc(lead.identifier)}</code>. The tool excludes this from identity evidence. Whether a relation caused this OpenAlex record requires an internal investigation.</p></div>`;
      const unavailable=r.registry_sources.filter(s=>s.status!=='found');
      if(omitted||unavailable.length||r.capture_scope==='primary')html+=`<div class="relation-note"><strong>This is a bounded check.</strong><p>${omitted} source DOI(s) were not checked; ${unavailable.length} selected source(s) could not be read. ${esc(r.capture_note||'At most six DOI sources are attempted. A title comparison does not validate the whole record.')}</p></div>`;
    }
    const realErrors=r.errors.filter(e=>!(e.provider==='crossref'&&e.http_status===404&&r.registry_sources.some(s=>s.doi===e.doi&&s.provider==='datacite'&&s.status==='found')));
    if(realErrors.length)html+=`<div class="relation-note"><strong>Unresolved source responses</strong><p>${esc(realErrors.map(e=>e.provider+': '+e.message).join(' '))}</p></div>`;
    html+=`<div class="actions"><button type="button" class="button solid" id="download-json">Download evidence JSON <span>↓</span></button><button type="button" class="button" id="download-triage">Download review packet <span>↓</span></button></div><details class="evidence-details"><summary>Inspect timestamps, source links & SHA-256 receipts <span>+</span></summary><div class="receipts">`;
    for(const e of r.evidence){const url=safeAPI(e.url);html+=`<div class="receipt">${url?external(url,e.url):esc(e.url)}<br>HTTP ${esc(e.http_status??'no response')} · ${esc(e.retrieved_at)} · ${e.bytes} bytes${e.truncated?' · TRUNCATED PREFIX':''}<br><code>SHA-256 ${esc(e.sha256||'Unavailable—no response body')}</code></div>`;}
    html+='</div></details></section>';output.innerHTML=html;
    byId('download-json').addEventListener('click',()=>downloadable('sourcecheck-'+r.input.normalized.replace(/[^a-z0-9-]/gi,'_')+'.json',JSON.stringify({...r,capture_mode:mode},null,2)+'\n'));
    byId('download-triage').addEventListener('click',()=>downloadable('sourcecheck-review.md',triage(r),'text/markdown;charset=utf-8'));
  }
  function selectCase(id){
    if(busy)return;
    const spec=DATA.cases[id];let r;
    if(spec.report)r=structuredClone(spec.report);
    else{
      r=SourceCheck.assemble(SourceCheck.parseInput(spec.input),spec.work,spec.registries,spec.evidence,[],spec.checked_at);
      r.scope.registry_dois_checked=spec.registries.map(s=>s.doi);
      r.scope.registry_dois_omitted=[...new Set([spec.work.doi,...spec.work.location_dois].filter(Boolean))].filter(doi=>!r.scope.registry_dois_checked.includes(doi));
      r.scope.all_selected_registry_sources_read=spec.registries.every(s=>s.status==='found');
    }
    r.capture_scope=spec.scope;r.capture_note=spec.note;
    input.value=spec.input;document.querySelectorAll('[data-case]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.case===id)));
    setStatus('Captured public evidence · '+r.checked_at.slice(0,10)+' · '+spec.note);
    render(r,'captured');
  }
  document.querySelectorAll('[data-case]').forEach(button=>button.addEventListener('click',()=>selectCase(button.dataset.case)));
  byId('audit-form').addEventListener('submit',async event=>{
    event.preventDefault();if(busy)return;
    try{SourceCheck.parseInput(input.value);}catch(e){setStatus(e.message,true);input.focus();return;}
    busy=true;byId('audit-button').disabled=true;input.disabled=true;document.querySelectorAll('[data-case]').forEach(b=>{b.disabled=true;b.setAttribute('aria-pressed','false');});
    output.setAttribute('aria-busy','true');
    try{const r=await SourceCheck.audit(input.value,text=>setStatus(text));render(r,'live');setStatus('Live API check completed · '+r.checked_at.slice(0,19).replace('T',' ')+' UTC · '+r.evidence.length+' response / attempt receipts',r.status==='inconclusive');}
    catch(e){setStatus('The audit could not finish: '+e.message+'. The previous result remains labelled with its original capture time.',true);}
    finally{busy=false;byId('audit-button').disabled=false;input.disabled=false;document.querySelectorAll('[data-case]').forEach(b=>b.disabled=false);output.removeAttribute('aria-busy');}
  });
  const records=DATA.cohort.records,compared=records.filter(r=>typeof r.title_exact_match==='boolean'),disagree=compared.filter(r=>!r.title_exact_match);
  byId('cohort-disagreements').textContent=disagree.length;byId('cohort-compared').textContent=compared.length;
  byId('cohort-bars').innerHTML=records.map(r=>`<span class="${r.title_exact_match===false?'divergent':r.title_exact_match!==true?'unknown':''}" title="DOI suffix ${esc(r.suffix)}: ${r.title_exact_match===false?'disagrees':r.title_exact_match===true?'agrees':'unavailable'}"></span>`).join('');
  byId('cohort-status').textContent=(compared.length-disagree.length)+' agree / '+disagree.length+' differ / '+(records.length-compared.length)+' unavailable · Captured 17 Sep 2026';
  byId('cohort-table').innerHTML=records.map(r=>`<tr><td>${doiLink(r.doi).replace(esc(r.doi),esc(String(r.suffix).padStart(2,'0')))}</td><td>${esc(r.openalex_title||'Unavailable')}</td><td>${esc((r.registry_titles||[]).join(' / ')||'Unavailable')}</td><td>${r.title_exact_match===false?'Review':r.title_exact_match===true?'Titles agree':'Unavailable'}</td></tr>`).join('');
  selectCase('collision');
})();
