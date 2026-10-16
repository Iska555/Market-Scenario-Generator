import test from 'node:test';
import assert from 'node:assert/strict';
import { createPublicationWorkspace, publicationRequest, readPublished } from './publication.js';
import { DEMO_LABEL } from './demo.js';

test('anonymous published transport excludes owner header and rejects preview identities', async () => {
  let options;
  const fetcher = async (_url, init) => { options = init; return { ok: true, json: async () => ({status:'published',published_at:'2026-10-14T00:00:00Z',snapshot:{mode:'demo',label:DEMO_LABEL,schema_version:'demo_snapshot_v1'}}) }; };
  await readPublished('http://local', null, undefined, fetcher);
  assert.equal(options.headers, undefined);
  assert.equal(options.cache, 'no-store');
  await assert.rejects(readPublished('http://local', null, undefined, async()=>({ok:true,json:async()=>({status:'local_preview'})})), /identity/);
  await assert.rejects(readPublished('http://local', null, undefined, async()=>({ok:false,status:410})), /withdrawn/);
});

test('owner transport keeps key in header and captured body has no key', async () => {
  let seen;
  await publicationRequest('http://local/', 'private-secret', 'publish', {id:'same'}, async(url,options)=>{seen={url,options};return {ok:true,json:async()=>({})};});
  assert.equal(seen.options.headers['X-Research-Key'], 'private-secret');
  assert.equal(seen.options.body, '{"id":"same"}');
  assert.equal(seen.url, 'http://local/api/publication/publish');
});

test('publication uncertain retry preserves captured identity and review, stale conflicts clear preview', async () => {
  const calls=[];let attempt=0;
  const workspace=createPublicationWorkspace(async(action,body,key)=>{
    calls.push({action,body,key});
    if(action==='history')return {sequence:0,events:[]};
    if(action==='previews')return {id:'preview',expected_sequence:0,envelope:{}};
    if(attempt++===0)throw new Error('network');
    return {version:'public-v1'};
  },'isolated',()=> 'intent');
  await workspace.connect('owner-key');
  await workspace.preview();await workspace.publish();
  assert.equal(workspace.getSnapshot().uncertain,true);
  workspace.editSelection([]);workspace.editReason('changed');
  await workspace.retry();
  const publishes=calls.filter(call=>call.action==='publish');
  assert.deepEqual(publishes[0],publishes[1]);
  assert.equal(workspace.getSnapshot().result.version,'public-v1');
  assert.equal(JSON.stringify(workspace.getSnapshot()).includes('owner-key'),false);
  workspace.disconnect();assert.equal(workspace.getSnapshot().result,null);
});

test('lock ignores late preview and new session never retains prior preview', async () => {
  let resolve;
  const workspace=createPublicationWorkspace(async action=>action==='history'?{sequence:0,events:[]}:new Promise(done=>{resolve=done;}),'isolated',()=> 'intent');
  await workspace.connect('owner-key');const pending=workspace.preview();workspace.disconnect();resolve({id:'late'});await pending;
  assert.equal(workspace.getSnapshot().preview,null);assert.equal(workspace.getSnapshot().connected,false);
  await workspace.connect('new-key');assert.equal(workspace.getSnapshot().preview,null);
});

test('correction requires public reason and history conflict invalidates reviewed preview', async () => {
  let publishBody;
  const workspace=createPublicationWorkspace(async(action,body)=>{
    if(action==='history')return {sequence:1,events:[{action:'publish',version:'old'}]};
    if(action==='previews')return {id:'preview'};
    publishBody=body;throw Object.assign(new Error('stale'),{status:409});
  },'isolated',()=> 'intent');
  await workspace.connect('owner-key');await workspace.preview();await workspace.publish();assert.equal(publishBody,undefined);
  workspace.editReason('Include original loss review');await workspace.publish();
  assert.equal(publishBody.correction_of,'old');assert.equal(publishBody.public_reason,'Include original loss review');
  assert.equal(workspace.getSnapshot().preview,null);assert.equal(workspace.getSnapshot().uncertain,false);
});
