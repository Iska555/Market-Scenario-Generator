import assert from 'node:assert/strict';
import test from 'node:test';
import { DEMO_LABEL, formatMoney, formatPercent, readPublicPreview } from './demo.js';

test('public transport has no owner key or private account request and requires explicit demo preview',async()=>{
  const calls=[];
  const data={status:'local_preview',published_at:null,snapshot:{mode:'demo',label:DEMO_LABEL,schema_version:'demo_snapshot_v1'}};
  const fetcher=async(url,options)=>{calls.push([url,options]);return{ok:true,json:async()=>data};};
  assert.equal(await readPublicPreview('http://local/',undefined,fetcher),data);
  assert.equal(calls[0][0],'http://local/api/public-preview/original');
  assert.equal(calls[0][1].cache,'no-store');
  assert.equal(calls[0][1].headers,undefined);
  for(const change of [{mode:'real'},{mode:'unclassified'},{mode:undefined},{label:'Verified personal record'}]) {
    await assert.rejects(readPublicPreview('http://local',undefined,async()=>({ok:true,json:async()=>({...data,snapshot:{...data.snapshot,...change}})})));
  }
});

test('public metrics format server values and distinguish unavailable from real zero/negative',()=>{
  assert.match(formatPercent({value:null,reason:'missing_marks'}),/Unavailable.*missing marks/);
  assert.equal(formatPercent({value:0}),'0.00%');
  assert.equal(formatPercent({value:-.25}),'-25.00%');
  assert.equal(formatMoney(null),'Unavailable');
  assert.equal(formatMoney(''),'Unavailable');
  assert.equal(formatMoney('-400','USD'),'US$400.00'.replace('US$', '-US$'));
});
