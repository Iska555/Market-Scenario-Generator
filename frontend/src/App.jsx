import React, { useState, useMemo } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, BarChart, Bar, PieChart as RePieChart, Pie, Cell
} from 'recharts';
import { 
  TrendingUp, Activity, AlertTriangle, BarChart3, 
  Zap, Target, PieChart, RefreshCw, Sparkles, 
  Shield, TrendingDown, Plus, X, Briefcase, Layers,
  Sun, Moon, Info, ArrowRight
} from 'lucide-react';

const API_URL = 'https://market-scenario-generator.onrender.com';

// --- Components ---

// 1. Theme-Aware Tooltip for Charts
const CustomTooltip = ({ active, payload, label, isDark }) => {
  if (active && payload && payload.length) {
    const values = payload.map(p => p.value);
    const max = Math.max(...values);
    const min = Math.min(...values);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;

    return (
      <div className={`${isDark ? 'bg-[#1e293b] border-slate-700' : 'bg-white border-slate-200'} border p-4 rounded-xl shadow-2xl backdrop-blur-md`}>
        <p className={`${isDark ? 'text-slate-400' : 'text-slate-500'} font-bold mb-2 text-xs uppercase tracking-wider`}>Day {label}</p>
        <div className="space-y-1 text-sm font-mono">
          <div className="flex justify-between gap-6">
            <span className="text-emerald-500">High:</span>
            <span className={`${isDark ? 'text-white' : 'text-slate-900'} font-semibold`}>${max.toFixed(2)}</span>
          </div>
          <div className="flex justify-between gap-6">
            <span className="text-indigo-500">Avg:</span>
            <span className={`${isDark ? 'text-white' : 'text-slate-900'} font-semibold`}>${avg.toFixed(2)}</span>
          </div>
          <div className="flex justify-between gap-6">
            <span className="text-rose-500">Low:</span>
            <span className={`${isDark ? 'text-white' : 'text-slate-900'} font-semibold`}>${min.toFixed(2)}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

// 2. Info Tooltip Component (The "i" icon)
const InfoTooltip = ({ text, isDark }) => (
  <div className="group relative inline-block ml-2">
    <Info className={`w-3 h-3 cursor-help ${isDark ? 'text-slate-500 hover:text-slate-300' : 'text-slate-400 hover:text-slate-600'}`} />
    <div className={`
      invisible group-hover:visible absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 
      text-xs rounded-lg shadow-xl z-50 text-center pointer-events-none transition-all opacity-0 group-hover:opacity-100
      ${isDark ? 'bg-slate-800 text-slate-200 border border-slate-700' : 'bg-slate-900 text-white'}
    `}>
      {text}
      <div className={`absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent ${isDark ? 'border-t-slate-800' : 'border-t-slate-900'}`}></div>
    </div>
  </div>
);

// 3. Extreme Scenarios Table Component
const ExtremeScenarios = ({ returns, isDark }) => {
  // Helper to calculate percentiles
  const getPercentile = (arr, q) => {
    const sorted = [...arr].sort((a, b) => a - b);
    const pos = (sorted.length - 1) * q;
    const base = Math.floor(pos);
    const rest = pos - base;
    if (sorted[base + 1] !== undefined) {
      return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
    }
    return sorted[base];
  };

  const best = getPercentile(returns, 0.99);
  const bullish = getPercentile(returns, 0.75);
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
  const bearish = getPercentile(returns, 0.25);
  const worst = getPercentile(returns, 0.01);

  // Mock price base for visualization (assuming $100 start if not provided)
  const basePrice = 1000; 
  const scenarios = [
    { label: "Best Case (99%)", prob: "1%", val: best },
    { label: "Bullish (75%)", prob: "25%", val: bullish },
    { label: "Base Case (Mean)", prob: "50%", val: mean },
    { label: "Bearish (25%)", prob: "25%", val: bearish },
    { label: "Worst Case (1%)", prob: "1%", val: worst },
  ];

  return (
    <div className={`${isDark ? 'bg-[#151e32] border-slate-700' : 'bg-white border-slate-200 shadow-xl shadow-slate-200/50'} rounded-3xl overflow-hidden border transition-all h-fit flex flex-col`}>
      <div className={`p-5 border-b ${isDark ? 'border-slate-700' : 'border-slate-100'}`}>
         <div className="flex items-center gap-2 mb-1">
             <AlertTriangle className="w-5 h-5 text-amber-500" />
             <h3 className={`font-bold text-lg ${isDark ? 'text-white' : 'text-slate-900'}`}>Extreme Scenarios</h3>
         </div>
         <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Probabilistic tail outcomes</p>
      </div>
      
      <div className="flex-1 p-0">
          <div className="grid grid-cols-2 px-6 py-3 text-xs font-bold tracking-wider uppercase opacity-50">
             <span>Scenario</span>
             <span className="text-right">Return</span>
          </div>
          {scenarios.map((s, i) => (
             <div key={i} className={`grid grid-cols-2 px-6 py-4 border-t ${isDark ? 'border-slate-800' : 'border-slate-50'} items-center`}>
                <div>
                   <div className={`font-bold text-sm ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>{s.label}</div>
                   <div className="flex gap-2 mt-1">
                       <span className={`text-[10px] px-1.5 py-0.5 rounded ${isDark ? 'bg-slate-700 text-slate-300' : 'bg-slate-200 text-slate-600'}`}>{s.prob}</span>
                       <span className={`text-xs font-mono ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>${(basePrice * (1 + s.val)).toFixed(2)}</span>
                   </div>
                </div>
                <div className={`text-right font-mono font-bold ${s.val >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                   {s.val >= 0 ? '+' : ''}{(s.val * 100).toFixed(1)}%
                </div>
             </div>
          ))}
      </div>
      
      <div className={`p-4 border-t ${isDark ? 'border-slate-700' : 'border-slate-100'}`}>
          <button className={`w-full text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 py-2 rounded-lg transition-colors ${isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'}`}>
             View Full Distribution <ArrowRight className="w-3 h-3" />
          </button>
      </div>
    </div>
  );
};

export default function MarketScenarioGenerator() {
  const [theme, setTheme] = useState('dark'); // Default to dark per request image
  const isDark = theme === 'dark';
  
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
  // Initialized with strings to handle empty inputs cleanly
  const [portfolioAssets, setPortfolioAssets] = useState([
    { ticker: 'SPY', weight: '33.33' },
    { ticker: 'AAPL', weight: '33.33' },
    { ticker: 'BTC-USD', weight: '33.34' }
  ]);
  const [portfolioResults, setPortfolioResults] = useState(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);

  const toggleTheme = () => setTheme(curr => curr === 'light' ? 'dark' : 'light');

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
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
      // Ensure we parse strings to floats safely
      const weights = portfolioAssets.map(a => (parseFloat(a.weight) || 0) / 100);
      
      const response = await fetch(`${API_URL}/api/simulate-portfolio?t=${Date.now()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers, weights, years, horizon, num_paths: numPaths, model })
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

  // Asset Management
  const addAsset = () => {
    if (portfolioAssets.length >= 10) return;
    setPortfolioAssets([...portfolioAssets, { ticker: '', weight: '' }]);
  };

  const removeAsset = (index) => {
    if (portfolioAssets.length <= 2) return;
    setPortfolioAssets(portfolioAssets.filter((_, i) => i !== index));
  };

  const updateAsset = (index, field, value) => {
    const newAssets = [...portfolioAssets];
    
    if (field === 'weight') {
        // Allow empty string for clearing input, otherwise restrict to numbers
        if (value === '' || /^\d*\.?\d*$/.test(value)) {
            newAssets[index][field] = value;
        }
    } else {
        newAssets[index][field] = value;
    }
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

  // Memoized Data
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
    const seen = new Set();
    
    tickers.forEach(ticker1 => {
      tickers.forEach(ticker2 => {
        if (ticker1 !== ticker2) {
          const key = [ticker1, ticker2].sort().join('-');
          if (!seen.has(key)) {
            seen.add(key);
            const corr = portfolioResults.correlation_matrix[ticker1][ticker2];
            data.push({ pair: key, correlation: corr, abs: Math.abs(corr) });
          }
        }
      });
    });
    return data.sort((a, b) => b.abs - a.abs).slice(0, 6);
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

  // Dynamic Styles - DEEP NAVY / GRAY-WHITE Implementation
  const bgMain = isDark ? "bg-[#0B1120]" : "bg-slate-50"; 
  const textMain = isDark ? "text-slate-100" : "text-slate-900";
  const textSub = isDark ? "text-slate-400" : "text-slate-500";
  
  // Card styles: Dark uses a slightly lighter navy, Light uses white
  const bgCard = isDark ? "bg-[#151e32] border-slate-700/50" : "bg-white border-slate-200 shadow-xl shadow-slate-200/50";
  const border = isDark ? "border-slate-800" : "border-slate-200";

  return (
    <div className={`min-h-screen transition-colors duration-300 ${bgMain}`}>
      {/* Header */}
      <div className={`border-b ${border} ${isDark ? 'bg-[#0B1120]/90' : 'bg-white/80'} backdrop-blur-xl sticky top-0 z-50`}>
        <div className="max-w-7xl mx-auto px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`${isDark ? 'bg-blue-600' : 'bg-blue-600'} p-2.5 rounded-xl shadow-lg transition-colors`}>
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className={`text-xl font-bold ${textMain}`}>Market Scenario Generator</h1>
                <p className={`text-xs font-medium tracking-wide uppercase mt-0.5 ${textSub}`}>Advanced Monte Carlo Risk Simulation Platform</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <button onClick={toggleTheme} className={`p-2 rounded-full border transition-all ${isDark ? 'bg-slate-800 border-slate-700 text-yellow-400 hover:bg-slate-700' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}>
                {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </button>
              <div className={`px-3 py-1.5 rounded-full ${isDark ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-emerald-100 border-emerald-200 text-emerald-700'} text-xs font-semibold flex items-center gap-2`}>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                System Live
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-8 py-8">
        {/* Tabs */}
        <div className="flex gap-2 mb-8">
          {[
            { id: 'single', label: 'Single Asset', icon: Zap },
            { id: 'portfolio', label: 'Portfolio Builder', icon: Briefcase },
            { id: 'compare', label: 'Model Lab', icon: BarChart3 }
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-5 py-2.5 rounded-xl font-semibold transition-all flex items-center gap-2 text-sm ${
                  isActive
                    ? (isDark ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' : 'bg-slate-900 text-white shadow-lg shadow-slate-200')
                    : (isDark ? 'text-slate-400 hover:bg-slate-800' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50')
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* --- SINGLE ASSET TAB --- */}
        {activeTab === 'single' && (
          <>
            <SingleAssetConfig
              ticker={ticker} setTicker={setTicker} years={years} setYears={setYears}
              horizon={horizon} setHorizon={setHorizon} numPaths={numPaths} setNumPaths={setNumPaths}
              model={model} setModel={setModel} models={models} loading={loading} error={error}
              runSimulation={runSimulation} isDark={isDark}
            />
            {results && (
              <SingleAssetResults results={results} chartData={chartData} numPaths={numPaths} histogramData={histogramData} isDark={isDark} />
            )}
          </>
        )}

        {/* --- PORTFOLIO TAB --- */}
        {activeTab === 'portfolio' && (
          <>
            <PortfolioConfig
              portfolioAssets={portfolioAssets} updateAsset={updateAsset} removeAsset={removeAsset}
              addAsset={addAsset} totalWeight={totalWeight} normalizeWeights={normalizeWeights}
              years={years} setYears={setYears} horizon={horizon} setHorizon={setHorizon}
              numPaths={numPaths} setNumPaths={setNumPaths} model={model} setModel={setModel}
              models={models} portfolioLoading={portfolioLoading} error={error}
              runPortfolioSimulation={runPortfolioSimulation} isDark={isDark}
            />
            {portfolioResults && (
              <PortfolioResults 
                portfolioResults={portfolioResults} 
                portfolioChartData={portfolioChartData}
                correlationData={correlationData}
                isDark={isDark}
              />
            )}
          </>
        )}

        {/* --- COMPARE TAB --- */}
        {activeTab === 'compare' && (
          <div className={`${bgCard} rounded-3xl p-16 text-center border transition-all`}>
            <div className={`inline-flex p-6 rounded-full mb-6 ${isDark ? 'bg-slate-800' : 'bg-slate-100'}`}>
              <BarChart3 className={`w-16 h-16 ${isDark ? 'text-slate-600' : 'text-slate-400'}`} />
            </div>
            <h3 className={`text-3xl font-bold ${textMain} mb-3`}>Model Comparison Lab</h3>
            <p className={`${textSub} mb-8 max-w-md mx-auto`}>
              Run Gaussian, GMM, and EWMA models side-by-side to visualize tail risk differences.
            </p>
            <div className={`inline-flex items-center gap-2 px-6 py-3 rounded-full ${isDark ? 'bg-blue-900/30 text-blue-400 border border-blue-500/30' : 'bg-slate-900 text-white'}`}>
              <Sparkles className="w-4 h-4 animate-pulse" />
              <span className="text-sm font-semibold">Feature Coming Soon</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// --- SUB-COMPONENTS ---

function SingleAssetConfig({ ticker, setTicker, years, setYears, horizon, setHorizon, numPaths, setNumPaths, model, setModel, models, loading, error, runSimulation, isDark }) {
  const inputClass = `w-full rounded-xl px-4 py-3 font-mono text-sm border focus:outline-none focus:ring-2 transition-all ${
    isDark ? 'bg-[#0f172a] border-slate-700 text-white focus:ring-blue-500' : 'bg-slate-50 border-slate-200 text-slate-900 focus:ring-slate-900'
  }`;
  
  return (
    <div className={`${isDark ? 'bg-[#151e32] border-slate-700/50' : 'bg-white border-slate-200 shadow-xl shadow-slate-200/50'} rounded-3xl p-8 mb-8 border transition-all`}>
      <div className="flex items-center gap-3 mb-6">
        <div className={`p-2 rounded-xl ${isDark ? 'bg-slate-800 text-white' : 'bg-slate-900 text-white'}`}>
          <Activity className="w-5 h-5" />
        </div>
        <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>Configuration</h2>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <div>
          <label className={`block text-xs font-bold uppercase tracking-wider mb-2 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>Ticker</label>
          <input type="text" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} className={inputClass} />
        </div>
        <div>
          <label className={`block text-xs font-bold uppercase tracking-wider mb-2 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>Horizon (Days)</label>
          <input type="number" value={horizon} onChange={(e) => setHorizon(parseInt(e.target.value))} className={inputClass} />
        </div>
        <div>
          <label className={`block text-xs font-bold uppercase tracking-wider mb-2 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>Sim Paths</label>
          <input type="number" value={numPaths} onChange={(e) => setNumPaths(parseInt(e.target.value))} className={inputClass} />
        </div>
        <div>
          <label className={`block text-xs font-bold uppercase tracking-wider mb-2 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>History (Yrs)</label>
          <input type="number" value={years} onChange={(e) => setYears(parseInt(e.target.value))} className={inputClass} />
        </div>
      </div>

      <div className="mb-8">
        <label className={`block text-xs font-bold uppercase tracking-wider mb-3 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>Statistical Model</label>
        <div className="grid grid-cols-3 gap-4">
          {models.map(m => {
            const Icon = m.icon;
            const isActive = model === m.value;
            return (
              <button
                key={m.value}
                onClick={() => setModel(m.value)}
                className={`p-4 rounded-xl border text-left transition-all ${
                  isActive 
                    ? (isDark ? 'bg-slate-800 border-slate-600 text-white' : 'bg-slate-900 border-slate-900 text-white shadow-lg') 
                    : (isDark ? 'bg-[#0f172a] border-slate-800 text-slate-400 hover:border-slate-600' : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300')
                }`}
              >
                <div className="flex items-center gap-3 mb-1">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'opacity-70'}`} />
                    <span className="font-bold text-sm">{m.label}</span>
                </div>
                <div className="text-xs opacity-60 pl-7">{m.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      <button
        onClick={runSimulation}
        disabled={loading}
        className={`w-full font-bold py-4 px-8 rounded-xl transition-all shadow-lg flex items-center justify-center gap-3 ${
            isDark ? 'bg-white hover:bg-slate-200 text-slate-900 shadow-white/10' : 'bg-slate-900 hover:bg-slate-800 text-white shadow-slate-200'
        } disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {loading ? <RefreshCw className="w-5 h-5 animate-spin" /> : null} 
        {loading ? 'Processing Simulation...' : 'Run Risk Simulation'}
      </button>

      {error && (
        <div className="mt-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-500 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}
    </div>
  );
}

function PortfolioConfig({ portfolioAssets, updateAsset, removeAsset, addAsset, totalWeight, normalizeWeights, years, setYears, horizon, setHorizon, numPaths, setNumPaths, model, setModel, models, portfolioLoading, error, runPortfolioSimulation, isDark }) {
  const inputClass = `w-full rounded-xl px-4 py-3 font-mono text-sm border focus:outline-none focus:ring-2 transition-all ${
    isDark ? 'bg-[#0f172a] border-slate-700 text-white focus:ring-blue-500' : 'bg-slate-50 border-slate-200 text-slate-900 focus:ring-slate-900'
  }`;

  return (
    <div className={`${isDark ? 'bg-[#151e32] border-slate-700/50' : 'bg-white border-slate-200 shadow-xl shadow-slate-200/50'} rounded-3xl p-8 mb-8 border transition-all`}>
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-xl ${isDark ? 'bg-slate-800 text-white' : 'bg-slate-900 text-white'}`}>
            <Briefcase className="w-5 h-5" />
          </div>
          <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>Portfolio Builder</h2>
        </div>
        <button onClick={addAsset} disabled={portfolioAssets.length >= 10} className={`px-4 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all ${isDark ? 'bg-slate-800 hover:bg-slate-700 text-white' : 'bg-slate-900 text-white hover:bg-slate-800'}`}>
          <Plus className="w-4 h-4" /> Add Asset
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
        {/* Left Col: Asset List */}
        <div className="space-y-4">
            {portfolioAssets.map((asset, index) => (
            <div key={index} className="flex gap-3">
                <div className="flex-1">
                    <input
                        type="text"
                        value={asset.ticker}
                        onChange={(e) => updateAsset(index, 'ticker', e.target.value.toUpperCase())}
                        placeholder="TICKER"
                        className={inputClass}
                    />
                </div>
                <div className={`flex items-center gap-2 rounded-xl px-4 border ${isDark ? 'bg-[#0f172a] border-slate-700' : 'bg-slate-50 border-slate-200'}`}>
                    <input
                        type="text" 
                        value={asset.weight}
                        onChange={(e) => updateAsset(index, 'weight', e.target.value)}
                        placeholder="0"
                        className={`w-16 bg-transparent focus:outline-none font-mono font-semibold ${isDark ? 'text-white' : 'text-slate-900'}`}
                    />
                    <span className="text-slate-500 font-bold">%</span>
                </div>
                <button onClick={() => removeAsset(index)} disabled={portfolioAssets.length <= 2} className={`p-3 rounded-xl transition-all ${isDark ? 'bg-red-900/20 text-red-400 hover:bg-red-900/30' : 'bg-red-50 text-red-500 hover:bg-red-100'} disabled:opacity-30`}>
                    <X className="w-5 h-5" />
                </button>
            </div>
            ))}
            
            <div className={`flex items-center justify-between mt-4 p-4 rounded-xl border ${isDark ? 'bg-[#0f172a] border-slate-700' : 'bg-slate-50 border-slate-200'}`}>
                <span className={`text-sm font-semibold ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Total Allocation</span>
                <div className="flex items-center gap-4">
                    <span className={`text-lg font-mono font-bold ${Math.abs(totalWeight - 100) < 0.01 ? 'text-emerald-500' : 'text-red-500'}`}>
                        {totalWeight.toFixed(2)}%
                    </span>
                    <button onClick={normalizeWeights} className={`px-3 py-1.5 text-xs font-bold rounded-lg ${isDark ? 'bg-slate-800 text-slate-300 hover:bg-slate-700' : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'}`}>
                        Normalize
                    </button>
                </div>
            </div>
        </div>

        {/* Right Col: Settings */}
        <div className="flex flex-col gap-6">
            <div className="grid grid-cols-3 gap-4">
                <div>
                    <label className={`block text-xs font-bold uppercase tracking-wider mb-2 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>History</label>
                    <input type="number" value={years} onChange={(e) => setYears(parseInt(e.target.value))} className={inputClass} />
                </div>
                <div>
                    <label className={`block text-xs font-bold uppercase tracking-wider mb-2 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>Horizon</label>
                    <input type="number" value={horizon} onChange={(e) => setHorizon(parseInt(e.target.value))} className={inputClass} />
                </div>
                <div>
                    <label className={`block text-xs font-bold uppercase tracking-wider mb-2 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>Paths</label>
                    <input type="number" value={numPaths} onChange={(e) => setNumPaths(parseInt(e.target.value))} className={inputClass} />
                </div>
            </div>

            <div>
                <label className={`block text-xs font-bold uppercase tracking-wider mb-3 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>Correlation Model</label>
                <div className="grid grid-cols-2 gap-3">
                    {models.filter(m => m.value !== 'ewma').map(m => {
                        const Icon = m.icon;
                        const isActive = model === m.value;
                        return (
                            <button
                                key={m.value} onClick={() => setModel(m.value)}
                                className={`p-4 rounded-xl border text-left transition-all flex flex-col items-center justify-center gap-2 ${
                                    isActive 
                                    ? (isDark ? 'bg-slate-800 border-slate-600 text-white' : 'bg-slate-900 border-slate-900 text-white') 
                                    : (isDark ? 'bg-[#0f172a] border-slate-800 text-slate-400' : 'bg-white border-slate-200 text-slate-600')
                                }`}
                            >
                                <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'opacity-70'}`} />
                                <span className="text-sm font-bold">{m.label}</span>
                            </button>
                        );
                    })}
                </div>
            </div>

            <button
                onClick={runPortfolioSimulation}
                disabled={portfolioLoading || Math.abs(totalWeight - 100) > 0.01}
                className={`mt-auto w-full font-bold py-4 px-8 rounded-xl transition-all shadow-lg flex items-center justify-center gap-3 ${
                    isDark ? 'bg-white hover:bg-slate-200 text-slate-900 shadow-white/10' : 'bg-slate-900 hover:bg-slate-800 text-white shadow-slate-200'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
                {portfolioLoading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Layers className="w-5 h-5" />}
                {portfolioLoading ? 'Calculating Correlations...' : 'Run Portfolio Simulation'}
            </button>
        </div>
      </div>

      {error && (
        <div className="mt-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-500 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}
    </div>
  );
}

function SingleAssetResults({ results, chartData, numPaths, histogramData, isDark }) {
  // Description dictionary for Single Asset
  const singleAssetInfo = {
    mean: "Average return of all 1000 simulated paths. Positive means uptrend.",
    vol: "Annualized Standard Deviation. Higher % means riskier swings.",
    var: "Value at Risk (95%): In the worst 5% of cases, you lose at least this much.",
    cvar: "Expected Shortfall: The average loss when the crash actually happens.",
    prob: "Probability of Loss: The % of paths that ended below the start price."
  };

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <StatCard title="Mean Return" value={`${(results.risk_stats.mean * 100).toFixed(2)}%`} icon={TrendingUp} color="emerald" trend="positive" isDark={isDark} info={singleAssetInfo.mean} />
        <StatCard title="Volatility" value={`${(results.risk_stats.vol * 100).toFixed(2)}%`} icon={Activity} color="violet" isDark={isDark} info={singleAssetInfo.vol} />
        <StatCard title="VaR (95%)" value={`${(results.risk_stats.VaR_95 * 100).toFixed(2)}%`} icon={Shield} color="rose" trend="negative" isDark={isDark} info={singleAssetInfo.var} />
        <StatCard title="CVaR (95%)" value={`${(results.risk_stats.CVaR_95 * 100).toFixed(2)}%`} icon={TrendingDown} color="orange" trend="negative" isDark={isDark} info={singleAssetInfo.cvar} />
        <StatCard title="Prob. Loss" value={`${(results.risk_stats.prob_loss * 100).toFixed(1)}%`} icon={AlertTriangle} color="amber" isDark={isDark} info={singleAssetInfo.prob} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
            <ChartCard title="Simulated Price Paths" icon={TrendingUp} isDark={isDark}>
            <ResponsiveContainer width="100%" height={320}>
                <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke={isDark ? "#1e293b" : "#e2e8f0"} />
                <XAxis dataKey="day" stroke={isDark ? "#64748b" : "#94a3b8"} hide />
                <YAxis stroke={isDark ? "#64748b" : "#94a3b8"} domain={['auto', 'auto']} />
                <Tooltip content={<CustomTooltip isDark={isDark} />} />
                {results.paths_sample.map((_, idx) => (
                    <Line key={idx} type="monotone" dataKey={`path_${idx}`} stroke={isDark ? "#818cf8" : "#4f46e5"} strokeWidth={1.5} dot={false} strokeOpacity={0.15} isAnimationActive={false} />
                ))}
                </LineChart>
            </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Return Distribution" icon={BarChart3} isDark={isDark}>
            <ResponsiveContainer width="100%" height={320}>
                <BarChart data={histogramData}>
                <CartesianGrid strokeDasharray="3 3" stroke={isDark ? "#1e293b" : "#e2e8f0"} />
                <XAxis dataKey="return" stroke={isDark ? "#64748b" : "#94a3b8"} tickFormatter={(val) => `${(val * 100).toFixed(0)}%`} />
                <YAxis stroke={isDark ? "#64748b" : "#94a3b8"} />
                <Tooltip cursor={{fill: 'transparent'}} contentStyle={{backgroundColor: isDark ? '#0f172a' : '#fff', borderRadius: '8px'}} />
                <Bar dataKey="count" fill={isDark ? "#818cf8" : "#4f46e5"} radius={[4, 4, 0, 0]} />
                </BarChart>
            </ResponsiveContainer>
            </ChartCard>
        </div>
        {/* Extreme Scenarios Added Here */}
        <div className="lg:col-span-1">
            <ExtremeScenarios returns={results.final_returns} isDark={isDark} />
        </div>
      </div>
    </>
  );
}

function PortfolioResults({ portfolioResults, portfolioChartData, correlationData, isDark }) {
  const pieColors = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
  const info = {
    return: "Weighted average return of the entire portfolio basket.",
    sharpe: "Sharpe Ratio: Returns per unit of risk. >1.0 is good, >2.0 is excellent.",
    corr: "Correlation Matrix: +1.0 means assets move together, -1.0 means opposite.",
    contrib: "Risk Contribution: How much each asset adds to total portfolio volatility."
  };

  // Guard against missing data to prevent crash
  if (!portfolioResults || !portfolioResults.portfolio_stats) return null;
  
  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard title="Portfolio Return" value={`${(portfolioResults.portfolio_stats.mean * 100).toFixed(2)}%`} icon={TrendingUp} color="emerald" trend="positive" isDark={isDark} info={info.return} />
        <StatCard title="Volatility" value={`${(portfolioResults.portfolio_stats.volatility * 100).toFixed(2)}%`} icon={Activity} color="violet" isDark={isDark} info="Total Portfolio Risk (Annualized)" />
        <StatCard title="Sharpe Ratio" value={`${portfolioResults.portfolio_stats.sharpe_ratio.toFixed(2)}`} icon={Target} color="blue" isDark={isDark} info={info.sharpe} />
        <StatCard title="VaR (95%)" value={`${(portfolioResults.portfolio_stats.VaR_95 * 100).toFixed(2)}%`} icon={Shield} color="rose" trend="negative" isDark={isDark} info="Max portfolio loss in 95% of cases." />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
            <ChartCard title="Projected Portfolio Value" icon={TrendingUp} isDark={isDark}>
            <ResponsiveContainer width="100%" height={320}>
                <LineChart data={portfolioChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke={isDark ? "#1e293b" : "#e2e8f0"} />
                <XAxis dataKey="day" stroke={isDark ? "#64748b" : "#94a3b8"} hide />
                <YAxis stroke={isDark ? "#64748b" : "#94a3b8"} domain={['auto', 'auto']} />
                <Tooltip content={<CustomTooltip isDark={isDark} />} />
                {portfolioResults.portfolio_paths_sample?.map((_, idx) => (
                    <Line key={idx} type="monotone" dataKey={`path_${idx}`} stroke={isDark ? "#818cf8" : "#4f46e5"} strokeWidth={1.5} dot={false} strokeOpacity={0.15} isAnimationActive={false} />
                ))}
                </LineChart>
            </ResponsiveContainer>
            </ChartCard>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                 {/* Allocation Card - Fixed Logo */}
                <div className={`${isDark ? 'bg-[#151e32] border-slate-700/50' : 'bg-white border-slate-200 shadow-xl shadow-slate-200/50'} rounded-3xl p-6 border transition-all`}>
                    <div className="flex items-center gap-3 mb-4">
                        <div className={`p-2 rounded-xl ${isDark ? 'bg-slate-800 text-white' : 'bg-slate-900 text-white'}`}>
                            <PieChart className="w-5 h-5" /> 
                        </div>
                        <h3 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>Allocation</h3>
                    </div>
                    <div className="h-[180px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <RePieChart>
                                <Pie data={portfolioResults.asset_stats || []} dataKey="contribution" nameKey="ticker" cx="50%" cy="50%" innerRadius={55} outerRadius={75} paddingAngle={5}>
                                    {(portfolioResults.asset_stats || []).map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={pieColors[index % pieColors.length]} />
                                    ))}
                                </Pie>
                                <Tooltip contentStyle={{backgroundColor: isDark ? '#0f172a' : '#fff', borderRadius: '8px'}} />
                            </RePieChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="space-y-2 mt-2">
                        {(portfolioResults.asset_stats || []).map((asset, index) => (
                            <div key={asset.ticker} className="flex justify-between text-sm">
                                <span className={`font-semibold flex items-center gap-2 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: pieColors[index % pieColors.length] }}></span>
                                    {asset.ticker}
                                </span>
                                <span className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                                    {((asset.contribution || 0) * 100).toFixed(1)}% Contrib.
                                </span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className={`${isDark ? 'bg-[#151e32] border-slate-700/50' : 'bg-white border-slate-200 shadow-xl shadow-slate-200/50'} rounded-3xl p-6 border transition-all`}>
                    <div className="flex items-center gap-3 mb-4">
                        <div className={`p-2 rounded-xl ${isDark ? 'bg-slate-800 text-white' : 'bg-slate-900 text-white'}`}>
                            <Layers className="w-5 h-5" />
                        </div>
                        <h3 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>Top Correlations</h3>
                    </div>
                    <div className="space-y-3">
                        {correlationData.slice(0, 4).map((item, idx) => (
                            <div key={idx} className={`flex items-center justify-between p-3 rounded-xl ${isDark ? 'bg-[#0f172a]' : 'bg-slate-50'}`}>
                                <span className={`text-xs font-bold ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{item.pair}</span>
                                <span className={`text-sm font-bold ${item.correlation > 0.7 ? 'text-emerald-500' : item.correlation < -0.5 ? 'text-rose-500' : (isDark ? 'text-white' : 'text-slate-900')}`}>
                                    {item.correlation.toFixed(2)}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>

        {/* Extreme Scenarios Added Here for Portfolio */}
        <div className="lg:col-span-1">
             <ExtremeScenarios returns={portfolioResults.final_returns} isDark={isDark} />
        </div>
      </div>
    </>
  );
}

function StatCard({ title, value, icon: Icon, color, trend, isDark, info }) {
  const colors = {
    emerald: isDark ? 'text-emerald-400 bg-emerald-500/10' : 'text-emerald-600 bg-emerald-50',
    violet: isDark ? 'text-violet-400 bg-violet-500/10' : 'text-violet-600 bg-violet-50',
    rose: isDark ? 'text-rose-400 bg-rose-500/10' : 'text-rose-600 bg-rose-50',
    orange: isDark ? 'text-orange-400 bg-orange-500/10' : 'text-orange-600 bg-orange-50',
    amber: isDark ? 'text-amber-400 bg-amber-500/10' : 'text-amber-600 bg-amber-50',
    blue: isDark ? 'text-blue-400 bg-blue-500/10' : 'text-blue-600 bg-blue-50',
  };

  return (
    <div className={`${isDark ? 'bg-[#151e32] border-slate-700/50' : 'bg-white border-slate-200 shadow-lg shadow-slate-200/50'} rounded-2xl p-6 border transition-all`}>
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-xl ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex items-center gap-2">
            {trend === 'positive' && <TrendingUp className="w-4 h-4 text-emerald-500" />}
            {trend === 'negative' && <TrendingDown className="w-4 h-4 text-rose-500" />}
        </div>
      </div>
      <div>
        <div className="flex items-center gap-1 mb-1">
            <p className={`text-xs font-bold uppercase tracking-wider ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>{title}</p>
            {info && <InfoTooltip text={info} isDark={isDark} />}
        </div>
        <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{value}</p>
      </div>
    </div>
  );
}

function ChartCard({ title, icon: Icon, children, isDark }) {
  return (
    <div className={`${isDark ? 'bg-[#151e32] border-slate-700/50' : 'bg-white border-slate-200 shadow-xl shadow-slate-200/50'} rounded-3xl p-6 border transition-all`}>
      <div className="flex items-center gap-3 mb-6">
        <div className={`p-2 rounded-xl ${isDark ? 'bg-slate-800 text-white' : 'bg-slate-900 text-white'}`}>
          <Icon className="w-5 h-5" />
        </div>
        <h3 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{title}</h3>
      </div>
      {children}
    </div>
  );
}