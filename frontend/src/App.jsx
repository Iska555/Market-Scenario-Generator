import React, { useState, useMemo } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, BarChart, Bar, Area, AreaChart
} from 'recharts';
import { 
  TrendingUp, Activity, AlertTriangle, BarChart3, 
  Zap, Target, PieChart, Download, RefreshCw,
  ChevronRight, Sparkles, Shield, TrendingDown
} from 'lucide-react';

const API_URL = 'https://market-scenario-generator.onrender.com';

export default function MarketScenarioGenerator() {
  const [ticker, setTicker] = useState('SPY');
  const [years, setYears] = useState(3);
  const [horizon, setHorizon] = useState(252);
  const [numPaths, setNumPaths] = useState(1000);
  const [model, setModel] = useState('gaussian');
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
      .map(([ret, count]) => ({
        return: parseFloat(ret),
        count
      }))
      .sort((a, b) => a.return - b.return);
  }, [results]);

  const models = [
    { value: 'gaussian', label: 'Gaussian', icon: Target, desc: 'Normal distribution baseline' },
    { value: 'gmm', label: 'GMM', icon: PieChart, desc: 'Fat-tailed multi-regime' },
    { value: 'ewma', label: 'EWMA', icon: Activity, desc: 'Time-varying volatility' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950">
      {/* Animated Background */}
      <div className="fixed inset-0 opacity-20">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 animate-pulse"></div>
      </div>

      <div className="relative z-10">
        {/* Header */}
        <div className="border-b border-white/10 backdrop-blur-xl bg-slate-900/50">
          <div className="max-w-7xl mx-auto px-8 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-3 rounded-2xl shadow-lg shadow-blue-500/50">
                  <TrendingUp className="w-8 h-8 text-white" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                    Market Scenario Generator
                  </h1>
                  <p className="text-slate-400 text-sm mt-1">
                    Advanced Monte Carlo Risk Simulation Platform
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="px-4 py-2 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-sm font-semibold">
                  <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse mr-2"></span>
                  Live
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
                  className={`px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 ${
                    activeTab === tab.id
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/50'
                      : 'bg-slate-800/50 text-slate-400 hover:bg-slate-800 hover:text-white border border-slate-700/50'
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
              <div className="bg-gradient-to-br from-slate-900/90 to-slate-800/90 backdrop-blur-xl rounded-3xl p-8 mb-8 border border-white/10 shadow-2xl">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 rounded-xl bg-blue-500/20">
                    <Activity className="w-5 h-5 text-blue-400" />
                  </div>
                  <h2 className="text-2xl font-bold text-white">Configuration</h2>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                  <div className="group">
                    <label className="block text-sm font-semibold text-slate-300 mb-3">Ticker Symbol</label>
                    <input
                      type="text"
                      value={ticker}
                      onChange={(e) => setTicker(e.target.value.toUpperCase())}
                      className="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all group-hover:border-slate-600"
                      placeholder="SPY"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-slate-300 mb-3">Historical Years</label>
                    <input
                      type="number"
                      value={years}
                      onChange={(e) => setYears(parseInt(e.target.value))}
                      min="1"
                      max="10"
                      className="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-slate-300 mb-3">Simulation Horizon (days)</label>
                    <input
                      type="number"
                      value={horizon}
                      onChange={(e) => setHorizon(parseInt(e.target.value))}
                      min="1"
                      max="1000"
                      className="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-slate-300 mb-3">Number of Paths</label>
                    <input
                      type="number"
                      value={numPaths}
                      onChange={(e) => setNumPaths(parseInt(e.target.value))}
                      min="100"
                      max="10000"
                      step="100"
                      className="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-semibold text-slate-300 mb-3">Model Type</label>
                    <div className="grid grid-cols-3 gap-3">
                      {models.map(m => {
                        const Icon = m.icon;
                        return (
                          <button
                            key={m.value}
                            onClick={() => setModel(m.value)}
                            className={`p-4 rounded-xl transition-all border-2 ${
                              model === m.value
                                ? 'bg-gradient-to-br from-blue-600 to-purple-600 border-transparent shadow-lg shadow-blue-500/50'
                                : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600'
                            }`}
                          >
                            <Icon className="w-5 h-5 mb-2 mx-auto text-white" />
                            <div className="text-sm font-bold text-white">{m.label}</div>
                            <div className="text-xs text-slate-400 mt-1">{m.desc}</div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <button
                  onClick={runSimulation}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:from-slate-700 disabled:to-slate-600 text-white font-bold py-4 px-8 rounded-xl transition-all shadow-lg shadow-blue-500/50 hover:shadow-xl hover:shadow-blue-500/60 flex items-center justify-center gap-3 group"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      Running Simulation...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5 group-hover:rotate-12 transition-transform" />
                      Run Simulation
                      <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </>
                  )}
                </button>

                {error && (
                  <div className="mt-6 bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-red-200 font-semibold">Simulation Error</p>
                      <p className="text-red-300/80 text-sm mt-1">{error}</p>
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
                      gradient="from-emerald-500 to-teal-600"
                      trend="positive"
                    />
                    <StatCard
                      title="Volatility"
                      value={`${(results.risk_stats.vol * 100).toFixed(2)}%`}
                      icon={Activity}
                      gradient="from-violet-500 to-purple-600"
                    />
                    <StatCard
                      title="VaR (95%)"
                      value={`${(results.risk_stats.VaR_95 * 100).toFixed(2)}%`}
                      icon={Shield}
                      gradient="from-rose-500 to-red-600"
                      trend="negative"
                    />
                    <StatCard
                      title="CVaR (95%)"
                      value={`${(results.risk_stats.CVaR_95 * 100).toFixed(2)}%`}
                      icon={TrendingDown}
                      gradient="from-orange-500 to-amber-600"
                      trend="negative"
                    />
                    <StatCard
                      title="Prob. Loss"
                      value={`${(results.risk_stats.prob_loss * 100).toFixed(1)}%`}
                      icon={AlertTriangle}
                      gradient="from-yellow-500 to-orange-600"
                    />
                  </div>

                  {/* Charts Grid */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Paths Chart */}
                    <ChartCard title="Simulated Price Paths" icon={TrendingUp}>
                      <ResponsiveContainer width="100%" height={320}>
                        <LineChart data={chartData}>
                          <defs>
                            <linearGradient id="pathGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                          <XAxis dataKey="day" stroke="#94a3b8" type="number" domain={[0, horizon]} />
                          <YAxis stroke="#94a3b8" />
                          <Tooltip
                            contentStyle={{ 
                              backgroundColor: '#1e293b', 
                              border: '1px solid #475569',
                              borderRadius: '12px',
                              boxShadow: '0 10px 25px rgba(0,0,0,0.5)'
                            }}
                            labelStyle={{ color: '#e2e8f0', fontWeight: 'bold' }}
                          />
                          {results.paths_sample.map((_, idx) => (
                            <Line
                              key={idx}
                              type="monotone"
                              dataKey={`path_${idx}`}
                              stroke="#3b82f6"
                              strokeWidth={1.5}
                              dot={false}
                              strokeOpacity={0.4}
                              isAnimationActive={false}
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                      <p className="text-sm text-slate-400 mt-4 flex items-center gap-2">
                        <Sparkles className="w-4 h-4" />
                        Showing 50 of {numPaths} paths | Start: ${results.start_price.toFixed(2)}
                      </p>
                    </ChartCard>

                    {/* Distribution Chart */}
                    <ChartCard title="Return Distribution" icon={BarChart3}>
                      <ResponsiveContainer width="100%" height={320}>
                        <BarChart data={histogramData}>
                          <defs>
                            <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.9}/>
                              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.9}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                          <XAxis
                            dataKey="return"
                            stroke="#94a3b8"
                            tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                          />
                          <YAxis stroke="#94a3b8" />
                          <Tooltip
                            contentStyle={{ 
                              backgroundColor: '#1e293b', 
                              border: '1px solid #475569',
                              borderRadius: '12px',
                              boxShadow: '0 10px 25px rgba(0,0,0,0.5)'
                            }}
                            labelFormatter={(val) => `Return: ${(val * 100).toFixed(1)}%`}
                          />
                          <Bar dataKey="count" fill="url(#barGradient)" radius={[8, 8, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                      <p className="text-sm text-slate-400 mt-4 flex items-center gap-2">
                        <Target className="w-4 h-4" />
                        Model: {results.model.toUpperCase()} | Paths: {numPaths}
                      </p>
                    </ChartCard>
                  </div>
                </>
              )}
            </>
          )}

          {activeTab === 'compare' && (
            <div className="bg-gradient-to-br from-slate-900/90 to-slate-800/90 backdrop-blur-xl rounded-3xl p-12 text-center border border-white/10">
              <div className="inline-flex p-6 rounded-full bg-gradient-to-br from-blue-500/20 to-purple-500/20 mb-6">
                <BarChart3 className="w-16 h-16 text-blue-400" />
              </div>
              <h3 className="text-3xl font-bold text-white mb-3">Model Comparison</h3>
              <p className="text-slate-400 mb-6 max-w-md mx-auto">
                Compare Gaussian, GMM, and EWMA models side-by-side with advanced analytics
              </p>
              <div className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400">
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

function StatCard({ title, value, icon: Icon, gradient, trend }) {
  return (
    <div className="group relative">
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-10 rounded-2xl blur-xl transition-opacity group-hover:opacity-20`}></div>
      <div className="relative bg-gradient-to-br from-slate-900/90 to-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-white/10 hover:border-white/20 transition-all">
        <div className="flex items-start justify-between mb-3">
          <div className={`p-2 rounded-xl bg-gradient-to-br ${gradient} bg-opacity-20`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
          {trend === 'positive' && <TrendingUp className="w-4 h-4 text-emerald-400" />}
          {trend === 'negative' && <TrendingDown className="w-4 h-4 text-rose-400" />}
        </div>
        <p className="text-slate-400 text-sm font-medium mb-1">{title}</p>
        <p className="text-3xl font-bold text-white">{value}</p>
      </div>
    </div>
  );
}

function ChartCard({ title, icon: Icon, children }) {
  return (
    <div className="bg-gradient-to-br from-slate-900/90 to-slate-800/90 backdrop-blur-xl rounded-3xl p-6 border border-white/10 shadow-2xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-xl bg-blue-500/20">
          <Icon className="w-5 h-5 text-blue-400" />
        </div>
        <h3 className="text-xl font-bold text-white">{title}</h3>
      </div>
      {children}
    </div>
  );
}