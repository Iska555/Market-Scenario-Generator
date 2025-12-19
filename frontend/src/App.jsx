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

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const prices = payload.map(p => p.value);
    const max = Math.max(...prices);
    const min = Math.min(...prices);
    const avg = prices.reduce((a, b) => a + b, 0) / prices.length;

    return (
      <div className="bg-white border border-slate-200 p-4 rounded-2xl shadow-2xl">
        <p className="text-slate-600 font-bold mb-2 text-xs uppercase tracking-wider">Day {label}</p>
        <div className="space-y-1 text-sm font-mono">
          <div className="flex justify-between gap-6">
            <span className="text-emerald-600">High:</span>
            <span className="text-slate-900 font-semibold">${max.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
          </div>
          <div className="flex justify-between gap-6">
            <span className="text-slate-600">Avg:</span>
            <span className="text-slate-900 font-semibold">${avg.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
          </div>
          <div className="flex justify-between gap-6">
            <span className="text-rose-600">Low:</span>
            <span className="text-slate-900 font-semibold">${min.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
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
                  Monte Carlo Risk Simulation Platform
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
            { id: 'simulate', label: 'Simulate', icon: Zap },
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

        {activeTab === 'simulate' && (
          <>
            {/* Configuration Card */}
            <div className="bg-white rounded-3xl p-8 mb-8 border border-slate-200 shadow-xl shadow-slate-200/50">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-xl bg-slate-900">
                  <Activity className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-slate-900">Configuration</h2>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div className="group">
                  <label className="block text-sm font-semibold text-slate-700 mb-3">Ticker Symbol</label>
                  <input
                    type="text"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent transition-all group-hover:border-slate-300 font-semibold"
                    placeholder="SPY"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-3">Historical Years</label>
                  <input
                    type="number"
                    value={years}
                    onChange={(e) => setYears(parseInt(e.target.value))}
                    min="1"
                    max="10"
                    className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900 transition-all font-semibold"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-3">Simulation Horizon (days)</label>
                  <input
                    type="number"
                    value={horizon}
                    onChange={(e) => setHorizon(parseInt(e.target.value))}
                    min="1"
                    max="1000"
                    className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900 transition-all font-semibold"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-3">Number of Paths</label>
                  <input
                    type="number"
                    value={numPaths}
                    onChange={(e) => setNumPaths(parseInt(e.target.value))}
                    min="100"
                    max="10000"
                    step="100"
                    className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900 transition-all font-semibold"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-semibold text-slate-700 mb-3">Model Type</label>
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
                          <div className={`text-xs mt-1 ${isActive ? 'text-slate-300' : 'text-slate-600'}`}>{m.desc}</div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              <button
                onClick={runSimulation}
                disabled={loading}
                className="w-full bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 disabled:text-slate-500 text-white font-bold py-4 px-8 rounded-2xl transition-all shadow-lg shadow-slate-900/20 hover:shadow-xl hover:shadow-slate-900/30 flex items-center justify-center gap-3 group"
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
                <div className="mt-6 bg-red-50 border border-red-200 rounded-2xl p-4 flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-red-900 font-semibold">Simulation Error</p>
                    <p className="text-red-700 text-sm mt-1">{error}</p>
                  </div>
                </div>
              )}
            </div>

            {/* Results */}
            {results && (
              <>
                {/* Stats Grid - Bento Style */}
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
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="day" stroke="#64748b" type="number" domain={[0, horizon]} />
                        <YAxis stroke="#64748b" />
                        <Tooltip content={<CustomTooltip />} />
                        {results.paths_sample.map((_, idx) => (
                          <Line
                            key={idx}
                            type="monotone"
                            dataKey={`path_${idx}`}
                            stroke="#0f172a"
                            strokeWidth={1.5}
                            dot={false}
                            strokeOpacity={0.15}
                            isAnimationActive={false}
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                    <p className="text-sm text-slate-600 mt-4 flex items-center gap-2">
                      <Database className="w-4 h-4" />
                      Showing 50 of {numPaths} paths | Start: ${results.start_price.toFixed(2)}
                    </p>
                  </ChartCard>

                  {/* Distribution Chart */}
                  <ChartCard title="Return Distribution" icon={BarChart3}>
                    <ResponsiveContainer width="100%" height={320}>
                      <BarChart data={histogramData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis
                          dataKey="return"
                          stroke="#64748b"
                          tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                        />
                        <YAxis stroke="#64748b" />
                        <Tooltip
                          contentStyle={{ 
                            backgroundColor: '#ffffff', 
                            border: '1px solid #e2e8f0',
                            borderRadius: '16px',
                            boxShadow: '0 10px 25px rgba(0,0,0,0.1)'
                          }}
                          labelFormatter={(val) => `Return: ${(val * 100).toFixed(1)}%`}
                        />
                        <Bar dataKey="count" fill="#0f172a" radius={[8, 8, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="text-sm text-slate-600 mt-4 flex items-center gap-2">
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

function StatCard({ title, value, icon: Icon, color, trend }) {
  const colors = {
    emerald: 'from-emerald-500 to-teal-600',
    violet: 'from-violet-500 to-purple-600',
    rose: 'from-rose-500 to-red-600',
    orange: 'from-orange-500 to-amber-600',
    amber: 'from-amber-500 to-yellow-600'
  };

  return (
    <div className="group relative">
      <div className="bg-white rounded-2xl p-6 border border-slate-200 hover:border-slate-300 transition-all shadow-lg shadow-slate-200/50 hover:shadow-xl hover:shadow-slate-200/60">
        <div className="flex items-start justify-between mb-3">
          <div className={`p-2 rounded-xl bg-gradient-to-br ${colors[color]} shadow-lg`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
          {trend === 'positive' && <TrendingUp className="w-4 h-4 text-emerald-600" />}
          {trend === 'negative' && <TrendingDown className="w-4 h-4 text-rose-600" />}
        </div>
        <p className="text-slate-600 text-sm font-semibold mb-1">{title}</p>
        <p className="text-3xl font-bold text-slate-900">{value}</p>
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