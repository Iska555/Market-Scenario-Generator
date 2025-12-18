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
    <div className="min-h-screen bg-black text-gray-100 font-sans selection:bg-blue-500/30">
      
      <div className="relative z-10">
        {/* Header */}
        <div className="border-b border-gray-800 bg-black/50 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="bg-gray-900 p-2.5 rounded-xl border border-gray-800">
                  <TrendingUp className="w-6 h-6 text-blue-500" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-white tracking-tight">
                    Market<span className="text-blue-500">Scenario</span>
                  </h1>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
                  System Operational
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">
          {/* Tabs */}
          <div className="flex gap-2 mb-8 bg-gray-900/50 p-1 rounded-xl w-fit border border-gray-800">
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
                      ? 'bg-gray-800 text-white shadow-sm border border-gray-700'
                      : 'text-gray-500 hover:text-gray-300'
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
              <div className="bg-gray-900/40 backdrop-blur-sm rounded-2xl p-6 mb-8 border border-gray-800">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 rounded-lg bg-gray-800/50">
                    <Activity className="w-5 h-5 text-gray-400" />
                  </div>
                  <h2 className="text-lg font-semibold text-white">Simulation Parameters</h2>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                  <div className="group">
                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Ticker Symbol</label>
                    <input
                      type="text"
                      value={ticker}
                      onChange={(e) => setTicker(e.target.value.toUpperCase())}
                      className="w-full bg-black border border-gray-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all font-mono"
                      placeholder="SPY"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">History (Years)</label>
                    <input
                      type="number"
                      value={years}
                      onChange={(e) => setYears(parseInt(e.target.value))}
                      min="1"
                      max="10"
                      className="w-full bg-black border border-gray-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Horizon (Days)</label>
                    <input
                      type="number"
                      value={horizon}
                      onChange={(e) => setHorizon(parseInt(e.target.value))}
                      min="1"
                      max="1000"
                      className="w-full bg-black border border-gray-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Paths</label>
                    <input
                      type="number"
                      value={numPaths}
                      onChange={(e) => setNumPaths(parseInt(e.target.value))}
                      min="100"
                      max="10000"
                      step="100"
                      className="w-full bg-black border border-gray-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all font-mono"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Statistical Model</label>
                    <div className="grid grid-cols-3 gap-3">
                      {models.map(m => {
                        const Icon = m.icon;
                        return (
                          <button
                            key={m.value}
                            onClick={() => setModel(m.value)}
                            className={`p-3 rounded-lg transition-all border text-left ${
                              model === m.value
                                ? 'bg-blue-600/10 border-blue-500/50 text-blue-400'
                                : 'bg-black border-gray-800 text-gray-400 hover:border-gray-700'
                            }`}
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <Icon className="w-4 h-4" />
                              <span className="font-semibold text-sm">{m.label}</span>
                            </div>
                            <div className="text-[10px] opacity-70 truncate">{m.desc}</div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <button
                  onClick={runSimulation}
                  disabled={loading}
                  className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-500 text-white font-semibold py-4 px-8 rounded-lg transition-all shadow-lg shadow-blue-900/20 flex items-center justify-center gap-3"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5" />
                      Run Simulation
                      <ChevronRight className="w-5 h-5 opacity-70" />
                    </>
                  )}
                </button>

                {error && (
                  <div className="mt-6 bg-red-900/10 border border-red-900/30 rounded-lg p-4 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-red-400 font-semibold text-sm">Simulation Error</p>
                      <p className="text-red-400/70 text-sm mt-1">{error}</p>
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
                      accentColor="text-blue-400"
                      borderColor="border-blue-500/30"
                    />
                    <StatCard
                      title="Volatility"
                      value={`${(results.risk_stats.vol * 100).toFixed(2)}%`}
                      icon={Activity}
                      accentColor="text-gray-300"
                      borderColor="border-gray-600/30"
                    />
                    <StatCard
                      title="VaR (95%)"
                      value={`${(results.risk_stats.VaR_95 * 100).toFixed(2)}%`}
                      icon={Shield}
                      accentColor="text-blue-300"
                      borderColor="border-blue-400/30"
                    />
                    <StatCard
                      title="CVaR (95%)"
                      value={`${(results.risk_stats.CVaR_95 * 100).toFixed(2)}%`}
                      icon={TrendingDown}
                      accentColor="text-gray-400"
                      borderColor="border-gray-500/30"
                    />
                    <StatCard
                      title="Prob. Loss"
                      value={`${(results.risk_stats.prob_loss * 100).toFixed(1)}%`}
                      icon={AlertTriangle}
                      accentColor="text-gray-400"
                      borderColor="border-gray-500/30"
                    />
                  </div>

                  {/* Charts Grid */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Paths Chart */}
                    <ChartCard title="Simulated Price Paths" icon={TrendingUp}>
                      <ResponsiveContainer width="100%" height={320}>
                        <LineChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                          <XAxis dataKey="day" stroke="#4b5563" type="number" domain={[0, horizon]} tick={{fontSize: 12}} />
                          <YAxis stroke="#4b5563" tick={{fontSize: 12}} />
                          <Tooltip
                            contentStyle={{ 
                              backgroundColor: '#000', 
                              border: '1px solid #333',
                              borderRadius: '8px',
                            }}
                            labelStyle={{ color: '#9ca3af' }}
                          />
                          {results.paths_sample.map((_, idx) => (
                            <Line
                              key={idx}
                              type="monotone"
                              dataKey={`path_${idx}`}
                              stroke="#3b82f6"
                              strokeWidth={1}
                              dot={false}
                              strokeOpacity={0.15}
                              isAnimationActive={false}
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                      <p className="text-xs text-gray-500 mt-4 font-mono">
                        Showing 50 of {numPaths} paths | Start: ${results.start_price.toFixed(2)}
                      </p>
                    </ChartCard>

                    {/* Distribution Chart */}
                    <ChartCard title="Return Distribution" icon={BarChart3}>
                      <ResponsiveContainer width="100%" height={320}>
                        <BarChart data={histogramData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                          <XAxis
                            dataKey="return"
                            stroke="#4b5563"
                            tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                            tick={{fontSize: 12}}
                          />
                          <YAxis stroke="#4b5563" tick={{fontSize: 12}} />
                          <Tooltip
                            contentStyle={{ 
                              backgroundColor: '#000', 
                              border: '1px solid #333',
                              borderRadius: '8px',
                            }}
                            labelFormatter={(val) => `Return: ${(val * 100).toFixed(1)}%`}
                            labelStyle={{ color: '#9ca3af' }}
                          />
                          <Bar dataKey="count" fill="#3b82f6" radius={[2, 2, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                      <p className="text-xs text-gray-500 mt-4 font-mono">
                        Model: {results.model.toUpperCase()} | Paths: {numPaths}
                      </p>
                    </ChartCard>
                  </div>
                </>
              )}
            </>
          )}

          {activeTab === 'compare' && (
            <div className="bg-gray-900/40 rounded-2xl p-12 text-center border border-gray-800">
              <div className="inline-flex p-4 rounded-full bg-gray-800 mb-6">
                <BarChart3 className="w-12 h-12 text-blue-500" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">Model Comparison</h3>
              <p className="text-gray-500 mb-6">Coming soon</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon: Icon, accentColor, borderColor }) {
  return (
    <div className={`bg-black rounded-xl p-5 border ${borderColor} hover:border-gray-600 transition-all`}>
      <div className="flex items-start justify-between mb-3">
        <div className="p-2 rounded-lg bg-gray-900">
          <Icon className={`w-4 h-4 ${accentColor}`} />
        </div>
      </div>
      <p className="text-gray-500 text-xs font-medium uppercase tracking-wider mb-1">{title}</p>
      <p className={`text-2xl font-bold ${accentColor}`}>{value}</p>
    </div>
  );
}

function ChartCard({ title, icon: Icon, children }) {
  return (
    <div className="bg-gray-900/20 rounded-2xl p-6 border border-gray-800">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-gray-800">
          <Icon className="w-4 h-4 text-blue-500" />
        </div>
        <h3 className="text-sm font-bold text-gray-200 uppercase tracking-wide">{title}</h3>
      </div>
      {children}
    </div>
  );
}