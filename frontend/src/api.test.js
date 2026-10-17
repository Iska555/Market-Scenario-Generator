import assert from 'node:assert/strict';
import { test } from 'node:test';
import { setTimeout } from 'node:timers/promises';
import { apiBase, postScenario } from './api.js';

test('production stays same-origin even with a stale deployed API environment value', () => {
  assert.equal(apiBase(false, 'https://old-host.example'), '');
  assert.equal(apiBase(true, undefined), 'http://localhost:8000');
  assert.equal(apiBase(true, 'http://localhost:9000/'), 'http://localhost:9000');
});

test('public simulation submits without an owner key or authentication headers', async () => {
  let calls = 0;
  const fetcher = async (url, options) => {
    ++calls;
    assert.equal(url, '/api/simulate');
    assert.deepEqual(options.headers, { 'Content-Type': 'application/json' });
    return { ok: true, json: async () => ({ api_version: '3.0.0', statistics: {}, percentiles: {}, percentile_values: {} }) };
  };
  await postScenario('', '/api/simulate', {}, { fetcher });
  assert.equal(calls, 1);
});

test('network, unexpected access restriction, provider failure and timeout have actionable messages', async () => {
  await assert.rejects(postScenario('', '/api/simulate', {}, { fetcher: async () => { throw new TypeError('Failed to fetch'); } }), /Check your connection/);
  await assert.rejects(postScenario('', '/api/simulate', {}, { fetcher: async () => ({ ok: false, status: 401, json: async () => ({}) }) }), /misconfigured/);
  await assert.rejects(postScenario('', '/api/simulate', {}, { fetcher: async () => ({ ok: false, status: 503, json: async () => ({ detail: 'Price provider failed for TEST' }) }) }), /Price provider failed/);
  await assert.rejects(postScenario('', '/api/simulate', {}, { timeoutMs: 1, fetcher: async (_, { signal }) => { await setTimeout(10); signal.throwIfAborted(); } }), /timed out/);
});
