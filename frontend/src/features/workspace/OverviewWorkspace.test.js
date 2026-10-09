import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

let server, components, App;
before(async () => {
  server = await createServer({ root: fileURLToPath(new URL('../../..', import.meta.url)), appType: 'custom', configLoader: 'native', logLevel: 'silent', server: { middlewareMode: true } });
  components = await server.ssrLoadModule('/src/features/workspace/Overview.jsx');
  ({ default: App } = await server.ssrLoadModule('/src/App.jsx'));
});
after(async () => { await server?.close(); });

test('application starts on Overview with one global unlock and no example portfolio', () => {
  const html = renderToStaticMarkup(React.createElement(App));
  assert.match(html, /data-workspace="overview" aria-current="page"/);
  assert.equal((html.match(/>Unlock private workspace<\/button>/g) || []).length, 1);
  assert.match(html, /No broker account is connected/);
  assert.doesNotMatch(html, /Portfolio Simulations|SPY|TLT|NAV:|TWR:/);
});

test('Overview renders exact recorded quantities without inventing values or zero holdings', () => {
  const state = { portfolios: [{ id: 'p', name: 'Recorded account', base_currency: 'GBP' }], selectedId: 'p', securities: { s: { ticker: 'TEST', name: 'Equity name' } }, ledger: { version: 2, as_of: '2026-09-13', known_at: '2026-09-13', positions: [{ security_id: 's', quantity: '2.5000', currency: 'USD' }], cash: [{ currency: 'GBP', amount: '7.2000' }] } };
  const render = value => renderToStaticMarkup(React.createElement(components.OverviewRecords, { state: value }));
  const html = render(state);
  for (const value of ['Recorded account', 'TEST', '2.5000', '7.2000', '2026-09-13', 'not inferred from cost']) assert.ok(html.includes(value));
  assert.doesNotMatch(html, /[£$][0-9]|NAV|TWR|0%/);
  assert.match(render({ ...state, ledger: { ...state.ledger, positions: [], cash: [] } }), /No open positions recorded/);
  assert.doesNotMatch(render({ ...state, ledger: null }), /No open positions recorded/);
});
