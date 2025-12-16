import React, { useState, useMemo } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, BarChart, Bar 
} from 'recharts';
import { TrendingUp, Activity, AlertTriangle, BarChart3 } from 'lucide-react';

const API_URL = "https://market-scenario-backend.onrender.com";

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

  // --- FIXED DATA TRANSFORMATION LOGIC ---
  // This pivots the data: Array of Days -> Object containing prices for all paths on that day
  const chartData = useMemo(() => {
    if (!results?.paths_sample) return [];
    
    // Create an array for every day in the horizon
    return Array.from({ length: horizon }, (_, dayIndex) => {
      const dayData = { day: dayIndex };
      
      // For this specific day, grab the price from every path
      results.paths_sample.forEach((path, pathIdx) => {
        dayData[`path_${pathIdx}`] = path[dayIndex];
      });
      
      return dayData;
    });
  }, [results, horizon]);

  // Histogram Logic (Unchanged)
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
            <TrendingUp className="w-10 h-10 text-blue-400" />
            Market Scenario Generator
          </h1>
          <p className="text-slate-400">Monte Carlo simulation for financial risk analysis</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b border-slate-700">
          <button
            onClick={() => setActiveTab('simulate')}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === 'simulate' 
                ? 'border-b-2 border-blue-400 text-blue-400' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Simulate
          </button>
          <button
            onClick={() => setActiveTab('compare')}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === 'compare' 
                ? 'border-b-2 border-blue-400 text-blue-400' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Compare Models
          </button>
        </div>

        {activeTab === 'simulate' && (
          <>
            {/* Configuration Panel */}
            <div className="bg-slate-800 rounded-lg p-6 mb-6 shadow-xl">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5" />
                Configuration
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm font-medium mb-2">Ticker Symbol</label>
                  <input
                    type="text"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="SPY"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Historical Years</label>
                  <input
                    type="number"
                    value={years}
                    onChange={(e) => setYears(parseInt(e.target.value))}
                    min="1"
                    max="10"
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Simulation Horizon (days)</label>
                  <input
                    type="number"
                    value={horizon}
                    onChange={(e) => setHorizon(parseInt(e.target.value))}
                    min="1"
                    max="1000"
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Number of Paths</label>
                  <input
                    type="number"
                    value={numPaths}
                    onChange={(e) => setNumPaths(parseInt(e.target.value))}
                    min="100"
                    max="10000"
                    step="100"
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Model Type</label>
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="gaussian">Gaussian (Normal)</option>
                    <option value="gmm">GMM (Fat-tailed)</option>
                    <option value="ewma">EWMA (Time-varying Vol)</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <button
                    onClick={runSimulation}
                    disabled={loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-semibold py-2 px-6 rounded transition-colors"
                  >
                    {loading ? 'Running...' : 'Run Simulation'}
                  </button>
                </div>
              </div>

              {error && (
                <div className="mt-4 bg-red-900/50 border border-red-700 rounded p-4 flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <p className="text-red-200">{error}</p>
                </div>
              )}
            </div>

            {/* Results */}
            {results && (
              <>
                {/* Risk Metrics Cards */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                  <MetricCard 
                    title="Mean Return" 
                    value={`${(results.risk_stats.mean * 100).toFixed(2)}%`}
                    color="blue"
                  />
                  <MetricCard 
                    title="Volatility" 
                    value={`${(results.risk_stats.vol * 100).toFixed(2)}%`}
                    color="purple"
                  />
                  <MetricCard 
                    title="VaR (95%)" 
                    value={`${(results.risk_stats.VaR_95 * 100).toFixed(2)}%`}
                    color="red"
                  />
                  <MetricCard 
                    title="CVaR (95%)" 
                    value={`${(results.risk_stats.CVaR_95 * 100).toFixed(2)}%`}
                    color="orange"
                  />
                  <MetricCard 
                    title="Prob. Loss" 
                    value={`${(results.risk_stats.prob_loss * 100).toFixed(1)}%`}
                    color="yellow"
                  />
                </div>

                {/* Charts */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  
                  {/* --- FIXED SIMULATED PATHS CHART --- */}
                  <div className="bg-slate-800 rounded-lg p-6 shadow-xl">
                    <h3 className="text-lg font-semibold mb-4">Simulated Price Paths</h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                        <XAxis 
                          dataKey="day" 
                          stroke="#94a3b8" 
                          type="number" 
                          domain={[0, horizon]}
                          tickCount={10} 
                        />
                        <YAxis 
                          stroke="#94a3b8" 
                          domain={['auto', 'auto']}
                        />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
                          labelStyle={{ color: '#e2e8f0' }}
                          labelFormatter={(label) => `Day ${label}`}
                          formatter={(value) => [`$${value.toFixed(2)}`, 'Price']}
                        />
                        {/* Dynamically render a line for each of the 50 paths */}
                        {results.paths_sample.map((_, idx) => (
                          <Line 
                            key={idx} 
                            type="monotone" 
                            dataKey={`path_${idx}`} 
                            stroke="#60a5fa" 
                            strokeWidth={1} 
                            dot={false} 
                            strokeOpacity={0.3} // Transparency makes overlapping lines look cool
                            isAnimationActive={false} // Performance boost
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                    <p className="text-sm text-slate-400 mt-2">
                      Showing 50 of {numPaths} paths | Start: ${results.start_price.toFixed(2)}
                    </p>
                  </div>

                  {/* Return Distribution */}
                  <div className="bg-slate-800 rounded-lg p-6 shadow-xl">
                    <h3 className="text-lg font-semibold mb-4">Final Return Distribution</h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={histogramData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                        <XAxis 
                          dataKey="return" 
                          stroke="#94a3b8"
                          tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                        />
                        <YAxis stroke="#94a3b8" />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
                          labelFormatter={(val) => `Return: ${(val * 100).toFixed(1)}%`}
                        />
                        <Bar dataKey="count" fill="#60a5fa" />
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="text-sm text-slate-400 mt-2">
                      Model: {results.model.toUpperCase()} | Paths: {numPaths}
                    </p>
                  </div>
                </div>
              </>
            )}
          </>
        )}

        {activeTab === 'compare' && (
          <div className="bg-slate-800 rounded-lg p-6 text-center">
            <BarChart3 className="w-16 h-16 mx-auto text-slate-600 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Model Comparison</h3>
            <p className="text-slate-400 mb-4">
              Compare Gaussian, GMM, and EWMA models side-by-side
            </p>
            <p className="text-sm text-slate-500">Coming soon in next update...</p>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ title, value, color }) {
  const colors = {
    blue: 'from-blue-600 to-blue-700',
    purple: 'from-purple-600 to-purple-700',
    red: 'from-red-600 to-red-700',
    orange: 'from-orange-600 to-orange-700',
    yellow: 'from-yellow-600 to-yellow-700',
  };

  return (
    <div className={`bg-gradient-to-br ${colors[color]} rounded-lg p-4 shadow-lg`}>
      <p className="text-sm opacity-90 mb-1">{title}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}