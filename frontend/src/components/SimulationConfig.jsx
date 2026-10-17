import { useState } from 'react';
import { Layers, Plus, RefreshCw, X } from 'lucide-react';

import {
  describeDriftModel,
  driftModelLabel,
  estimationWindowPreset,
  MODEL_OPTIONS,
  yearsForEstimationWindow,
} from '../scenarioContract.js';

const MAX_SIMULATION_CELLS = 2_000_000;

const panel = (isDark) => isDark
  ? 'bg-[#151e32] border-slate-700/60'
  : 'bg-white border-slate-200 shadow-xl shadow-slate-200/50';

const input = (isDark) => `w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition focus:ring-2 focus:ring-indigo-500/40 ${
  isDark ? 'bg-[#0f172a] border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
}`;

const muted = (isDark) => isDark ? 'text-slate-400' : 'text-slate-500';

export default function SimulationConfig({
  mode, ticker, setTicker, assets, setAssets, updateAsset, totalWeight,
  normalizeWeights, assumptions, setAssumptions, onRun, loading, isDark,
}) {
  const [customWindow, setCustomWindow] = useState(estimationWindowPreset(assumptions.years) === 'custom');
  const updateAssumption = (field, value) => setAssumptions((current) => ({ ...current, [field]: value }));
  const windowChoice = customWindow ? 'custom' : estimationWindowPreset(assumptions.years);
  const weightsValid = mode === 'single' || Math.abs(totalWeight - 100) <= 1e-8;
  const identifiersValid = mode === 'single'
    ? Boolean(ticker.trim())
    : assets.length >= 2 && assets.every((asset) => asset.ticker.trim());
  const simulationCells = Number(assumptions.horizon) * Number(assumptions.numPaths) * (mode === 'single' ? 1 : assets.length);
  const sizeValid = Number.isFinite(simulationCells) && simulationCells <= MAX_SIMULATION_CELLS;

  const selectWindow = (preset) => {
    setCustomWindow(preset === 'custom');
    updateAssumption('years', yearsForEstimationWindow(preset, assumptions.years));
  };

  return (
    <section className={`mb-8 rounded-3xl border p-5 sm:p-6 ${panel(isDark)}`}>
      <div className="mb-6">
        <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{mode === 'single' ? 'Single-asset scenario' : 'Portfolio scenario'}</h2>
        <p className={`mt-1 text-sm ${muted(isDark)}`}>Set assets and assumptions. Prices are downloaded on the first run and cached for one hour.</p>
      </div>

      {mode === 'single' ? (
        <Field label="Ticker" isDark={isDark}>
          <input value={ticker} placeholder="e.g. AAPL" autoComplete="off" spellCheck={false} onChange={(event) => setTicker(event.target.value.toUpperCase())} className={input(isDark)} />
        </Field>
      ) : (
        <PortfolioAssets assets={assets} setAssets={setAssets} updateAsset={updateAsset} totalWeight={totalWeight} normalizeWeights={normalizeWeights} isDark={isDark} />
      )}

      <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <Field label="Estimation window" isDark={isDark}>
            <select value={windowChoice} onChange={(event) => selectWindow(event.target.value)} className={input(isDark)}>
              <option value="recent">Recent · 3 years</option>
              <option value="medium">Medium · 5 years</option>
              <option value="long">Long · 10 years</option>
              <option value="custom">Custom</option>
            </select>
          </Field>
          {windowChoice === 'custom' && <div className="mt-2"><NumberField label="Custom history (years)" value={assumptions.years} onChange={(value) => updateAssumption('years', value)} min="1" max="10" isDark={isDark} /></div>}
        </div>
        <NumberField label="Horizon (modeled periods)" value={assumptions.horizon} onChange={(value) => updateAssumption('horizon', value)} min="1" max="1000" isDark={isDark} />
        <Field label="Forward return assumption" isDark={isDark}>
          <select value={assumptions.driftModel} onChange={(event) => updateAssumption('driftModel', event.target.value)} className={input(isDark)}>
            <option value="zero_log_drift">{driftModelLabel('zero_log_drift')}</option>
            <option value="historical_diagnostic">{driftModelLabel('historical_diagnostic')}</option>
          </select>
        </Field>
        <NumberField label="Initial value" value={assumptions.initialValue} onChange={(value) => updateAssumption('initialValue', value)} min="0.01" max="1000000000000" step="0.01" isDark={isDark} />
        <Field label="Valuation currency" isDark={isDark}>
          <select value={assumptions.currency} onChange={(event) => updateAssumption('currency', event.target.value)} className={input(isDark)}><option value="USD">USD</option></select>
        </Field>
      </div>

      <div className="mt-6">
        <h3 className={`mb-3 text-xs font-bold uppercase tracking-wider ${muted(isDark)}`}>Scenario family</h3>
        <div className={`grid gap-3 ${mode === 'single' ? 'sm:grid-cols-3' : 'sm:grid-cols-2'}`}>
          {MODEL_OPTIONS.filter((option) => mode === 'single' || option.value !== 'ewma').map((option) => (
            <button type="button" key={option.value} aria-pressed={assumptions.model === option.value} onClick={() => updateAssumption('model', option.value)}
              className={`rounded-xl border p-4 text-left transition ${assumptions.model === option.value
                ? isDark ? 'border-indigo-400 bg-indigo-400/10 text-white' : 'border-indigo-600 bg-indigo-50 text-indigo-950'
                : isDark ? 'border-slate-700 bg-[#0f172a] text-slate-300 hover:border-slate-500' : 'border-slate-200 bg-white text-slate-700 hover:border-slate-400'}`}>
              <span className="block font-bold">{mode === 'single' ? option.singleLabel : option.label}</span>
              <span className="mt-1 block text-xs opacity-80">{mode === 'single' && option.singleDescription ? option.singleDescription : option.description}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="scenario-summary"><span>{assumptions.numPaths} paths · {assumptions.horizon} periods · {assumptions.currency}</span>{mode === 'portfolio' && <span>{assumptions.rebalance === 'buy_and_hold' ? 'Weight policy: Buy and hold' : 'Weight policy: Daily rebalancing'}</span>}<span>Conditional scenarios, not forecasts</span></div>

      <details className={`mt-6 rounded-2xl border p-4 ${isDark ? 'border-slate-700 bg-[#0f172a]/60' : 'border-slate-200 bg-slate-50'}`}>
        <summary className={`cursor-pointer text-sm font-semibold ${isDark ? 'text-slate-100' : 'text-slate-800'}`}>Advanced settings</summary>
        <p className={`mt-4 text-sm ${muted(isDark)}`}>{describeDriftModel(assumptions.driftModel)} Saved valuation estimates are not applied automatically. Values use the selected currency without FX conversion; annualization uses {assumptions.periodsPerYear} periods per year.</p>
        <p className={`mt-2 text-xs ${muted(isDark)}`}>Shorter estimation windows respond to recent changes; longer windows include more observations and older market conditions.</p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <NumberField label="Simulation paths" value={assumptions.numPaths} onChange={(value) => updateAssumption('numPaths', value)} min="100" max="5000" isDark={isDark} />
          <NumberField label="Random seed" value={assumptions.randomSeed} onChange={(value) => updateAssumption('randomSeed', value)} min="0" max="4294967295" isDark={isDark} />
          <NumberField label="Periods per year" value={assumptions.periodsPerYear} onChange={(value) => updateAssumption('periodsPerYear', value)} min="1" max="366" isDark={isDark} />
          <NumberField label="Confidence (0.95 = 95%)" value={assumptions.confidence} onChange={(value) => updateAssumption('confidence', value)} min="0.001" max="0.999" step="0.005" isDark={isDark} />
          <NumberField label="Annual effective risk-free rate (0.04 = 4%)" value={assumptions.riskFreeRate} onChange={(value) => updateAssumption('riskFreeRate', value)} min="-0.999" max="1" step="0.001" isDark={isDark} />
          {mode === 'portfolio' && (
            <>
              <Field label="Covariance estimator" isDark={isDark}>
                <select value={assumptions.covarianceEstimator} onChange={(event) => updateAssumption('covarianceEstimator', event.target.value)} className={input(isDark)}>
                  <option value="ledoit_wolf">Ledoit-Wolf</option><option value="sample">Sample covariance</option>
                </select>
              </Field>
              <Field label="Rebalancing" isDark={isDark}>
                <select value={assumptions.rebalance} onChange={(event) => updateAssumption('rebalance', event.target.value)} className={input(isDark)}>
                  <option value="buy_and_hold">Buy and hold</option><option value="daily">Daily</option>
                </select>
              </Field>
            </>
          )}
          {assumptions.model === 'gmm' && (
            <>
              <NumberField label="GMM components" value={assumptions.gmmComponents} onChange={(value) => updateAssumption('gmmComponents', value)} min="1" max="5" isDark={isDark} />
              <NumberField label="GMM covariance regularizer" value={assumptions.gmmRegCovar} onChange={(value) => updateAssumption('gmmRegCovar', value)} min="0.000000001" max="0.01" step="0.000001" isDark={isDark} />
            </>
          )}
          {mode === 'single' && assumptions.model === 'ewma' && <NumberField label="EWMA lambda" value={assumptions.ewmaLambda} onChange={(value) => updateAssumption('ewmaLambda', value)} min="0.0001" max="0.9999" step="0.01" isDark={isDark} />}
        </div>
        {mode === 'portfolio' && <p className={`mt-4 text-xs ${muted(isDark)}`}>Covariance estimates how assets move together. Ledoit-Wolf is the recommended default: it shrinks noisy historical covariance estimates toward a more stable structure. Sample covariance uses the raw sample. Buy and hold leaves holdings unchanged, so weights drift as assets gain or lose value; daily rebalancing resets target weights each modeled period without costs.</p>}
        {assumptions.model === 'gmm' && <p className={`mt-2 text-xs ${muted(isDark)}`}>GMM components count fitted statistical regimes. The regularizer stabilizes their covariance estimates; neither parameter identifies an economic regime.</p>}
        {mode === 'single' && assumptions.model === 'ewma' && <p className={`mt-2 text-xs ${muted(isDark)}`}>EWMA lambda controls how slowly weight on older volatility observations decays; a lower value responds more quickly to recent changes.</p>}
        <p className={`mt-4 text-xs ${muted(isDark)}`}>Request capacity: {Number.isFinite(simulationCells) ? simulationCells.toLocaleString() : 'invalid'} of {MAX_SIMULATION_CELLS.toLocaleString()} path × horizon × asset cells.</p>
      </details>

      <button type="button" onClick={onRun} disabled={loading || !weightsValid || !identifiersValid || !sizeValid}
        className={`mt-6 flex w-full items-center justify-center gap-3 rounded-xl px-8 py-4 font-bold shadow-lg disabled:cursor-not-allowed disabled:opacity-50 ${isDark ? 'bg-white text-slate-900' : 'bg-slate-900 text-white'}`}>
        {loading ? <RefreshCw className="h-5 w-5 animate-spin" /> : <Layers className="h-5 w-5" />}
        {loading ? 'Running conditional scenarios…' : 'Run conditional scenarios'}
      </button>
      {loading && <p className="mt-3 text-sm" role="status">Loading market history and calculating scenarios. First runs take longer; repeat runs reuse cached prices.</p>}
      {!weightsValid && <p className="mt-2 text-sm text-red-500">Portfolio weights must total 100%.</p>}
      {!identifiersValid && <p className="mt-2 text-sm text-red-500">Enter {mode === 'single' ? 'a ticker' : 'at least two asset tickers'}.</p>}
      {!sizeValid && <p className="mt-2 text-sm text-red-500">Reduce paths, horizon, or asset count to stay within 2,000,000 simulation cells. Current request: {Number.isFinite(simulationCells) ? simulationCells.toLocaleString() : 'invalid'} cells. See Advanced settings.</p>}
    </section>
  );
}

export function PortfolioAssets({ assets, setAssets, updateAsset, totalWeight, normalizeWeights, isDark }) {
  return (
    <div>
      <div className="space-y-3">
        {assets.map((asset, index) => (
          <div key={index} className="grid grid-cols-[minmax(0,1fr)_5.5rem_auto] gap-3 sm:grid-cols-[minmax(0,1fr)_9rem_auto]">
            <input aria-label={`Asset ${index + 1} ticker`} value={asset.ticker} onChange={(event) => updateAsset(index, 'ticker', event.target.value.toUpperCase())} className={input(isDark)} placeholder="Ticker" />
            <div className="relative">
              <input aria-label={`Asset ${index + 1} weight`} type="number" min="0" max="100" value={asset.weight} onChange={(event) => updateAsset(index, 'weight', event.target.value)} className={`${input(isDark)} pr-8`} />
              <span className={`absolute right-3 top-2.5 text-sm ${muted(isDark)}`}>%</span>
            </div>
            <button type="button" aria-label={`Remove asset ${index + 1}`} disabled={assets.length <= 2} onClick={() => setAssets((current) => current.filter((_, assetIndex) => assetIndex !== index))} className={`rounded-xl p-3 disabled:opacity-30 ${isDark ? 'text-slate-400 hover:bg-slate-800' : 'text-slate-500 hover:bg-slate-100'}`}><X className="h-4 w-4" /></button>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <button type="button" disabled={assets.length >= 10} onClick={() => setAssets((current) => [...current, { ticker: '', weight: '' }])} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-40 ${isDark ? 'bg-slate-800 text-slate-200' : 'bg-slate-100 text-slate-700'}`}><Plus className="h-4 w-4" /> Add asset</button>
        <div className="flex items-center gap-3">
          <span className={`font-mono font-bold ${Math.abs(totalWeight - 100) <= 1e-8 ? 'text-emerald-500' : 'text-red-500'}`}>{totalWeight.toFixed(2)}%</span>
          <button type="button" onClick={normalizeWeights} className={`rounded-lg px-3 py-2 text-xs font-bold ${isDark ? 'bg-slate-800 text-slate-300' : 'border border-slate-300 bg-white text-slate-700'}`}>Normalize</button>
        </div>
      </div>
    </div>
  );
}

export function Field({ label, isDark, children }) {
  return <label className="block"><span className={`mb-2 block text-xs font-bold uppercase tracking-wider ${muted(isDark)}`}>{label}</span>{children}</label>;
}

export function NumberField({ label, value, onChange, isDark, ...props }) {
  return <Field label={label} isDark={isDark}><input type="number" value={value} onChange={(event) => onChange(event.target.value)} className={input(isDark)} {...props} /></Field>;
}
