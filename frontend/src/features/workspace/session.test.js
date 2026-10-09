import assert from 'node:assert/strict';
import { test } from 'node:test';
import { setImmediate } from 'node:timers';
import { createPrivateSession } from './session.js';
import { createWorkspace } from '../thesis/thesis.js';
import { createConstructionWorkspace } from '../construction/construction.js';
import { createValuationWorkspace } from '../valuation/valuation.js';
import { createLedgerWorkspace } from '../ledger/ledger.js';
import { createStressWorkspace } from '../stress/stress.js';

test('one validated session connects multiple modules and locking clears their private state', async () => {
  const received = [];
  const request = async (path, options, key) => { received.push(key); return path.includes('securities') ? [{ id: 'private-equity' }] : []; };
  const thesis = createWorkspace(request);
  const construction = createConstructionWorkspace(request);
  let validations = 0;
  const session = createPrivateSession(async key => { assert.equal(key, 'private-secret'); validations++; });
  session.attach(thesis);
  await session.unlock('private-secret');
  session.attach(construction);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(validations, 1);
  assert.equal(thesis.getSnapshot().connected, true);
  assert.equal(construction.getSnapshot().connected, true);
  assert.ok(received.every(key => key === 'private-secret'));
  assert.ok(!JSON.stringify(session.getSnapshot()).includes('private-secret'));
  thesis.newThesis();
  thesis.editThesis('notes', 'private draft');
  session.lock();
  assert.equal(session.getSnapshot().connected, false);
  assert.equal(thesis.getSnapshot().draft, null);
  assert.deepEqual(construction.getSnapshot().securities, []);
});

test('lock cancels pending unlock and late module responses', async () => {
  let finish;
  const session = createPrivateSession(() => new Promise(resolve => { finish = resolve; }));
  const pending = session.unlock('secret');
  session.lock(); finish(); await pending;
  assert.equal(session.getSnapshot().connected, false);
  let respond;
  const controller = createConstructionWorkspace(() => new Promise(resolve => { respond = resolve; }));
  const ready = createPrivateSession(async () => {});
  ready.attach(controller); await ready.unlock('secret');
  ready.lock(); respond([]); await new Promise(resolve => setImmediate(resolve));
  assert.equal(controller.getSnapshot().connected, false);
  assert.deepEqual(controller.getSnapshot().securities, []);
});

test('secret never enters browser persistence and failed unlock never exposes error payloads', async () => {
  const forbidden = () => { throw new Error('durable storage access'); };
  for (const name of ['localStorage', 'sessionStorage', 'indexedDB']) Object.defineProperty(globalThis, name, { configurable: true, get: forbidden });
  try {
    const session = createPrivateSession(async () => {});
    await session.unlock('hidden-secret'); session.lock();
    const failed = createPrivateSession(async () => { throw Object.assign(new Error('hidden-secret'), { status: 401 }); });
    await failed.unlock('hidden-secret');
    assert.equal(failed.getSnapshot().connected, false);
    assert.match(failed.getSnapshot().error, /not accepted/);
    assert.ok(!JSON.stringify(failed.getSnapshot()).includes('hidden-secret'));
  } finally { for (const name of ['localStorage', 'sessionStorage', 'indexedDB']) delete globalThis[name]; }
});

test('detaching a child clears its state but preserves the shared connection', async () => {
  const session = createPrivateSession(async () => {});
  const controller = createConstructionWorkspace(async () => []);
  await session.unlock('secret');
  const detach = session.attach(controller);
  await new Promise(resolve => setImmediate(resolve));
  detach();
  assert.equal(controller.getSnapshot().connected, false);
  assert.equal(session.getSnapshot().connected, true);
});

test('unlocking a locked workspace does not remount the owner workflow or key form', async () => {
  const session = createPrivateSession(async () => { throw Object.assign(new Error('rejected'), { status: 401 }); });
  const before = session.getSnapshot().epoch;
  await session.unlock('incorrect');
  assert.equal(session.getSnapshot().epoch, before);
  session.lock();
  assert.equal(session.getSnapshot().epoch, before + 1);
});

test('all private modules share one connection and clear on the global lock', async () => {
  const calls = [];
  const request = async (path, options, key) => { calls.push(key); return []; };
  const controllers = [createWorkspace, createConstructionWorkspace, createValuationWorkspace, createLedgerWorkspace, createStressWorkspace].map(create => create(request));
  const session = createPrivateSession(async () => {});
  controllers.forEach(controller => session.attach(controller));
  await session.unlock('one-session-key');
  await new Promise(resolve => setImmediate(resolve));
  controllers.forEach(controller => assert.equal(controller.getSnapshot().connected, true));
  assert.ok(calls.every(key => key === 'one-session-key'));
  session.lock();
  controllers.forEach(controller => assert.equal(controller.getSnapshot().connected, false));
});
