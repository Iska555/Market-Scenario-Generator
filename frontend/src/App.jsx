import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Briefcase,
  Info,
  Layers,
  Moon,
  Plus,
  RefreshCw,
  Sun,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react';

import ScenarioResults from './components/ScenarioResults.jsx';
import {
  assertV3Response,
  buildPortfolioRequest,
  buildSingleRequest,
  DEFAULT_ASSUMPTIONS,
  describeDriftModel,
  MODEL_OPTIONS,
  normalizeWeightPercentages,
} from './scenarioContract.js';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const MAX_SIMULATION_CELLS = 2_000_000;

const panel = (isDark) => isDark
  ? 'bg-[#151e32] border-slate-700/60'
  : 'bg-white border-slate-200 shadow-xl shadow-slate-200/50';

const input = (isDark) => `w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition focus:ring-2 focus:ring-indigo-500/40 ${
  isDark ? 'bg-[#0f172a] border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
}`;

function parseApiError(detail, fallback) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg || JSON.stringify(item)).join('; ');
  return fallback;
}

async function postScenario(path, body) {
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(parseApiError(errorBody.detail, 'Scenario simulation failed.'));
  }
  return assertV3Response(await response.json());
}

export default function StochasticMarketSimulator() {
  const [theme, setTheme] = useState('light');
  const [activeTab, setActiveTab] = useState('single');
  const [ticker, setTicker] = useState('SPY');
  const [portfolioAssets, setPortfolioAssets] = useState([
    { ticker: 'SPY', weight: '60' },
    { ticker: 'TLT', weight: '40' },
  ]);
  const [singleAssumptions, setSingleAssumptions] = useState({ ...DEFAULT_ASSUMPTIONS });
  const [portfolioAssumptions, setPortfolioAssumptions] = useState({ ...DEFAULT_ASSUMPTIONS, model: 'gaussian' });
  const [singleResult, setSingleResult] = useState(null);
  const [portfolioResult, setPortfolioResult] = useState(null);
  const [loading, setLoading] = useState({ single: false, portfolio: false });
  const [errors, setErrors] = useState({ single: null, portfolio: null });
  const error = errors[activeTab];
  const isDark = theme === 'dark';

  useEffect(() => {
    fetch(`${API_URL}/ping`).catch(() => {});
  }, []);

  const totalWeight = portfolioAssets.reduce((sum, asset) => sum + (Number(asset.weight) || 0), 0);

  const updateAsset = (index, field, value) => {
    setPortfolioAssets((current) => current.map((asset, assetIndex) => (
      assetIndex === index ? { ...asset, [field]: value } : asset
    )));
  };

  const normalizeWeights = () => {
    if (totalWeight === 0) return;
    setPortfolioAssets((current) => normalizeWeightPercentages(current));
  };

  const runSingle = async () => {
    setLoading((current) => ({ ...current, single: true }));
    setErrors((current) => ({ ...current, single: null }));
    try {
      setSingleResult(await postScenario('/api/simulate', buildSingleRequest(ticker, singleAssumptions)));
    } catch (requestError) {
      setErrors((current) => ({ ...current, single: requestError.message }));
    } finally {
      setLoading((current) => ({ ...current, single: false }));
    }
  };

  const runPortfolio = async () => {
    setLoading((current) => ({ ...current, portfolio: true }));
    setErrors((current) => ({ ...current, portfolio: null }));
    try {
      const request = buildPortfolioRequest(portfolioAssets, portfolioAssumptions);
      setPortfolioResult(await postScenario('/api/simulate-portfolio', request));
    } catch (requestError) {
      setErrors((current) => ({ ...current, portfolio: requestError.message }));
    } finally {
      setLoading((current) => ({ ...current, portfolio: false }));
    }
  };

  return (
    <div className={`min-h-screen transition-colors ${isDark ? 'bg-[#0B1120]' : 'bg-slate-50'}`}>
      <header className={`sticky top-0 z-50 border-b backdrop-blur-xl ${isDark ? 'border-slate-800 bg-[#0B1120]/90' : 'border-slate-200 bg-white/90'}`}>
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 md:px-8">
          <div className="flex items-center gap-4">
            <div className={`rounded-xl p-2.5 shadow-lg ${isDark ? 'bg-white' : 'bg-blue-600'}`}>
              <TrendingUp className={`h-6 w-6 ${isDark ? 'text-slate-900' : 'text-white'}`} />
            </div>
            <div>
              <h1 className={`text-xl font-bold ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>Portfolio Simulations</h1>
              <p className={`mt-0.5 text-xs font-medium uppercase tracking-wide ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Risk &amp; Scenario Lab</p>
            </div>
          </div>
          <button
            type="button"
            aria-label="Toggle color theme"
            onClick={() => setTheme((current) => current === 'light' ? 'dark' : 'light')}
            className={`rounded-full border p-2 ${isDark ? 'border-slate-700 bg-slate-800 text-yellow-400' : 'border-slate-200 bg-white text-slate-600'}`}
          >
            {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-8 md:px-8">
        <div className={`mb-6 rounded-2xl border p-5 ${isDark ? 'border-indigo-400/20 bg-indigo-400/10 text-indigo-100' : 'border-indigo-200 bg-indigo-50 text-indigo-950'}`}>
          <div className="flex gap-3">
            <Info className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="font-semibold">These are conditional simulations, not return forecasts.</p>
              <p className={`mt-1 text-sm ${isDark ? 'text-indigo-200/80' : 'text-indigo-800'}`}>
                Historical data estimates distribution and risk inputs. Each result remains tied to the assumptions returned by the API.
              </p>
            </div>
          </div>
        </div>

        <div className="mb-8 flex gap-2">
          <TabButton active={activeTab === 'single'} onClick={() => setActiveTab('single')} isDark={isDark} icon={Zap}>Single Asset</TabButton>
          <TabButton active={activeTab === 'portfolio'} onClick={() => setActiveTab('portfolio')} isDark={isDark} icon={Briefcase}>Portfolio</TabButton>
        </div>

        {activeTab === 'single' ? (
          <>
            <SimulationConfig
              mode="single"
              ticker={ticker}
              setTicker={setTicker}
              assumptions={singleAssumptions}
              setAssumptions={setSingleAssumptions}
              onRun={runSingle}
              loading={loading.single}
              isDark={isDark}
            />
            {singleResult && <ScenarioResults result={singleResult} mode="single" isDark={isDark} />}
          </>
        ) : (
          <>
            <SimulationConfig
              mode="portfolio"
              assets={portfolioAssets}
              setAssets={setPortfolioAssets}
              updateAsset={updateAsset}
              totalWeight={totalWeight}
              normalizeWeights={normalizeWeights}
              assumptions={portfolioAssumptions}
              setAssumptions={setPortfolioAssumptions}
              onRun={runPortfolio}
              loading={loading.portfolio}
              isDark={isDark}
            />
            {portfolioResult && <ScenarioResults result={portfolioResult} mode="portfolio" isDark={isDark} />}
          </>
        )}

        {error && (
          <div role="alert" className="mt-6 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-500">
            <AlertTriangle className="h-4 w-4 shrink-0" /> {error}
          </div>
        )}
      </main>
    </div>
  );
}

function TabButton({ active, onClick, isDark, icon, children }) {
  const IconComponent = icon;
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition ${active
        ? isDark ? 'bg-white text-slate-900' : 'bg-slate-900 text-white'
        : isDark ? 'text-slate-400 hover:bg-slate-800' : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-100'
      }`}
    >
      <IconComponent className="h-4 w-4" /> {children}
    </button>
  );
}

function SimulationConfig({
  mode,
  ticker,
  setTicker,
  assets,
  setAssets,
  updateAsset,
  totalWeight,
  normalizeWeights,
  assumptions,
  setAssumptions,
  onRun,
  loading,
  isDark,
}) {
  const updateAssumption = (field, value) => setAssumptions((current) => ({ ...current, [field]: value }));
  const weightsValid = mode === 'single' || Math.abs(totalWeight - 100) <= 1e-8;
  const identifiersValid = mode === 'single'
    ? Boolean(ticker.trim())
    : assets.length >= 2 && assets.every((asset) => asset.ticker.trim());
  const simulationCells = Number(assumptions.horizon) * Number(assumptions.numPaths) * (mode === 'single' ? 1 : assets.length);
  const sizeValid = Number.isFinite(simulationCells) && simulationCells <= MAX_SIMULATION_CELLS;

  return (
    <section className={`mb-8 rounded-3xl border p-6 ${panel(isDark)}`}>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{mode === 'single' ? 'Single-asset scenario' : 'Portfolio scenario'}</h2>
          <p className={`mt-1 text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Set the assumptions explicitly before running the simulation.</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-bold ${isDark ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-600'}`}>API v3</span>
      </div>

      {mode === 'single' ? (
        <Field label="Ticker" isDark={isDark}>
          <input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} className={input(isDark)} />
        </Field>
      ) : (
        <PortfolioAssets assets={assets} setAssets={setAssets} updateAsset={updateAsset} totalWeight={totalWeight} normalizeWeights={normalizeWeights} isDark={isDark} />
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <NumberField label="History (years)" value={assumptions.years} onChange={(value) => updateAssumption('years', value)} min="1" max="10" isDark={isDark} />
        <NumberField label="Horizon (modeled periods)" value={assumptions.horizon} onChange={(value) => updateAssumption('horizon', value)} min="1" max="1000" isDark={isDark} />
        <NumberField label="Simulation paths" value={assumptions.numPaths} onChange={(value) => updateAssumption('numPaths', value)} min="100" max="5000" isDark={isDark} />
        <NumberField label="Random seed" value={assumptions.randomSeed} onChange={(value) => updateAssumption('randomSeed', value)} min="0" max="4294967295" isDark={isDark} />
        <NumberField label="Initial value" value={assumptions.initialValue} onChange={(value) => updateAssumption('initialValue', value)} min="0.01" max="1000000000000" step="0.01" isDark={isDark} />
        <Field label="Currency denomination" isDark={isDark}>
          <select value={assumptions.currency} onChange={(event) => updateAssumption('currency', event.target.value)} className={input(isDark)}><option value="USD">USD</option></select>
        </Field>
        <NumberField label="Periods per year" value={assumptions.periodsPerYear} onChange={(value) => updateAssumption('periodsPerYear', value)} min="1" max="366" isDark={isDark} />
        <NumberField label="Confidence (0.95 = 95%)" value={assumptions.confidence} onChange={(value) => updateAssumption('confidence', value)} min="0.001" max="0.999" step="0.005" isDark={isDark} />
        <NumberField label="Annual effective risk-free rate (0.04 = 4%)" value={assumptions.riskFreeRate} onChange={(value) => updateAssumption('riskFreeRate', value)} min="-0.999" max="1" step="0.001" isDark={isDark} />
        <Field label="Drift model" isDark={isDark}>
          <select value={assumptions.driftModel} onChange={(event) => updateAssumption('driftModel', event.target.value)} className={input(isDark)}>
            <option value="zero_log_drift">Zero log drift</option>
            <option value="historical_diagnostic">Historical diagnostic</option>
          </select>
        </Field>
        <Field label="Covariance estimator" isDark={isDark}>
          <select value={assumptions.covarianceEstimator} onChange={(event) => updateAssumption('covarianceEstimator', event.target.value)} className={input(isDark)}>
            <option value="ledoit_wolf">Ledoit-Wolf</option><option value="sample">Sample covariance</option>
          </select>
        </Field>
        <Field label="Rebalancing" isDark={isDark}>
          <select value={assumptions.rebalance} onChange={(event) => updateAssumption('rebalance', event.target.value)} className={input(isDark)}>
            <option value="daily">Daily</option><option value="buy_and_hold">Buy and hold</option>
          </select>
        </Field>
      </div>

      <div className="mt-6">
        <label className={`mb-3 block text-xs font-bold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Return model</label>
        <div className={`grid gap-3 ${mode === 'single' ? 'sm:grid-cols-3' : 'sm:grid-cols-2'}`}>
          {MODEL_OPTIONS.filter((option) => mode === 'single' || option.value !== 'ewma').map((option) => (
            <button
              type="button"
              key={option.value}
              onClick={() => updateAssumption('model', option.value)}
              className={`rounded-xl border p-4 text-left ${assumptions.model === option.value
                ? isDark ? 'border-indigo-400 bg-indigo-400/10 text-white' : 'border-indigo-600 bg-indigo-50 text-indigo-950'
                : isDark ? 'border-slate-700 bg-[#0f172a] text-slate-400' : 'border-slate-200 bg-white text-slate-600'
              }`}
            >
              <span className="block font-bold">{option.label}</span><span className="mt-1 block text-xs opacity-75">{option.description}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        {assumptions.model === 'gmm' && (
          <>
            <NumberField label="GMM components" value={assumptions.gmmComponents} onChange={(value) => updateAssumption('gmmComponents', value)} min="1" max="5" isDark={isDark} />
            <NumberField label="GMM covariance regularizer" value={assumptions.gmmRegCovar} onChange={(value) => updateAssumption('gmmRegCovar', value)} min="0.000000001" max="0.01" step="0.000001" isDark={isDark} />
          </>
        )}
        {assumptions.model === 'ewma' && <NumberField label="EWMA lambda" value={assumptions.ewmaLambda} onChange={(value) => updateAssumption('ewmaLambda', value)} min="0.0001" max="0.9999" step="0.01" isDark={isDark} />}
      </div>

      <div className={`mt-5 rounded-xl p-4 text-sm ${isDark ? 'bg-slate-900 text-slate-300' : 'bg-slate-100 text-slate-700'}`}>
        <p>{describeDriftModel(assumptions.driftModel)}</p>
        <p className="mt-1">Currency is the portfolio valuation denomination. The simulation performs no foreign-exchange conversion.</p>
        <p className="mt-1">Request size: {Number.isFinite(simulationCells) ? simulationCells.toLocaleString() : 'invalid'} of {MAX_SIMULATION_CELLS.toLocaleString()} maximum path × horizon × asset cells.</p>
      </div>

      <button
        type="button"
        onClick={onRun}
        disabled={loading || !weightsValid || !identifiersValid || !sizeValid}
        className={`mt-6 flex w-full items-center justify-center gap-3 rounded-xl px-8 py-4 font-bold shadow-lg disabled:cursor-not-allowed disabled:opacity-50 ${isDark ? 'bg-white text-slate-900' : 'bg-slate-900 text-white'}`}
      >
        {loading ? <RefreshCw className="h-5 w-5 animate-spin" /> : <Layers className="h-5 w-5" />}
        {loading ? 'Running conditional scenarios…' : 'Run conditional scenarios'}
      </button>
      {!weightsValid && <p className="mt-2 text-sm text-red-500">Portfolio weights must total 100%.</p>}
      {!sizeValid && <p className="mt-2 text-sm text-red-500">Reduce paths, horizon, or asset count to stay within 2,000,000 simulation cells.</p>}
    </section>
  );
}

function PortfolioAssets({ assets, setAssets, updateAsset, totalWeight, normalizeWeights, isDark }) {
  return (
    <div>
      <div className="space-y-3">
        {assets.map((asset, index) => (
          <div key={index} className="grid grid-cols-[1fr_9rem_auto] gap-3">
            <input aria-label={`Asset ${index + 1} ticker`} value={asset.ticker} onChange={(event) => updateAsset(index, 'ticker', event.target.value.toUpperCase())} className={input(isDark)} placeholder="Ticker" />
            <div className="relative">
              <input aria-label={`Asset ${index + 1} weight`} type="number" min="0" max="100" value={asset.weight} onChange={(event) => updateAsset(index, 'weight', event.target.value)} className={`${input(isDark)} pr-8`} />
              <span className={`absolute right-3 top-2.5 text-sm ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>%</span>
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

function Field({ label, isDark, children }) {
  return <label className="block"><span className={`mb-2 block text-xs font-bold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{label}</span>{children}</label>;
}

function NumberField({ label, value, onChange, isDark, ...props }) {
  return <Field label={label} isDark={isDark}><input type="number" value={value} onChange={(event) => onChange(event.target.value)} className={input(isDark)} {...props} /></Field>;
}
