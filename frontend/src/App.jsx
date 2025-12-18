import React, { useState, useMemo } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, BarChart, Bar, Cell
} from 'recharts';
import { 
  TrendingUp, Activity, AlertTriangle, BarChart3, 
  Zap, Target, PieChart, RefreshCw,
  ChevronRight, Sparkles, Shield, TrendingDown, Info
} from 'lucide-react';
import './index.css';

// ✅ Ensure this URL is correct!
const API_URL = 'https://market-scenario-generator.onrender.com';

export default function MarketScenarioGenerator() {
  const [ticker, setTicker] = useState('BTC-USD');
  const [years, setYears] = useState(3);
  const [horizon, setHorizon] = useState(30);
  const [numPaths, setNumPaths] = useState(200);
  const [model, setModel] = useState('ewma');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/simulate`, {
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
    { value: 'gaussian', label: 'Gaussian', desc: 'Standard Walk' },
    { value: 'gmm', label: 'GMM', desc: 'Fat-Tail Risk' },
    { value: 'ewma', label: 'EWMA', desc: 'Vol Clustering' }
  ];

  return (
    <div className="min-h-screen bg-[#050505] text-white p-6 md:p-12 font-sans selection:bg-[#00ff9d] selection:text-black">
      <div className="max-w-7xl mx-auto">
        
        {/* Header - Quantro Style: Minimal & Big */}
        <header className="mb-12 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-5xl font-bold tracking-tight text-white mb-2">
              Market<span className="text-[#00ff9d]">Sim</span>
            </h1>
            <p className="text-[#888888] text-lg">Advanced Stochastic Scenarios</p>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-[#111] rounded-full border border-[#222]">
            <div className="w-2 h-2 rounded-full bg-[#00ff9d] animate-pulse"></div>
            <span className="text-sm font-medium text-[#ccc]">System Active</span>
          </div>
        </header>

        {/* Input Configuration - "Island" Style */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-12">
          
          {/* Left: Controls */}
          <div className="lg:col-span-4 space-y-6">
            <div className="fintech-card p-6">
              <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <Target className="w-5 h-5 text-[#00ff9d]" /> Configuration
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-bold text-[#666] uppercase mb-1 block">Asset</label>
                  <input 
                    type="text" 
                    value={ticker} 
                    onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    className="fintech-input w-full p-3 font-mono text-lg"
                    placeholder="BTC-USD"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold text-[#666] uppercase mb-1 block">Years</label>
                    <input 
                      type="number" 
                      value={years} 
                      onChange={(e) => setYears(e.target.value)}
                      className="fintech-input w-full p-3"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold text-[#666] uppercase mb-1 block">Horizon (Days)</label>
                    <input 
                      type="number" 
                      value={horizon} 
                      onChange={(e) => setHorizon(e.target.value)}
                      className="fintech-input w-full p-3"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-bold text-[#666] uppercase mb-1 block">Model</label>
                  <div className="grid grid-cols-3 gap-2">
                    {models.map(m => (
                      <button
                        key={m.value}
                        onClick={() => setModel(m.value)}
                        className={`p-2 rounded-lg text-xs font-medium transition-all border ${
                          model === m.value
                            ? 'bg-[#00ff9d] text-black border-[#00ff9d]'
                            : 'bg-[#0a0a0a] text-[#888] border-[#333] hover:border-[#666]'
                        }`}
                      >
                        {m.label}
                      </button>
                    ))}
                  </div>
                </div>

                <button 
                  onClick={runSimulation}
                  disabled={loading}
                  className="neon-button w-full py-4 mt-4 flex items-center justify-center gap-2 text-lg"
                >
                  {loading ? <RefreshCw className="animate-spin" /> : <Zap fill="currentColor" />}
                  {loading ? 'Crunching Numbers...' : 'Generate Scenarios'}
                </button>
              </div>
            </div>
            
            {/* Error Display */}
            {error && (
              <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-xl text-red-400 flex items-center gap-3">
                <AlertTriangle className="w-5 h-5" />
                {error}
              </div>
            )}
          </div>

          {/* Right: Visualization Area */}
          <div className="lg:col-span-8 space-y-6">
            {results ? (
              <>
                {/* Key Metrics - Huge Numbers like Quantro */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <MetricItem label="Projected Mean" value={`${(results.risk_stats.mean * 100).toFixed(2)}%`} color="#00ff9d" />
                  <MetricItem label="Volatility" value={`${(results.risk_stats.vol * 100).toFixed(2)}%`} color="#a855f7" />
                  <MetricItem label="VaR (95%)" value={`${(results.risk_stats.VaR_95 * 100).toFixed(2)}%`} color="#ef4444" />
                  <MetricItem label="Win Probability" value={`${(100 - results.risk_stats.prob_loss * 100).toFixed(1)}%`} color="#3b82f6" />
                </div>

                {/* Main Chart */}
                <div className="fintech-card p-6 h-[400px]">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-medium text-[#ccc]">Price Simulation Paths</h3>
                    <span className="text-xs text-[#666] font-mono">{numPaths} Iterations</span>
                  </div>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <defs>
                        <linearGradient id="neonGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#00ff9d" stopOpacity={0.2}/>
                          <stop offset="95%" stopColor="#00ff9d" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                      <XAxis dataKey="day" hide />
                      <YAxis 
                        stroke="#444" 
                        tick={{fill: '#666', fontSize: 10}}
                        tickFormatter={(val) => `$${val.toLocaleString()}`}
                        domain={['auto', 'auto']}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#111', borderColor: '#333', color: '#fff' }}
                        itemStyle={{ color: '#00ff9d' }}
                        labelFormatter={() => ''}
                        formatter={(val) => [`$${val.toFixed(2)}`, 'Price']}
                      />
                      {/* Render limited paths for performance but sleek look */}
                      {Object.keys(results.paths_sample[0] || {})
                        .filter(key => key.startsWith('path_'))
                        .slice(0, 50) 
                        .map((key, idx) => (
                          <Line
                            key={key}
                            type="monotone"
                            dataKey={key}
                            stroke="#00ff9d"
                            strokeWidth={1}
                            dot={false}
                            opacity={0.15}
                          />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Histogram */}
                <div className="fintech-card p-6 h-[250px]">
                  <h3 className="text-lg font-medium text-[#ccc] mb-4">Risk Distribution</h3>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={histogramData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                      <XAxis 
                        dataKey="return" 
                        stroke="#444" 
                        tickFormatter={(val) => `${(val * 100).toFixed(0)}%`} 
                        tick={{fill: '#666', fontSize: 10}}
                      />
                      <Tooltip 
                        cursor={{fill: 'rgba(255,255,255,0.05)'}}
                        contentStyle={{ backgroundColor: '#111', borderColor: '#333' }}
                      />
                      <Bar dataKey="count">
                        {histogramData.map((entry, index) => (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={entry.return >= 0 ? '#00ff9d' : '#ef4444'} 
                            opacity={entry.return >= 0 ? 0.8 : 0.6}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </>
            ) : (
              // Empty State
              <div className="h-full flex flex-col items-center justify-center fintech-card p-12 text-center opacity-50">
                <BarChart3 className="w-16 h-16 text-[#333] mb-4" />
                <p className="text-[#666]">Configure simulation to view scenarios</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Minimal Metric Component
function MetricItem({ label, value, color }) {
  return (
    <div className="fintech-card p-5 flex flex-col justify-between">
      <span className="text-xs text-[#666] font-bold uppercase tracking-wider">{label}</span>
      <span className="text-2xl md:text-3xl font-bold mt-2" style={{ color: color }}>
        {value}
      </span>
    </div>
  );
}