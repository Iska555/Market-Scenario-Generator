import SimulationConfig from './components/SimulationConfig.jsx';
import Overview from './features/workspace/Overview.jsx';
import { PrivateWorkspaceProvider } from './features/workspace/PrivateWorkspace.jsx';
import { usePrivateSession } from './features/workspace/sessionContext.js';
import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { AlertTriangle } from 'lucide-react';

import PlatformShell from './components/PlatformShell.jsx';
import { apiBase, postScenario } from './api.js';
const PublicDemoPage = lazy(() => import('./features/public/PublicDemoPage.jsx'));
const ScenarioResults = lazy(() => import('./components/ScenarioResults.jsx'));
const ConstructionWorkspace = lazy(() => import('./features/construction/ConstructionWorkspace.jsx'));
const LedgerWorkspace = lazy(() => import('./features/ledger/LedgerWorkspace.jsx'));
const PerformanceWorkspace = lazy(() => import('./features/performance/PerformanceWorkspace.jsx'));
const StressWorkspace = lazy(() => import('./features/stress/StressWorkspace.jsx'));
const ThesisWorkspace = lazy(() => import('./features/thesis/ThesisWorkspace.jsx'));
const ValuationWorkspace = lazy(() => import('./features/valuation/ValuationWorkspace.jsx'));
import {
  buildPortfolioRequest,
  buildSingleRequest,
  DEFAULT_ASSUMPTIONS,
  normalizeWeightPercentages,
} from './scenarioContract.js';

const API_URL = apiBase(import.meta.env.DEV, import.meta.env.VITE_API_URL);
const loadingView = <p className="workspace-loading" role="status">Loading workspace…</p>;

export default function PortfolioPlatform() {
  const path = typeof window !== 'undefined' ? window.location.pathname.replace(/\/$/, '') : '';
  if (path === '/demo-preview') return <Suspense fallback={loadingView}><PublicDemoPage apiUrl={API_URL} /></Suspense>;
  if (path === '/demo' || path.startsWith('/demo/')) return <Suspense fallback={loadingView}><PublicDemoPage apiUrl={API_URL} published version={path.slice(6) || null} /></Suspense>;
  return <PrivatePortfolioPlatform />;
}

function PrivatePortfolioPlatform() {
  return <PrivateWorkspaceProvider apiUrl={API_URL}><SessionContents /></PrivateWorkspaceProvider>;
}

function SessionContents() {
  const { epoch } = usePrivateSession();
  const [activeTab, setActiveTab] = useState('overview');
  const [theme, setTheme] = useState('light');
  return <PortfolioPlatformContent key={epoch} activeTab={activeTab} setActiveTab={setActiveTab} theme={theme} setTheme={setTheme} />;
}

function PortfolioPlatformContent({ activeTab, setActiveTab, theme, setTheme }) {
  const [ticker, setTicker] = useState('');
  const [portfolioAssets, setPortfolioAssets] = useState([
    { ticker: '', weight: '' },
    { ticker: '', weight: '' },
  ]);
  const [singleAssumptions, setSingleAssumptions] = useState({ ...DEFAULT_ASSUMPTIONS });
  const [portfolioAssumptions, setPortfolioAssumptions] = useState({ ...DEFAULT_ASSUMPTIONS, model: 'gaussian' });
  const [singleResult, setSingleResult] = useState(null);
  const [portfolioResult, setPortfolioResult] = useState(null);
  const [loading, setLoading] = useState({ single: false, portfolio: false });
  const [errors, setErrors] = useState({ single: null, portfolio: null });
  const requests = useRef({});
  const error = errors[activeTab];
  const isDark = theme === 'dark';

  useEffect(() => { const current = requests.current; return () => Object.values(current).forEach(controller => controller.abort()); }, []);

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
    requests.current.single?.abort();
    const controller = new AbortController();
    requests.current.single = controller;
    setLoading((current) => ({ ...current, single: true }));
    setErrors((current) => ({ ...current, single: null }));
    try {
      const result = await postScenario(API_URL, '/api/simulate', buildSingleRequest(ticker, singleAssumptions), { signal: controller.signal });
      if (!controller.signal.aborted) setSingleResult(result);
    } catch (requestError) {
      if (!controller.signal.aborted) setErrors((current) => ({ ...current, single: requestError.message }));
    } finally {
      setLoading((current) => ({ ...current, single: false }));
    }
  };

  const runPortfolio = async () => {
    requests.current.portfolio?.abort();
    const controller = new AbortController();
    requests.current.portfolio = controller;
    setLoading((current) => ({ ...current, portfolio: true }));
    setErrors((current) => ({ ...current, portfolio: null }));
    try {
      const request = buildPortfolioRequest(portfolioAssets, portfolioAssumptions);
      const result = await postScenario(API_URL, '/api/simulate-portfolio', request, { signal: controller.signal });
      if (!controller.signal.aborted) setPortfolioResult(result);
    } catch (requestError) {
      if (!controller.signal.aborted) setErrors((current) => ({ ...current, portfolio: requestError.message }));
    } finally {
      setLoading((current) => ({ ...current, portfolio: false }));
    }
  };

  return (
    <PlatformShell
      activeWorkspace={activeTab}
      onNavigate={setActiveTab}
      isDark={isDark}
      onToggleTheme={() => setTheme((current) => current === 'light' ? 'dark' : 'light')}
    >
      <Suspense fallback={loadingView}>
        {activeTab === 'overview' ? <Overview apiUrl={API_URL} isDark={isDark} onNavigate={setActiveTab} /> : activeTab === 'ledger' ? <LedgerWorkspace apiUrl={API_URL} isDark={isDark} /> : activeTab === 'performance' ? <PerformanceWorkspace apiUrl={API_URL} isDark={isDark} /> : activeTab === 'construction' ? <ConstructionWorkspace apiUrl={API_URL} isDark={isDark} /> : activeTab === 'stress' ? <StressWorkspace apiUrl={API_URL} isDark={isDark} /> : activeTab === 'valuation' ? <ValuationWorkspace apiUrl={API_URL} isDark={isDark} /> : activeTab === 'thesis' ? <ThesisWorkspace apiUrl={API_URL} isDark={isDark} /> : activeTab === 'single' ? (
          <>
            <SimulationConfig
              key="single"
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
              key="portfolio"
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
      </Suspense>
    </PlatformShell>
  );
}
