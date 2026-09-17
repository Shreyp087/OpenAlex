// Verify the offline UI contract and execute all exported Python regressions.
// This is a DOM stub unit check, not a browser layout test.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const source = fs.readFileSync(path.join(root, 'web/app.js'), 'utf8');
const data = JSON.parse(fs.readFileSync(path.join(root, 'data/demo.json'), 'utf8'));
const nodes = new Map();
const downloads = [];
let latestBlob;
function node(id) {
  if (!nodes.has(id)) nodes.set(id, {innerHTML:'',textContent:'',hidden:true, listeners:{}, attributes:{},classList:{add(){},remove(){},toggle(){}},
    addEventListener(type, callback){this.listeners[type]=callback;},setAttribute(key,value){this.attributes[key]=value;},focus(){},querySelector(){return {focus(){}};}});
  return nodes.get(id);
}
node('demo-data').textContent = JSON.stringify(data);
const context = vm.createContext({
  document:{getElementById:node,body:{appendChild(){}},createElement(){return {click(){downloads.push({name:this.download,blob:latestBlob});},remove(){}};}},
  location:{hostname:''},Blob,
  URL:{createObjectURL(blob){latestBlob=blob;return 'blob:fixture';},revokeObjectURL(){}},
  setTimeout(){return 1;},clearTimeout(){},console,
  fetch(){throw new Error('Offline mode must not make network requests');}
});
vm.runInContext(source, context);
assert.match(node('case-content').innerHTML, /Inspect verified replay/);
assert.equal(node('test-passed').textContent, data.evaluation.passed);
const expected = ['Source-backed repair','Human review needed','Abstain','Idempotent replay'];
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'repair-desk-export-'));
try {
  for (const [i, scenario] of data.scenarios.entries()) {
    node('case-list').listeners.click({target:{closest(){return {dataset:{case:scenario.id}};}}});
    const action = name => node('case-content').listeners.click({target:{closest(selector){return selector === '[data-action]' ? {dataset:{action:name}} : null;}}});
    action('replay');
    assert.match(node('case-content').innerHTML, new RegExp(expected[i]));
    assert.match(node('case-content').innerHTML, /VERIFIED PYTHON OUTPUT/);
    action('bundle');
    const exported = JSON.parse(await downloads.at(-1).blob.text());
    assert.equal(exported.scenario.id, scenario.id);
    assert.equal(exported.evidence_mode, 'bundled-python-output');
    action('test');
    const test = downloads.at(-1);
    assert.match(test.name, /^test_[a-z_]+\.py$/);
    const file = path.join(temp, test.name);
    fs.writeFileSync(file, await test.blob.text());
    const result = spawnSync('python3', [file, '-v'], {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8'});
    assert.equal(result.status, 0, result.stderr);
    action('reply');
    assert.match(await downloads.at(-1).blob.text(), /Fictional ticket; no message has been sent/);
  }
  const html = fs.readFileSync(path.join(root,'web/archive/prototype.html'),'utf8');
  const inertJson = html.match(/<script id="demo-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
  assert.deepEqual(JSON.parse(inertJson), data);
  assert.equal((html.match(/<script/g)||[]).length, 2);
  assert.ok(!/<script[^>]+src=/.test(html));
  // Metadata must be rendered as text, never as markup, even in downloaded snapshots.
  const injected = JSON.parse(JSON.stringify(data));
  injected.scenarios[0].ticket.subject = '<img src=x onerror=alert(1)>';
  injected.scenarios[0].bronze.record.authorships[2].raw_affiliation_strings = ['</pre><script>alert(1)</script>'];
  node('demo-data').textContent = JSON.stringify(injected);
  vm.runInContext(source, context);
  assert.ok(!node('case-content').innerHTML.includes('<img src=x'));
  assert.ok(!node('case-content').innerHTML.includes('</pre><script>'));
  assert.match(node('case-content').innerHTML, /&lt;img src=x/);
  console.log('PASS: four offline decisions, 12 downloads, four exported Python regressions, embedded-data parity, no external scripts, escaped metadata.');
} finally { fs.rmSync(temp,{recursive:true,force:true}); }
