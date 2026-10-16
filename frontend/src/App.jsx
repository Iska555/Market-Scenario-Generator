import SimulationConfig from './components/SimulationConfig.jsx';
import Overview from './features/workspace/Overview.jsx';
import PublicDemoPage from './features/public/PublicDemoPage.jsx';
import { PrivateWorkspaceProvider } from './features/workspace/PrivateWorkspace.jsx';
import { usePrivateSession } from './features/workspace/sessionContext.js';
import { useEffect, useState } from 'react';
import { AlertTriangle } from 'lucide-react';

import ScenarioResults from './components/ScenarioResults.jsx';
import PlatformShell from './components/PlatformShell.jsx';
import ConstructionWorkspace from './features/construction/ConstructionWorkspace.jsx';
import LedgerWorkspace from './features/ledger/LedgerWorkspace.jsx';
import PerformanceWorkspace from './features/performance/PerformanceWorkspace.jsx';
import StressWorkspace from './features/stress/StressWorkspace.jsx';
import ThesisWorkspace from './features/thesis/ThesisWorkspace.jsx';
import ValuationWorkspace from './features/valuation/ValuationWorkspace.jsx';
import {
  assertV3Response,
  buildPortfolioRequest,
  buildSingleRequest,
  DEFAULT_ASSUMPTIONS,
  normalizeWeightPercentages,
} from './scenarioContract.js';

const API_URL = import.meta.env.VITE_API_URL?.replace(/\/$/, '') ?? 'http://localhost:8000';
function parseApiError(detail, fallback) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg || JSON.stringify(item)).join('; ');
  return fallback;
}

async function postScenario(path, body, key = '') {
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(key ? { 'X-Research-Key': key } : {}) },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(parseApiError(errorBody.detail, 'Scenario simulation failed.'));
  }
  return assertV3Response(await response.json());
}

export default function PortfolioPlatform() {
  const path = typeof window !== 'undefined' ? window.location.pathname.replace(/\/$/, '') : '';
  if (path === '/demo-preview') return <PublicDemoPage apiUrl={API_URL} />;
  if (path === '/demo' || path.startsWith('/demo/')) return <PublicDemoPage apiUrl={API_URL} published version={path.slice(6) || null} />;
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
  const { session } = usePrivateSession();
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
      setSingleResult(await session.authorize(key => postScenario('/api/simulate', buildSingleRequest(ticker, singleAssumptions), key)));
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
      setPortfolioResult(await session.authorize(key => postScenario('/api/simulate-portfolio', request, key)));
    } catch (requestError) {
      setErrors((current) => ({ ...current, portfolio: requestError.message }));
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
    </PlatformShell>
  );
}
