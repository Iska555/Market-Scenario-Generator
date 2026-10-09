import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
let server;
let components;
before(async () => {
  server = await createServer({ root: fileURLToPath(new URL('../../..', import.meta.url)), appType: 'custom', configLoader: 'native', logLevel: 'silent', server: { middlewareMode: true } });
  components = await server.ssrLoadModule('/src/features/thesis/ThesisWorkspace.jsx');
});
after(async () => { await server?.close(); });

test('saved revision displays narrative, immutable metadata and declared units', () => {
  const html = renderToStaticMarkup(React.createElement(components.RevisionDetails, { revision: { id: 'revision-9', revision: 9, thesis_id: 'thesis-1', security_id: 'security-1', created_at: '2026-09-09T12:00:00Z', ticker: 'ACME', exchange: 'XNAS', valuation_currency: 'USD', target_low: '15.25', target_high: '20', required_return: '0.08', variant_perception: 'Demand is underestimated', invalidation_conditions: 'Margin collapse', notes: '<script>unsafe</script>' } }));
  for (const text of ['revision-9', 'security-1', '2026-09-09T12:00:00Z', 'ACME', 'XNAS', 'USD', '15.25', '0.08', 'annual effective fraction', 'Demand is underestimated', 'Margin collapse']) assert.ok(html.includes(text), text);
  assert.ok(!html.includes('<script>unsafe</script>'));
});

test('review history records false validity and the exact reviewed revision', () => {
  const html = renderToStaticMarkup(React.createElement(components.ReviewDetails, { review: { id: 'review-1', thesis_id: 'thesis-1', revision_id: 'old-revision-4', reviewed_at: '2026-09-09T12:00:00Z', decision: 'EXIT', thesis_still_valid: false, valuation_currency: 'EUR', current_price: null, updated_expected_return: '-0.2', what_changed: 'New competitor', what_was_correct: 'Good cash flow', what_was_wrong: 'Growth assumption', new_information: 'New filing', notes: 'Owner judgment' } }));
  for (const text of ['old-revision-4', 'EXIT', 'No', 'Not supplied', 'EUR', '-0.2', 'Growth assumption', 'New filing']) assert.ok(html.includes(text), text);
});

test('workspace starts private and disconnected without an automatic decision', () => {
  const html = renderToStaticMarkup(React.createElement(components.default, { apiUrl: 'http://localhost:8000', isDark: false }));
  assert.doesNotMatch(html, /Owner research key/);
  assert.doesNotMatch(html, /type="password"/);
  assert.match(html, /Unlock private workspace above/);
  assert.match(html, /memory/);
  assert.ok(!html.includes('BUY_MORE'));
});
