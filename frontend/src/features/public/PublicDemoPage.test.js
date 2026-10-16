import assert from 'node:assert/strict';
import { after,before,test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

let server,component,snapshot;
before(async()=>{
  server=await createServer({root:fileURLToPath(new URL('../../..',import.meta.url)),appType:'custom',configLoader:'native',logLevel:'silent',server:{middlewareMode:true}});
  component=(await server.ssrLoadModule('/src/features/public/PublicDemoPage.jsx')).PublicSnapshotView;
  snapshot=JSON.parse(await readFile(new URL('../../../../backend/demo/public_preview_v1.json',import.meta.url),'utf8'));
});
after(async()=>{await server?.close();});

test('public view displays synthetic identity, partial periods, complete loss and date distinctions',()=>{
  const html=renderToStaticMarkup(React.createElement(component,{envelope:snapshot,downloadUrl:'http://local/api/public-preview/original/download'}));
  for(const text of ['Local preview','not published','synthetic data','no real money invested','Maximum drawdown','Partial period','Orchard Systems','-US$400.00','fee reversed','actual creation','actually recorded','matching ex ante covariance inputs not supplied','not investment advice','sanitized synthetic snapshot']) assert.ok(html.includes(text),text);
  assert.ok(html.includes('id="research-orchard-v1"'));
  assert.doesNotMatch(html,/X-Research-Key|owner_key|account_label|ledger_records|private_note/);
});

test('empty public history never invents zero periods or growth',()=>{
  const empty=structuredClone(snapshot);empty.snapshot.series=[];empty.snapshot.monthly=[];empty.snapshot.annual=[];
  const html=renderToStaticMarkup(React.createElement(component,{envelope:empty,downloadUrl:'/download'}));
  assert.match(html,/No measured history is available/);
  assert.match(html,/No measured periods/);
});
