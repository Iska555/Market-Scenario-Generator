import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

let server;
let components;
before(async () => {
  server = await createServer({ root: fileURLToPath(new URL('../../..', import.meta.url)), appType: 'custom', configLoader: 'native', logLevel: 'silent', server: { middlewareMode: true } });
  components = await server.ssrLoadModule('/src/features/ledger/LedgerWorkspace.jsx');
});
after(async () => { await server?.close(); });

test('ledger starts disconnected with honest persistence and no invented broker account', () => {
  const html = renderToStaticMarkup(React.createElement(components.default, { apiUrl: 'http://local', isDark: false }));
  assert.doesNotMatch(html, /type="password"/);
  assert.match(html, /Unlock private workspace to continue/);
  assert.match(html, /No broker is connected/);
  assert.doesNotMatch(html, /Planned broker|Stocks &amp; Shares ISA/);
  assert.match(html, /Persisted transactions remain on the server/);
  assert.doesNotMatch(html, /£[0-9]/);
});

test('ledger results render exact holdings, cash, history and undefined valuation honestly', () => {
  const state = {
    base_currency: 'GBP', version: 7, as_of: '2026-09-12T08:00:00+00:00', known_at: '2026-09-12T09:00:00+00:00', convention: 'trade_date_economic_cash',
    cash: [{ currency: 'GBP', amount: '125.5000000000' }],
    positions: [{ security_id: 'security-1', currency: 'USD', quantity: '2.5000000000', cost_basis: '200.0000000000', average_cost: '80.0000000000' }],
  };
  const history = { total: 1, transactions: [{ id: 'transaction-1', sequence: 7, type: 'BUY', effective_at: '2026-09-10T08:00:00+00:00', recorded_at: '2026-09-12T08:00:00+00:00', currency: 'USD', security_id: 'security-1', quantity: '2.5000000000', price: '80.0000000000', amount: null, fees: '0.50', to_currency: null, to_amount: null, fx_rate: null, reverses_id: null, source: 'manual', external_reference: 'buy-1', note: '', content_sha256: 'abc' }] };
  const valuation = { state: { ...state, as_of: '2026-09-11T08:00:00+00:00' }, nav: null, reason: 'missing_price', positions: [{ ...state.positions[0], market_value_local: null, unrealized_pnl_local: null, market_value_base: null, translated_unrealized_pnl_base: null, weight: null, reason: 'missing_price' }], cash: [{ currency: 'GBP', amount: '125.5000000000', value_base: '125.5000000000', weight: null, reason: 'incomplete_nav' }], inputs: { as_of: '2026-09-11T08:00:00+00:00', prices: [{ security_id: 'security-1', currency: 'USD', price: '100.00', observed_at: '2026-09-11T07:00:00+00:00', source: 'owner supplied close' }], fx: [] } };
  const html = renderToStaticMarkup(React.createElement(components.LedgerResults, { state, history, valuation }));
  for (const text of ['125.5000000000', '2.5000000000', '200.0000000000', '80.0000000000', 'buy-1', 'transaction-1', 'missing_price', 'Undefined']) assert.ok(html.includes(text), text);
  assert.match(html, /trade_date_economic_cash/);
  assert.match(html, /History includes reversals/);
  assert.match(html, /Cash valuation/);
  assert.match(html, /owner supplied close/);
  assert.match(html, /Supplied marks and FX provenance/);
  assert.match(html, /GBP/);
  assert.match(html, /2026-09-11T08:00:00\+00:00/);
  assert.match(html, /<details/);
  assert.match(html, /Content hash/);
  assert.doesNotMatch(html, /min-w-\[2200px\]/);
});

test('transaction preview labels a captured atomic batch and duplicate replay', () => {
  const preview = { inserted: 0, duplicates: 1, transactions: [{ id: 'existing-1', sequence: 4, type: 'DEPOSIT', effective_at: '2026-09-01T00:00:00+00:00', currency: 'GBP', amount: '100.00', fees: '0', source: 'lightyear_reviewed', external_reference: 'deposit-1' }], state: { ...({ base_currency: 'GBP', version: 4, cash: [], positions: [], convention: 'trade_date_economic_cash' }) } };
  const html = renderToStaticMarkup(React.createElement(components.PreviewPanel, { preview, canSave: true, busy: false, saveStatus: '', onSave: () => {} }));
  assert.match(html, /Captured atomic batch/);
  assert.match(html, /1 duplicate replay/);
  assert.match(html, /Save captured batch/);
  assert.match(html, /deposit-1/);
  assert.match(html, /<th class="p-3">Currency<\/th>/);
  assert.match(html, /<td class="p-3">GBP<\/td>/);
});
