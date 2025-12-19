import React, { useState, useMemo } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, BarChart, Bar
} from 'recharts';
import { 
  TrendingUp, Activity, AlertTriangle, BarChart3, 
  Zap, Target, PieChart, RefreshCw,
  ChevronRight, Sparkles, Shield, TrendingDown, Database
} from 'lucide-react';

const API_URL = 'https://market-scenario-generator.onrender.com';

// --- Dark Mode Efficient Tooltip ---
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const prices = payload.map(p => p.value);
    const max = Math.max(...prices);
    const min = Math.min(...prices);
    const avg = prices.reduce((a, b) => a + b, 0) / prices.length;

    return (
      <div className="bg-slate-900 border border-slate-700 p-4 rounded-xl shadow-2xl backdrop-blur-md">
        <p className="text-slate-400 font-bold mb-2 text-xs uppercase tracking-wider">Day {label}</p>
        <div className="space-y-1 text-sm font-mono">
          <div className="flex justify-between gap-6">
            <span className="text-emerald-400">High:</span>
            <span className="text-white font-semibold">${max.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
          </div>
          <div className="flex justify-between gap-6">
            <span className="text-blue-400">Avg:</span>
            <span className="text-white font-semibold">${avg.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
          </div>
          <div className="flex justify-between gap-6">
            <span className="text-rose-400">Low:</span>
            <span className="text-white font-semibold">${min.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export default function MarketScenarioGenerator() {
  const [ticker, setTicker] = useState('BTC-USD');
  const [years, setYears] = useState(3);
  const [horizon, setHorizon] = useState(252);
  const [numPaths, setNumPaths] = useState(1000);
  const [model, setModel] = useState('gmm');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('simulate');

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
    { value: 'gaussian', label: 'Gaussian', icon: Target, desc: 'Normal distribution baseline' },
    { value: 'gmm', label: 'GMM', icon: PieChart, desc: 'Fat-tailed multi-regime' },
    { value: 'ewma', label: 'EWMA', icon: Activity, desc: 'Time-varying volatility' }
  ];

  return (
    <div className="min-h-screen bg-[#0B1120] text-white">
      {/* Background Ambience */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] bg-blue-600/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] bg-purple-600/20 rounded-full blur-[120px]" />
      </div>

      <div className="relative z-10">
        {/* Header */}
        <div className="border-b border-white/5 bg-slate-900/50 backdrop-blur-xl">
          <div className="max-w-7xl mx-auto px-8 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="bg-white p-2.5 rounded-xl shadow-lg shadow-white/5">
                  <TrendingUp className="w-6 h-6 text-slate-900" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-white tracking-tight">
                    Market Scenario Generator
                  </h1>
                  <p className="text-slate-400 text-xs font-medium tracking-wide uppercase mt-0.5">
                    Advanced Monte Carlo Risk Simulation
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold flex items-center gap-2">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  Live System
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-8 py-8">
          {/* Tabs */}
          <div className="flex gap-2 mb-8">
            {[
              { id: 'simulate', label: 'Simulate', icon: Zap },
              { id: 'compare', label: 'Compare Models', icon: BarChart3 }
            ].map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-5 py-2.5 rounded-lg font-medium text-sm transition-all flex items-center gap-2 ${
                    activeTab === tab.id
                      ? 'bg-slate-200 text-slate-900 shadow-lg shadow-white/5'
                      : 'bg-slate-800/50 text-slate-400 hover:bg-slate-800 hover:text-white border border-transparent hover:border-white/5'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {activeTab === 'simulate' && (
            <>
              {/* Configuration Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 mb-8 shadow-2xl shadow-black/20">
                <div className="flex items-center gap-3 mb-8">
                  <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
                    <Activity className="w-5 h-5 text-blue-400" />
                  </div>
                  <h2 className="text-xl font-bold text-white">Configuration</h2>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
                  <div className="group">
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Ticker Symbol</label>
                    <input
                      type="text"
                      value={ticker}
                      onChange={(e) => setTicker(e.target.value.toUpperCase())}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3.5 text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all font-mono"
                      placeholder="BTC-USD"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">History (Years)</label>
                    <input
                      type="number"
                      value={years}
                      onChange={(e) => setYears(parseInt(e.target.value))}
                      min="1"
                      max="10"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Horizon (Days)</label>
                    <input
                      type="number"
                      value={horizon}
                      onChange={(e) => setHorizon(parseInt(e.target.value))}
                      min="1"
                      max="1000"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Monte Carlo Paths</label>
                    <input
                      type="number"
                      value={numPaths}
                      onChange={(e) => setNumPaths(parseInt(e.target.value))}
                      min="100"
                      max="10000"
                      step="100"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all font-mono"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Statistical Model</label>
                    <div className="grid grid-cols-3 gap-4">
                      {models.map(m => {
                        const Icon = m.icon;
                        const isActive = model === m.value;
                        return (
                          <button
                            key={m.value}
                            onClick={() => setModel(m.value)}
                            className={`p-4 rounded-xl transition-all border ${
                              isActive
                                ? 'bg-slate-200 border-white text-slate-900 shadow-lg shadow-white/5'
                                : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                            }`}
                          >
                            <Icon className={`w-5 h-5 mb-2 mx-auto ${isActive ? 'text-slate-900' : 'text-slate-500'}`} />
                            <div className="text-sm font-bold">{m.label}</div>
                            <div className={`text-[10px] mt-1 ${isActive ? 'text-slate-600' : 'text-slate-600'}`}>{m.desc}</div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <button
                  onClick={runSimulation}
                  disabled={loading}
                  className="w-full bg-slate-200 hover:bg-white disabled:bg-slate-800 disabled:text-slate-600 text-slate-900 font-bold py-4 px-8 rounded-xl transition-all shadow-lg shadow-white/5 hover:shadow-xl hover:shadow-white/10 flex items-center justify-center gap-3 group relative overflow-hidden"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      Initializing Engine...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5 text-indigo-600 group-hover:rotate-12 transition-transform" />
                      Run Risk Simulation
                      <ChevronRight className="w-5 h-5 text-slate-400 group-hover:translate-x-1 transition-transform" />
                    </>
                  )}
                </button>

                {error && (
                  <div className="mt-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-red-200 font-semibold text-sm">Simulation Error</p>
                      <p className="text-red-400/80 text-xs mt-1">{error}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Results */}
              {results && (
                <>
                  {/* Stats Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
                    <StatCard
                      title="Mean Return"
                      value={`${(results.risk_stats.mean * 100).toFixed(2)}%`}
                      icon={TrendingUp}
                      color="emerald"
                      trend="positive"
                    />
                    <StatCard
                      title="Volatility"
                      value={`${(results.risk_stats.vol * 100).toFixed(2)}%`}
                      icon={Activity}
                      color="violet"
                    />
                    <StatCard
                      title="VaR (95%)"
                      value={`${(results.risk_stats.VaR_95 * 100).toFixed(2)}%`}
                      icon={Shield}
                      color="rose"
                      trend="negative"
                    />
                    <StatCard
                      title="CVaR (95%)"
                      value={`${(results.risk_stats.CVaR_95 * 100).toFixed(2)}%`}
                      icon={TrendingDown}
                      color="orange"
                      trend="negative"
                    />
                    <StatCard
                      title="Prob. Loss"
                      value={`${(results.risk_stats.prob_loss * 100).toFixed(1)}%`}
                      icon={AlertTriangle}
                      color="amber"
                    />
                  </div>

                  {/* Charts Grid */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Paths Chart */}
                    <ChartCard title="Simulated Price Paths" icon={TrendingUp}>
                      <ResponsiveContainer width="100%" height={320}>
                        <LineChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis dataKey="day" stroke="#64748b" type="number" domain={[0, horizon]} tick={{fontSize: 12}} />
                          <YAxis stroke="#64748b" tick={{fontSize: 12}} />
                          <Tooltip content={<CustomTooltip />} />
                          {results.paths_sample.map((_, idx) => (
                            <Line
                              key={idx}
                              type="monotone"
                              dataKey={`path_${idx}`}
                              stroke="#3b82f6"
                              strokeWidth={1}
                              dot={false}
                              strokeOpacity={0.2} // Reduced opacity for GMM look
                              isAnimationActive={false}
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                      <p className="text-xs text-slate-500 mt-4 flex items-center gap-2 font-mono">
                        <Database className="w-3 h-3" />
                        Showing 50 of {numPaths} paths | Start: ${results.start_price.toFixed(2)}
                      </p>
                    </ChartCard>

                    {/* Distribution Chart */}
                    <ChartCard title="Return Distribution" icon={BarChart3}>
                      <ResponsiveContainer width="100%" height={320}>
                        <BarChart data={histogramData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis
                            dataKey="return"
                            stroke="#64748b"
                            tick={{fontSize: 12}}
                            tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                          />
                          <YAxis stroke="#64748b" tick={{fontSize: 12}} />
                          <Tooltip
                            cursor={{fill: '#1e293b'}}
                            contentStyle={{ 
                              backgroundColor: '#0f172a', 
                              border: '1px solid #334155',
                              borderRadius: '12px',
                              color: '#fff'
                            }}
                            labelFormatter={(val) => `Return: ${(val * 100).toFixed(1)}%`}
                          />
                          <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                      <p className="text-xs text-slate-500 mt-4 flex items-center gap-2 font-mono">
                        <Target className="w-3 h-3" />
                        Model: {results.model.toUpperCase()} | Paths: {numPaths}
                      </p>
                    </ChartCard>
                  </div>
                </>
              )}
            </>
          )}

          {activeTab === 'compare' && (
            <div className="bg-slate-900 rounded-3xl p-12 text-center border border-slate-800 shadow-2xl">
              <div className="inline-flex p-6 rounded-full bg-slate-950 mb-6 border border-slate-800">
                <BarChart3 className="w-16 h-16 text-slate-700" />
              </div>
              <h3 className="text-3xl font-bold text-white mb-3">Model Comparison</h3>
              <p className="text-slate-400 mb-8 max-w-md mx-auto">
                Compare Gaussian, GMM, and EWMA models side-by-side
              </p>
              <div className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400">
                <Sparkles className="w-4 h-4 animate-pulse" />
                <span className="text-sm font-semibold">Coming Soon</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon: Icon, color, trend }) {
  const colors = {
    emerald: 'from-emerald-500/20 to-teal-500/5 text-emerald-400 border-emerald-500/20',
    violet: 'from-violet-500/20 to-purple-500/5 text-violet-400 border-violet-500/20',
    rose: 'from-rose-500/20 to-red-500/5 text-rose-400 border-rose-500/20',
    orange: 'from-orange-500/20 to-amber-500/5 text-orange-400 border-orange-500/20',
    amber: 'from-amber-500/20 to-yellow-500/5 text-amber-400 border-amber-500/20'
  };

  return (
    <div className="group relative">
      <div className={`bg-slate-900 rounded-2xl p-6 border ${colors[color].split(' ').pop()} transition-all hover:bg-slate-800`}>
        <div className="flex items-start justify-between mb-3">
          <div className={`p-2 rounded-lg bg-gradient-to-br ${colors[color].split(' ').slice(0, 2).join(' ')}`}>
            <Icon className={`w-5 h-5 ${colors[color].split(' ')[2]}`} />
          </div>
          {trend === 'positive' && <TrendingUp className="w-4 h-4 text-emerald-500" />}
          {trend === 'negative' && <TrendingDown className="w-4 h-4 text-rose-500" />}
        </div>
        <p className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">{title}</p>
        <p className="text-2xl font-bold text-white">{value}</p>
      </div>
    </div>
  );
}

function ChartCard({ title, icon: Icon, children }) {
  return (
    <div className="bg-slate-900 rounded-3xl p-6 border border-slate-800 shadow-xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-slate-800 border border-slate-700">
          <Icon className="w-5 h-5 text-blue-400" />
        </div>
        <h3 className="text-lg font-bold text-white">{title}</h3>
      </div>
      {children}
    </div>
  );
}