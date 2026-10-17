import assert from 'node:assert/strict';
import { test } from 'node:test';
import { setTimeout } from 'node:timers/promises';
import { apiBase, postScenario } from './api.js';

test('production stays same-origin even with a stale deployed API environment value', () => {
  assert.equal(apiBase(false, 'https://old-host.example'), '');
  assert.equal(apiBase(true, undefined), 'http://localhost:8000');
  assert.equal(apiBase(true, 'http://localhost:9000/'), 'http://localhost:9000');
});

test('locked simulation never submits a request; owner key stays in the header', async () => {
  let calls = 0;
  const fetcher = async (url, options) => {
    ++calls;
    assert.equal(url, '/api/simulate');
    assert.equal(options.headers['X-Research-Key'], 'test-owner');
    assert.ok(!options.body.includes('test-owner'));
    return { ok: true, json: async () => ({ api_version: '3.0.0', statistics: {}, percentiles: {}, percentile_values: {} }) };
  };
  await assert.rejects(postScenario('', '/api/simulate', {}, '', { fetcher }), /Unlock/);
  assert.equal(calls, 0);
  await postScenario('', '/api/simulate', {}, 'test-owner', { fetcher });
  assert.equal(calls, 1);
});

test('network, expired access, provider failure and timeout have actionable messages', async () => {
  await assert.rejects(postScenario('', '/api/simulate', {}, 'key', { fetcher: async () => { throw new TypeError('Failed to fetch'); } }), /Check your connection/);
  await assert.rejects(postScenario('', '/api/simulate', {}, 'key', { fetcher: async () => ({ ok: false, status: 401, json: async () => ({}) }) }), /owner key/);
  await assert.rejects(postScenario('', '/api/simulate', {}, 'key', { fetcher: async () => ({ ok: false, status: 503, json: async () => ({ detail: 'Price provider failed for TEST' }) }) }), /Price provider failed/);
  await assert.rejects(postScenario('', '/api/simulate', {}, 'key', { timeoutMs: 1, fetcher: async (_, { signal }) => { await setTimeout(10); signal.throwIfAborted(); } }), /timed out/);
});
