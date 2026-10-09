import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

let server;
let PlatformShell;
before(async () => {
  server = await createServer({ root: fileURLToPath(new URL('../..', import.meta.url)), appType: 'custom', configLoader: 'native', logLevel: 'silent', server: { middlewareMode: true } });
  ({ default: PlatformShell } = await server.ssrLoadModule('/src/components/PlatformShell.jsx'));
});
after(async () => { await server?.close(); });

const render = (activeWorkspace, isDark = false) => renderToStaticMarkup(React.createElement(PlatformShell, {
  activeWorkspace, isDark, onNavigate: () => {}, onToggleTheme: () => {},
}, React.createElement('section', { 'aria-label': 'Current workspace' }, 'Workspace contents')));

test('navigation identifies exactly one current workspace and separates all nine destinations', () => {
  for (const activeWorkspace of ['overview', 'ledger', 'construction', 'thesis', 'valuation', 'single', 'portfolio', 'stress', 'performance']) {
    const html = render(activeWorkspace);
    assert.equal((html.match(/aria-current="page"/g) || []).length, 1);
    assert.match(html, new RegExp(`data-workspace="${activeWorkspace}"[^>]*aria-current="page"`));
    for (const label of ['Ledger', 'Construction', 'Thesis', 'Valuation', 'Single-asset Risk Lab', 'Portfolio Risk Lab', 'Historical &amp; shocks', 'Performance']) assert.ok(html.includes(label), label);
    assert.match(html, /aria-label="Workspace navigation"/);
  }
});

test('workspace content has a keyboard skip destination and risk context follows navigation', () => {
  const html = render('single');
  assert.match(html, /href="#workspace-content"/);
  assert.match(html, /<main[^>]*id="workspace-content"[^>]*tabindex="-1"/);
  assert.match(html, /conditional scenarios/);
  assert.match(html, /Workspace contents/);
  assert.doesNotMatch(render('construction'), /<h1[^>]*>Single-asset/);
});

test('theme control announces the action for the current theme', () => {
  assert.match(render('construction'), /aria-label="Switch to dark theme"/);
  assert.match(render('construction', true), /aria-label="Switch to light theme"/);
});

test('current product branding and Overview navigation are visible', () => {
  const html = render('overview');
  assert.match(html, /Investment Management Workspace/);
  assert.match(html, /Overview/);
  assert.doesNotMatch(html, /Portfolio Simulations/);
});
