import React, { useState, useMemo } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, BarChart, Bar, PieChart as RePieChart, Pie, Cell
} from 'recharts';
import { 
  TrendingUp, Activity, AlertTriangle, BarChart3, 
  Zap, Target, PieChart, RefreshCw, ChevronRight, Sparkles, 
  Shield, TrendingDown, Database, Plus, X, Briefcase, Layers
} from 'lucide-react';

const API_URL = 'https://market-scenario-generator.onrender.com';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    // Handle cases where payload might differ between charts
    const values = payload.map(p => p.value);
    const max = Math.max(...values);
    const min = Math.min(...values);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;

    return (
      <div className="bg-white border border-slate-200 p-4 rounded-2xl shadow-2xl">
        <p className="text-slate-600 font-bold mb-2 text-xs uppercase tracking-wider">Day {label}</p>
        <div className="space-y-1 text-sm font-mono">
          <div className="flex justify-between gap-6">
            <span className="text-emerald-600">High:</span>
            <span className="text-slate-900 font-semibold">${max.toFixed(2)}</span>
          </div>
          <div className="flex justify-between gap-6">
            <span className="text-slate-600">Avg:</span>
            <span className="text-slate-900 font-semibold">${avg.toFixed(2)}</span>
          </div>
          <div className="flex justify-between gap-6">
            <span className="text-rose-600">Low:</span>
            <span className="text-slate-900 font-semibold">${min.toFixed(2)}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export default function MarketScenarioGenerator() {
  const [ticker, setTicker] = useState('SPY');
  const [years, setYears] = useState(3);
  const [horizon, setHorizon] = useState(252);
  const [numPaths, setNumPaths] = useState(1000);
  const [model, setModel] = useState('gaussian');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('single');

  // Portfolio state
  const [portfolioAssets, setPortfolioAssets] = useState([
    { ticker: 'SPY', weight: 33.33 },
    { ticker: 'AAPL', weight: 33.33 },
    { ticker: 'BTC-USD', weight: 33.34 }
  ]);
  const [portfolioResults, setPortfolioResults] = useState(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Added timestamp to force fresh fetch
      const response = await fetch(`${API_URL}/api/simulate?t=${Date.now()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, years, horizon, num_paths: numPaths, model })
      });
      
      if (!response.ok) throw new Error('Simulation failed');
      
      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const runPortfolioSimulation = async () => {
    setPortfolioLoading(true);
    setError(null);
    
    try {
      const tickers = portfolioAssets.map(a => a.ticker);
      const weights = portfolioAssets.map(a => a.weight / 100);
      
      const response = await fetch(`${API_URL}/api/simulate-portfolio?t=${Date.now()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          tickers, 
          weights, 
          years, 
          horizon, 
          num_paths: numPaths, 
          model 
        })
      });
      
      if (!response.ok) throw new Error('Portfolio simulation failed');
      
      const data = await response.json();
      setPortfolioResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setPortfolioLoading(false);
    }
  };

  const addAsset = () => {
    if (portfolioAssets.length >= 10) return;
    setPortfolioAssets([...portfolioAssets, { ticker: '', weight: 0 }]);
  };

  const removeAsset = (index) => {
    if (portfolioAssets.length <= 2) return;
    const newAssets = portfolioAssets.filter((_, i) => i !== index);
    setPortfolioAssets(newAssets);
  };

  const updateAsset = (index, field, value) => {
    const newAssets = [...portfolioAssets];
    newAssets[index][field] = value;
    setPortfolioAssets(newAssets);
  };

  const normalizeWeights = () => {
    const total = portfolioAssets.reduce((sum, a) => sum + (parseFloat(a.weight) || 0), 0);
    if (total === 0) return;
    const normalized = portfolioAssets.map(a => ({
      ...a,
      weight: ((parseFloat(a.weight) || 0) / total * 100).toFixed(2)
    }));
    setPortfolioAssets(normalized);
  };

  const totalWeight = portfolioAssets.reduce((sum, a) => sum + (parseFloat(a.weight) || 0), 0);

  const chartData = useMemo(() => {
    if (!results?.paths_sample) return [];
    return Array.from({ length: horizon }, (_, dayIndex) => {
      const dayData = { day: dayIndex };
      results.paths_sample.forEach((path, pathIdx) => {
        dayData[`path_${pathIdx}`] = path[dayIndex];
      });
      return dayData;
    });
  }, [results, horizon]);

  const portfolioChartData = useMemo(() => {
    if (!portfolioResults?.portfolio_paths_sample) return [];
    const paths = portfolioResults.portfolio_paths_sample;
    return Array.from({ length: paths[0]?.length || 0 }, (_, dayIndex) => {
      const dayData = { day: dayIndex };
      paths.forEach((path, pathIdx) => {
        dayData[`path_${pathIdx}`] = path[dayIndex];
      });
      return dayData;
    });
  }, [portfolioResults]);

  const correlationData = useMemo(() => {
    if (!portfolioResults?.correlation_matrix) return [];
    const tickers = portfolioResults.tickers;
    const data = [];
    tickers.forEach(ticker1 => {
      tickers.forEach(ticker2 => {
        if (ticker1 !== ticker2) {
          const corr = portfolioResults.correlation_matrix[ticker1][ticker2];
          data.push({
            pair: `${ticker1}-${ticker2}`,
            correlation: corr,
            abs: Math.abs(corr)
          });
        }
      });
    });
    // Filter duplicates (A-B vs B-A) and sort
    const uniquePairs = new Set();
    const uniqueData = [];
    data.forEach(d => {
        const [a, b] = d.pair.split('-');
        const key = [a,b].sort().join('-');
        if (!uniquePairs.has(key)) {
            uniquePairs.add(key);
            uniqueData.push(d);
        }
    });

    return uniqueData.sort((a, b) => b.abs - a.abs).slice(0, 6);
  }, [portfolioResults]);

  const histogramData = useMemo(() => {
    if (!results?.final_returns) return [];
    const distributionData = results.final_returns.reduce((acc, ret) => {
      const bucket = Math.round(ret * 20) / 20;
      acc[bucket] = (acc[bucket] || 0) + 1;
      return acc;
    }, {});
    return Object.entries(distributionData)
      .map(([ret, count]) => ({ return: parseFloat(ret), count }))
      .sort((a, b) => a.return - b.return);
  }, [results]);

  const models = [
    { value: 'gaussian', label: 'Gaussian', icon: Target, desc: 'Normal distribution' },
    { value: 'gmm', label: 'GMM', icon: PieChart, desc: 'Fat-tailed regime' },
    { value: 'ewma', label: 'EWMA', icon: Activity, desc: 'Dynamic volatility' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-50">
      {/* Header */}
      <div className="border-b border-slate-200 bg-white/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="bg-slate-900 p-3 rounded-2xl shadow-lg">
                <TrendingUp className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-slate-900">
                  Market Scenario Generator
                </h1>
                <p className="text-slate-600 text-sm mt-1">
                  Professional Portfolio Risk Simulation
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="px-4 py-2 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm font-semibold">
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse mr-2"></span>
                Live
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-8 py-8">
        {/* Tabs */}
        <div className="flex gap-3 mb-8">
          {[
            { id: 'single', label: 'Single Asset', icon: Zap },
            { id: 'portfolio', label: 'Portfolio', icon: Briefcase },
            { id: 'compare', label: 'Compare', icon: BarChart3 }
          ].map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-3 rounded-2xl font-semibold transition-all flex items-center gap-2 ${
                  activeTab === tab.id
                    ? 'bg-slate-900 text-white shadow-lg shadow-slate-900/20'
                    : 'bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900 border border-slate-200 shadow-sm'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Single Asset Tab */}
        {activeTab === 'single' && (
          <>
            <SingleAssetConfig
              ticker={ticker}
              setTicker={setTicker}
              years={years}
              setYears={setYears}
              horizon={horizon}
              setHorizon={setHorizon}
              numPaths={numPaths}
              setNumPaths={setNumPaths}
              model={model}
              setModel={setModel}
              models={models}
              loading={loading}
              error={error}
              runSimulation={runSimulation}
            />
            
            {results && (
              <SingleAssetResults results={results} chartData={chartData} numPaths={numPaths} histogramData={histogramData} />
            )}
          </>
        )}

        {/* Portfolio Tab */}
        {activeTab === 'portfolio' && (
          <>
            <PortfolioConfig
              portfolioAssets={portfolioAssets}
              updateAsset={updateAsset}
              removeAsset={removeAsset}
              addAsset={addAsset}
              totalWeight={totalWeight}
              normalizeWeights={normalizeWeights}
              years={years}
              setYears={setYears}
              horizon={horizon}
              setHorizon={setHorizon}
              numPaths={numPaths}
              setNumPaths={setNumPaths}
              model={model}
              setModel={setModel}
              models={models}
              portfolioLoading={portfolioLoading}
              error={error}
              runPortfolioSimulation={runPortfolioSimulation}
            />

            {portfolioResults && (
              <PortfolioResults 
                portfolioResults={portfolioResults} 
                portfolioChartData={portfolioChartData}
                correlationData={correlationData}
              />
            )}
          </>
        )}

        {/* Compare Tab */}
        {activeTab === 'compare' && (
          <div className="bg-white rounded-3xl p-12 text-center border border-slate-200 shadow-xl shadow-slate-200/50">
            <div className="inline-flex p-6 rounded-full bg-slate-50 mb-6">
              <BarChart3 className="w-16 h-16 text-slate-900" />
            </div>
            <h3 className="text-3xl font-bold text-slate-900 mb-3">Model Comparison</h3>
            <p className="text-slate-600 mb-6 max-w-md mx-auto">
              Compare Gaussian, GMM, and EWMA models side-by-side
            </p>
            <div className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-slate-900 text-white">
              <Sparkles className="w-4 h-4 animate-pulse" />
              <span className="text-sm font-semibold">Coming Soon</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Component: Single Asset Configuration
function SingleAssetConfig({ ticker, setTicker, years, setYears, horizon, setHorizon, numPaths, setNumPaths, model, setModel, models, loading, error, runSimulation }) {
  return (
    <div className="bg-white rounded-3xl p-8 mb-8 border border-slate-200 shadow-xl shadow-slate-200/50">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-xl bg-slate-900">
          <Activity className="w-5 h-5 text-white" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900">Configuration</h2>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-3">Ticker</label>
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900 font-semibold"
          />
        </div>
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-3">Years</label>
          <input
            type="number"
            value={years}
            onChange={(e) => setYears(parseInt(e.target.value))}
            min="1"
            max="10"
            className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900 font-semibold"
          />
        </div>
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-3">Horizon (days)</label>
          <input
            type="number"
            value={horizon}
            onChange={(e) => setHorizon(parseInt(e.target.value))}
            min="1"
            max="1000"
            className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900 font-semibold"
          />
        </div>
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-3">Paths</label>
          <input
            type="number"
            value={numPaths}
            onChange={(e) => setNumPaths(parseInt(e.target.value))}
            min="100"
            max="10000"
            step="100"
            className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900 font-semibold"
          />
        </div>
        <div className="md:col-span-2">
          <label className="block text-sm font-semibold text-slate-700 mb-3">Model</label>
          <div className="grid grid-cols-3 gap-3">
            {models.map(m => {
              const Icon = m.icon;
              const isActive = model === m.value;
              return (
                <button
                  key={m.value}
                  onClick={() => setModel(m.value)}
                  className={`p-4 rounded-2xl transition-all border-2 ${
                    isActive
                      ? 'bg-slate-900 border-slate-900 shadow-lg shadow-slate-900/20'
                      : 'bg-white border-slate-200 hover:border-slate-300 shadow-sm'
                  }`}
                >
                  <Icon className={`w-5 h-5 mb-2 mx-auto ${isActive ? 'text-white' : 'text-slate-900'}`} />
                  <div className={`text-sm font-bold ${isActive ? 'text-white' : 'text-slate-900'}`}>{m.label}</div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <button
        onClick={runSimulation}
        disabled={loading}
        className="w-full bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white font-bold py-4 px-8 rounded-2xl transition-all shadow-lg flex items-center justify-center gap-3 group"
      >
        {loading ? (
          <>
            <RefreshCw className="w-5 h-5 animate-spin" />
            Running...
          </>
        ) : (
          <>
            <Sparkles className="w-5 h-5" />
            Run Simulation
            <ChevronRight className="w-5 h-5" />
          </>
        )}
      </button>

      {error && (
        <div className="mt-6 bg-red-50 border border-red-200 rounded-2xl p-4">
          <p className="text-red-900 font-semibold">{error}</p>
        </div>
      )}
    </div>
  );
}

// Component: Portfolio Configuration
function PortfolioConfig({ portfolioAssets, updateAsset, removeAsset, addAsset, totalWeight, normalizeWeights, years, setYears, horizon, setHorizon, numPaths, setNumPaths, model, setModel, models, portfolioLoading, error, runPortfolioSimulation }) {
  return (
    <div className="bg-white rounded-3xl p-8 mb-8 border border-slate-200 shadow-xl shadow-slate-200/50">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-slate-900">
            <Briefcase className="w-5 h-5 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900">Portfolio Builder</h2>
        </div>
        <button
          onClick={addAsset}
          disabled={portfolioAssets.length >= 10}
          className="px-4 py-2 bg-slate-900 text-white rounded-xl text-sm font-semibold flex items-center gap-2 disabled:bg-slate-300"
        >
          <Plus className="w-4 h-4" />
          Add Asset
        </button>
      </div>

      <div className="space-y-3 mb-6">
        {portfolioAssets.map((asset, index) => (
          <div key={index} className="flex gap-3">
            <input
              type="text"
              value={asset.ticker}
              onChange={(e) => updateAsset(index, 'ticker', e.target.value.toUpperCase())}
              placeholder="TICKER"
              className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900 font-semibold"
            />
            <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-4">
              <input
                type="number"
                value={asset.weight}
                onChange={(e) => updateAsset(index, 'weight', parseFloat(e.target.value) || 0)}
                className="w-20 bg-transparent text-slate-900 focus:outline-none font-semibold"
                step="0.01"
              />
              <span className="text-slate-600 font-semibold">%</span>
            </div>
            <button
              onClick={() => removeAsset(index)}
              disabled={portfolioAssets.length <= 2}
              className="p-3 bg-red-50 hover:bg-red-100 disabled:bg-slate-100 text-red-600 disabled:text-slate-400 rounded-xl transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between mb-6 p-4 bg-slate-50 rounded-xl">
        <span className="text-sm font-semibold text-slate-700">Total Weight:</span>
        <div className="flex items-center gap-3">
          <span className={`text-lg font-bold ${Math.abs(totalWeight - 100) < 0.01 ? 'text-emerald-600' : 'text-red-600'}`}>
            {totalWeight.toFixed(2)}%
          </span>
          <button
            onClick={normalizeWeights}
            className="px-4 py-2 bg-slate-900 text-white text-xs rounded-lg font-semibold"
          >
            Normalize
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">Years</label>
          <input
            type="number"
            value={years}
            onChange={(e) => setYears(parseInt(e.target.value))}
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
        </div>
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">Horizon</label>
          <input
            type="number"
            value={horizon}
            onChange={(e) => setHorizon(parseInt(e.target.value))}
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
        </div>
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">Paths</label>
          <input
            type="number"
            value={numPaths}
            onChange={(e) => setNumPaths(parseInt(e.target.value))}
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
        </div>
      </div>

      <div className="mb-6">
        <label className="block text-sm font-semibold text-slate-700 mb-3">Model</label>
        <div className="grid grid-cols-3 gap-3">
          {models.filter(m => m.value !== 'ewma').map(m => {
            const Icon = m.icon;
            const isActive = model === m.value;
            return (
              <button
                key={m.value}
                onClick={() => setModel(m.value)}
                className={`p-3 rounded-xl transition-all ${
                  isActive ? 'bg-slate-900 text-white' : 'bg-slate-50 text-slate-900 border border-slate-200'
                }`}
              >
                <Icon className="w-4 h-4 mx-auto mb-1" />
                <div className="text-xs font-bold">{m.label}</div>
              </button>
            );
          })}
        </div>
      </div>

      <button
        onClick={runPortfolioSimulation}
        disabled={portfolioLoading || Math.abs(totalWeight - 100) > 0.01}
        className="w-full bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white font-bold py-4 rounded-2xl transition-all flex items-center justify-center gap-3"
      >
        {portfolioLoading ? (
          <>
            <RefreshCw className="w-5 h-5 animate-spin" />
            Simulating Portfolio...
          </>
        ) : (
          <>
            <Layers className="w-5 h-5" />
            Run Portfolio Simulation
          </>
        )}
      </button>

      {error && (
        <div className="mt-6 bg-red-50 border border-red-200 rounded-2xl p-4">
          <p className="text-red-900 font-semibold">{error}</p>
        </div>
      )}
    </div>
  );
}

// Component: Single Asset Results
function SingleAssetResults({ results, chartData, numPaths, histogramData }) {
  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <StatCard title="Mean Return" value={`${(results.risk_stats.mean * 100).toFixed(2)}%`} icon={TrendingUp} color="emerald" trend="positive" />
        <StatCard title="Volatility" value={`${(results.risk_stats.vol * 100).toFixed(2)}%`} icon={Activity} color="violet" />
        <StatCard title="VaR (95%)" value={`${(results.risk_stats.VaR_95 * 100).toFixed(2)}%`} icon={Shield} color="rose" trend="negative" />
        <StatCard title="CVaR (95%)" value={`${(results.risk_stats.CVaR_95 * 100).toFixed(2)}%`} icon={TrendingDown} color="orange" trend="negative" />
        <StatCard title="Prob. Loss" value={`${(results.risk_stats.prob_loss * 100).toFixed(1)}%`} icon={AlertTriangle} color="amber" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Simulated Paths" icon={TrendingUp}>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="day" stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip content={<CustomTooltip />} />
              {results.paths_sample.map((_, idx) => (
                <Line key={idx} type="monotone" dataKey={`path_${idx}`} stroke="#0f172a" strokeWidth={1.5} dot={false} strokeOpacity={0.15} isAnimationActive={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Return Distribution" icon={BarChart3}>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={histogramData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="return" stroke="#64748b" tickFormatter={(val) => `${(val * 100).toFixed(0)}%`} />
              <YAxis stroke="#64748b" />
              <Tooltip />
              <Bar dataKey="count" fill="#0f172a" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </>
  );
}

// Component: Portfolio Results
function PortfolioResults({ portfolioResults, portfolioChartData, correlationData }) {
  const pieColors = ['#0f172a', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
  
  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard title="Portfolio Return" value={`${(portfolioResults.portfolio_stats.mean * 100).toFixed(2)}%`} icon={TrendingUp} color="emerald" trend="positive" />
        <StatCard title="Volatility" value={`${(portfolioResults.portfolio_stats.volatility * 100).toFixed(2)}%`} icon={Activity} color="violet" />
        <StatCard title="Sharpe Ratio" value={`${portfolioResults.portfolio_stats.sharpe_ratio.toFixed(2)}`} icon={Target} color="blue" />
        <StatCard title="VaR (95%)" value={`${(portfolioResults.portfolio_stats.VaR_95 * 100).toFixed(2)}%`} icon={Shield} color="rose" trend="negative" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Portfolio Value Chart (Spans 2 cols) */}
        <div className="lg:col-span-2">
            <ChartCard title="Projected Portfolio Value" icon={TrendingUp}>
            <ResponsiveContainer width="100%" height={320}>
                <LineChart data={portfolioChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="day" stroke="#64748b" />
                <YAxis stroke="#64748b" domain={['auto', 'auto']} />
                <Tooltip content={<CustomTooltip />} />
                {portfolioResults.portfolio_paths_sample.map((_, idx) => (
                    <Line 
                    key={idx} 
                    type="monotone" 
                    dataKey={`path_${idx}`} 
                    stroke="#4f46e5" 
                    strokeWidth={1.5} 
                    dot={false} 
                    strokeOpacity={0.15} 
                    isAnimationActive={false} 
                    />
                ))}
                </LineChart>
            </ResponsiveContainer>
            </ChartCard>
        </div>

        {/* Correlations & Breakdown (Spans 1 col) */}
        <div className="space-y-6">
            {/* Asset Weights Pie Chart */}
            <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xl shadow-slate-200/50">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-xl bg-slate-900">
                        <RePieChart className="w-5 h-5 text-white" />
                    </div>
                    <h3 className="text-xl font-bold text-slate-900">Allocation</h3>
                </div>
                <div className="h-[200px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <RePieChart>
                            <Pie
                                data={portfolioResults.asset_stats}
                                dataKey="contribution"
                                nameKey="ticker"
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                            >
                                {portfolioResults.asset_stats.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={pieColors[index % pieColors.length]} />
                                ))}
                            </Pie>
                            <Tooltip />
                        </RePieChart>
                    </ResponsiveContainer>
                </div>
                <div className="space-y-2 mt-2">
                    {portfolioResults.asset_stats.map((asset, index) => (
                        <div key={asset.ticker} className="flex justify-between text-sm">
                            <span className="font-semibold text-slate-600 flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: pieColors[index % pieColors.length] }}></span>
                                {asset.ticker}
                            </span>
                            <span className="font-bold text-slate-900">
                                {((asset.contribution || 0) * 100).toFixed(1)}% Contrib.
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Top Correlations */}
            <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xl shadow-slate-200/50">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 rounded-xl bg-slate-900">
                        <Layers className="w-5 h-5 text-white" />
                    </div>
                    <h3 className="text-xl font-bold text-slate-900">Top Correlations</h3>
                </div>
                <div className="space-y-3">
                    {correlationData.slice(0, 4).map((item, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                            <span className="text-xs font-bold text-slate-600">{item.pair}</span>
                            <span className={`text-sm font-bold ${item.correlation > 0.7 ? 'text-emerald-600' : item.correlation < -0.5 ? 'text-rose-600' : 'text-slate-900'}`}>
                                {item.correlation.toFixed(2)}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
      </div>
    </>
  );
}

function StatCard({ title, value, icon: Icon, color, trend }) {
  const colors = {
    emerald: 'text-emerald-600 bg-emerald-50',
    violet: 'text-violet-600 bg-violet-50',
    rose: 'text-rose-600 bg-rose-50',
    orange: 'text-orange-600 bg-orange-50',
    amber: 'text-amber-600 bg-amber-50',
    blue: 'text-blue-600 bg-blue-50',
  };

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-lg shadow-slate-200/50">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-xl ${colors[color] || 'text-slate-900 bg-slate-100'}`}>
          <Icon className="w-5 h-5" />
        </div>
        {trend === 'positive' && <TrendingUp className="w-4 h-4 text-emerald-500" />}
        {trend === 'negative' && <TrendingDown className="w-4 h-4 text-rose-500" />}
      </div>
      <div>
        <p className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">{title}</p>
        <p className="text-2xl font-bold text-slate-900">{value}</p>
      </div>
    </div>
  );
}

function ChartCard({ title, icon: Icon, children }) {
  return (
    <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xl shadow-slate-200/50">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-xl bg-slate-900">
          <Icon className="w-5 h-5 text-white" />
        </div>
        <h3 className="text-xl font-bold text-slate-900">{title}</h3>
      </div>
      {children}
    </div>
  );
}