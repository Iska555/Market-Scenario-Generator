import React, { useState, useMemo } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, BarChart, Bar
} from 'recharts';
import { 
  TrendingUp, Activity, AlertTriangle, BarChart3, 
  Zap, Target, PieChart, RefreshCw,
  ChevronRight, Sparkles, Shield, TrendingDown, Database,
  Sun, Moon
} from 'lucide-react';

const API_URL = 'https://market-scenario-generator.onrender.com';

// --- Theme Aware Tooltip ---
const CustomTooltip = ({ active, payload, label, isDark }) => {
  if (active && payload && payload.length) {
    const prices = payload.map(p => p.value);
    const max = Math.max(...prices);
    const min = Math.min(...prices);
    const avg = prices.reduce((a, b) => a + b, 0) / prices.length;

    // Dark Mode Tooltip Styles vs Light Mode Tooltip Styles
    const containerClass = isDark 
      ? "bg-slate-900 border border-slate-700" 
      : "bg-white border border-slate-200";
    
    const textLabel = isDark ? "text-slate-400" : "text-slate-600";
    const textValue = isDark ? "text-white" : "text-slate-900";

    return (
      <div className={`${containerClass} p-4 rounded-xl shadow-2xl backdrop-blur-md`}>
        <p className={`${textLabel} font-bold mb-2 text-xs uppercase tracking-wider`}>Day {label}</p>
        <div className="space-y-1 text-sm font-mono">
          <div className="flex justify-between gap-6">
            <span className={isDark ? "text-emerald-400" : "text-emerald-600"}>High:</span>
            <span className={`${textValue} font-semibold`}>${max.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
          </div>
          <div className="flex justify-between gap-6">
            <span className={isDark ? "text-blue-400" : "text-slate-600"}>Avg:</span>
            <span className={`${textValue} font-semibold`}>${avg.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
          </div>
          <div className="flex justify-between gap-6">
            <span className={isDark ? "text-rose-400" : "text-rose-600"}>Low:</span>
            <span className={`${textValue} font-semibold`}>${min.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export default function MarketScenarioGenerator() {
  const [theme, setTheme] = useState('dark'); // Default to Dark Mode
  const isDark = theme === 'dark';

  const [ticker, setTicker] = useState('BTC-USD');
  const [years, setYears] = useState(3);
  const [horizon, setHorizon] = useState(252);
  const [numPaths, setNumPaths] = useState(1000);
  const [model, setModel] = useState('gmm');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('simulate');

  const toggleTheme = () => setTheme(prev => prev === 'dark' ? 'light' : 'dark');

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    setResults(null); // Clear previous results to show loading state clearly
    
    try {
      // FIX: Added timestamp query param to force fresh request (bypasses browser cache)
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

  // --- Style Logic ---
  const styles = {
    mainBg: isDark 
      ? "bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950" 
      : "bg-gradient-to-br from-slate-50 via-slate-100 to-slate-50",
    header: isDark 
      ? "border-white/10 bg-slate-900/50 backdrop-blur-xl" 
      : "border-slate-200 bg-white/80 backdrop-blur-xl",
    headerIconBox: isDark 
      ? "bg-slate-200 shadow-slate-200/20 text-slate-900" 
      : "bg-slate-900 shadow-lg text-white",
    headerText: isDark ? "text-white" : "text-slate-900",
    headerSubText: isDark ? "text-slate-400" : "text-slate-600",
    
    // Tabs
    tabActive: isDark 
      ? "bg-slate-200 text-slate-900 shadow-lg shadow-slate-200/20" 
      : "bg-slate-900 text-white shadow-lg shadow-slate-900/20",
    tabInactive: isDark 
      ? "bg-slate-800/50 text-slate-400 hover:bg-slate-800 hover:text-white border border-slate-700/50" 
      : "bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900 border border-slate-200 shadow-sm",
    
    // Config Card
    configCard: isDark 
      ? "bg-gradient-to-br from-slate-900/90 to-slate-800/90 border-white/10 shadow-2xl" 
      : "bg-white border-slate-200 shadow-xl shadow-slate-200/50",
    configIconBox: isDark ? "bg-blue-500/20 text-blue-400" : "bg-slate-900 text-white",
    configTitle: isDark ? "text-white" : "text-slate-900",
    
    // Inputs
    inputLabel: isDark ? "text-slate-300" : "text-slate-700",
    inputField: isDark 
      ? "bg-slate-800/50 border-slate-700/50 text-white focus:ring-slate-200 group-hover:border-slate-600" 
      : "bg-slate-50 border-slate-200 text-slate-900 focus:ring-slate-900 group-hover:border-slate-300",
    
    // Model Buttons
    modelBtnActive: isDark 
      ? "bg-slate-200 border-transparent shadow-lg shadow-slate-200/20 text-slate-900" 
      : "bg-slate-900 border-slate-900 shadow-lg shadow-slate-900/20 text-white",
    modelBtnInactive: isDark 
      ? "bg-slate-800/50 border-slate-700/50 hover:border-slate-600 text-white" 
      : "bg-white border-slate-200 hover:border-slate-300 shadow-sm text-slate-900",
    modelDescActive: isDark ? "text-slate-600" : "text-slate-300",
    modelDescInactive: isDark ? "text-slate-400" : "text-slate-600",

    // Run Button
    runBtn: isDark 
      ? "bg-slate-200 hover:bg-white text-slate-900 shadow-slate-200/20 hover:shadow-slate-200/30 disabled:bg-slate-700" 
      : "bg-slate-900 hover:bg-slate-800 text-white shadow-slate-900/20 hover:shadow-slate-900/30 disabled:bg-slate-300",

    // Chart Lines
    gridStroke: isDark ? "#334155" : "#e2e8f0",
    axisStroke: isDark ? "#94a3b8" : "#64748b",
    lineOpacity: isDark ? 0.4 : 0.15,
    barFill: isDark ? "url(#barGradient)" : "#0f172a"
  };
  
  return (
    <div className={`min-h-screen transition-colors duration-500 ${styles.mainBg}`}>
      {/* Animated Background (Dark Mode Only) */}
      {isDark && (
        <div className="fixed inset-0 opacity-20 pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 animate-pulse"></div>
        </div>
      )}

      <div className="relative z-10">
        {/* Header */}
        <div className={`border-b ${styles.header}`}>
          <div className="max-w-7xl mx-auto px-8 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-2xl shadow-lg ${styles.headerIconBox}`}>
                  <TrendingUp className="w-8 h-8" />
                </div>
                <div>
                  <h1 className={`text-3xl font-bold ${styles.headerText}`}>
                    Market Scenario Generator
                  </h1>
                  <p className={`${styles.headerSubText} text-sm mt-1`}>
                    Advanced Monte Carlo Risk Simulation Platform
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-4">
                {/* Theme Toggle Button */}
                <button 
                  onClick={toggleTheme}
                  className={`p-2 rounded-full transition-all border ${
                    isDark 
                      ? 'bg-slate-800 border-slate-700 text-yellow-400 hover:bg-slate-700' 
                      : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {isDark ? <Sun className="w-6 h-6" /> : <Moon className="w-6 h-6" />}
                </button>

                <div className="px-4 py-2 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-sm font-semibold">
                  <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 dark:bg-emerald-400 animate-pulse mr-2"></span>
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
                    activeTab === tab.id ? styles.tabActive : styles.tabInactive
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
              <div className={`${styles.configCard} backdrop-blur-xl rounded-3xl p-8 mb-8 border`}>
                <div className="flex items-center gap-3 mb-6">
                  <div className={`p-2 rounded-xl ${styles.configIconBox}`}>
                    <Activity className="w-5 h-5" />
                  </div>
                  <h2 className={`text-2xl font-bold ${styles.configTitle}`}>Configuration</h2>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                  <div className="group">
                    <label className={`block text-sm font-semibold mb-3 ${styles.inputLabel}`}>Ticker Symbol</label>
                    <input
                      type="text"
                      value={ticker}
                      onChange={(e) => setTicker(e.target.value.toUpperCase())}
                      className={`w-full border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 transition-all ${styles.inputField}`}
                      placeholder="SPY"
                    />
                  </div>

                  <div>
                    <label className={`block text-sm font-semibold mb-3 ${styles.inputLabel}`}>Historical Years</label>
                    <input
                      type="number"
                      value={years}
                      onChange={(e) => setYears(parseInt(e.target.value))}
                      min="1"
                      max="10"
                      className={`w-full border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 transition-all ${styles.inputField}`}
                    />
                  </div>

                  <div>
                    <label className={`block text-sm font-semibold mb-3 ${styles.inputLabel}`}>Simulation Horizon (days)</label>
                    <input
                      type="number"
                      value={horizon}
                      onChange={(e) => setHorizon(parseInt(e.target.value))}
                      min="1"
                      max="1000"
                      className={`w-full border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 transition-all ${styles.inputField}`}
                    />
                  </div>

                  <div>
                    <label className={`block text-sm font-semibold mb-3 ${styles.inputLabel}`}>Number of Paths</label>
                    <input
                      type="number"
                      value={numPaths}
                      onChange={(e) => setNumPaths(parseInt(e.target.value))}
                      min="100"
                      max="10000"
                      step="100"
                      className={`w-full border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 transition-all ${styles.inputField}`}
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className={`block text-sm font-semibold mb-3 ${styles.inputLabel}`}>Model Type</label>
                    <div className="grid grid-cols-3 gap-3">
                      {models.map(m => {
                        const Icon = m.icon;
                        const isActive = model === m.value;
                        return (
                          <button
                            key={m.value}
                            onClick={() => setModel(m.value)}
                            className={`p-4 rounded-xl transition-all border-2 ${
                              isActive ? styles.modelBtnActive : styles.modelBtnInactive
                            }`}
                          >
                            <Icon className="w-5 h-5 mb-2 mx-auto" />
                            <div className="text-sm font-bold">{m.label}</div>
                            <div className={`text-xs mt-1 ${isActive ? styles.modelDescActive : styles.modelDescInactive}`}>{m.desc}</div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <button
                  onClick={runSimulation}
                  disabled={loading}
                  className={`w-full font-bold py-4 px-8 rounded-xl transition-all shadow-lg flex items-center justify-center gap-3 group ${styles.runBtn}`}
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
                      <p className="text-red-800 dark:text-red-200 font-semibold">Simulation Error</p>
                      <p className="text-red-600 dark:text-red-300/80 text-sm mt-1">{error}</p>
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
                      isDark={isDark}
                    />
                    <StatCard
                      title="Volatility"
                      value={`${(results.risk_stats.vol * 100).toFixed(2)}%`}
                      icon={Activity}
                      color="violet"
                      isDark={isDark}
                    />
                    <StatCard
                      title="VaR (95%)"
                      value={`${(results.risk_stats.VaR_95 * 100).toFixed(2)}%`}
                      icon={Shield}
                      color="rose"
                      trend="negative"
                      isDark={isDark}
                    />
                    <StatCard
                      title="CVaR (95%)"
                      value={`${(results.risk_stats.CVaR_95 * 100).toFixed(2)}%`}
                      icon={TrendingDown}
                      color="orange"
                      trend="negative"
                      isDark={isDark}
                    />
                    <StatCard
                      title="Prob. Loss"
                      value={`${(results.risk_stats.prob_loss * 100).toFixed(1)}%`}
                      icon={AlertTriangle}
                      color="amber"
                      isDark={isDark}
                    />
                  </div>

                  {/* Charts Grid */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Paths Chart */}
                    <ChartCard title="Simulated Price Paths" icon={TrendingUp} isDark={isDark}>
                      <ResponsiveContainer width="100%" height={320}>
                        <LineChart data={chartData}>
                          <defs>
                            <linearGradient id="pathGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke={styles.gridStroke} opacity={0.3} />
                          <XAxis dataKey="day" stroke={styles.axisStroke} type="number" domain={[0, horizon]} />
                          <YAxis stroke={styles.axisStroke} />
                          <Tooltip content={<CustomTooltip isDark={isDark} />} />
                          {results.paths_sample.map((_, idx) => (
                            <Line
                              key={idx}
                              type="monotone"
                              dataKey={`path_${idx}`}
                              stroke={isDark ? "#3b82f6" : "#0f172a"}
                              strokeWidth={1.5}
                              dot={false}
                              strokeOpacity={styles.lineOpacity}
                              isAnimationActive={false}
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                      <p className={`text-sm mt-4 flex items-center gap-2 ${isDark ? "text-slate-400" : "text-slate-600"}`}>
                        <Database className="w-4 h-4" />
                        Showing 50 of {numPaths} paths | Start: ${results.start_price.toFixed(2)}
                      </p>
                    </ChartCard>

                    {/* Distribution Chart */}
                    <ChartCard title="Return Distribution" icon={BarChart3} isDark={isDark}>
                      <ResponsiveContainer width="100%" height={320}>
                        <BarChart data={histogramData}>
                          <defs>
                            <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.9}/>
                              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.9}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke={styles.gridStroke} opacity={0.3} />
                          <XAxis
                            dataKey="return"
                            stroke={styles.axisStroke}
                            tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                          />
                          <YAxis stroke={styles.axisStroke} />
                          <Tooltip
                            contentStyle={{ 
                              backgroundColor: isDark ? '#1e293b' : '#ffffff', 
                              border: isDark ? '1px solid #475569' : '1px solid #e2e8f0',
                              borderRadius: '12px',
                              boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
                              color: isDark ? '#fff' : '#000'
                            }}
                            labelFormatter={(val) => `Return: ${(val * 100).toFixed(1)}%`}
                          />
                          <Bar dataKey="count" fill={styles.barFill} radius={[8, 8, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                      <p className={`text-sm mt-4 flex items-center gap-2 ${isDark ? "text-slate-400" : "text-slate-600"}`}>
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
            <div className={`${styles.configCard} backdrop-blur-xl rounded-3xl p-12 text-center border`}>
              <div className={`inline-flex p-6 rounded-full mb-6 ${isDark ? 'bg-gradient-to-br from-blue-500/20 to-purple-500/20' : 'bg-slate-50'}`}>
                <BarChart3 className={`w-16 h-16 ${isDark ? 'text-blue-400' : 'text-slate-900'}`} />
              </div>
              <h3 className={`text-3xl font-bold mb-3 ${styles.configTitle}`}>Model Comparison</h3>
              <p className={`mb-6 max-w-md mx-auto ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                Compare Gaussian, GMM, and EWMA models side-by-side with advanced analytics
              </p>
              <div className={`inline-flex items-center gap-2 px-6 py-3 rounded-full ${isDark ? 'bg-blue-500/10 border border-blue-500/30 text-blue-400' : 'bg-slate-900 text-white'}`}>
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

function StatCard({ title, value, icon: Icon, color, trend, isDark }) {
  const darkColors = {
    emerald: 'from-emerald-500 to-teal-600',
    violet: 'from-violet-500 to-purple-600',
    rose: 'from-rose-500 to-red-600',
    orange: 'from-orange-500 to-amber-600',
    amber: 'from-amber-500 to-yellow-600'
  };

  const lightColors = {
    emerald: 'from-emerald-500 to-teal-600',
    violet: 'from-violet-500 to-purple-600',
    rose: 'from-rose-500 to-red-600',
    orange: 'from-orange-500 to-amber-600',
    amber: 'from-amber-500 to-yellow-600'
  };

  if (isDark) {
    return (
      <div className="group relative">
        <div className={`absolute inset-0 bg-gradient-to-br ${darkColors[color]} opacity-10 rounded-2xl blur-xl transition-opacity group-hover:opacity-20`}></div>
        <div className="relative bg-gradient-to-br from-slate-900/90 to-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-white/10 hover:border-white/20 transition-all">
          <div className="flex items-start justify-between mb-3">
            <div className={`p-2 rounded-xl bg-gradient-to-br ${darkColors[color]} bg-opacity-20`}>
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
  } else {
    // Light Mode Card
    return (
      <div className="group relative">
        <div className="bg-white rounded-2xl p-6 border border-slate-200 hover:border-slate-300 transition-all shadow-lg shadow-slate-200/50 hover:shadow-xl hover:shadow-slate-200/60">
          <div className="flex items-start justify-between mb-3">
            <div className={`p-2 rounded-xl bg-gradient-to-br ${lightColors[color]} shadow-lg`}>
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
}

function ChartCard({ title, icon: Icon, children, isDark }) {
  const containerClass = isDark
    ? "bg-gradient-to-br from-slate-900/90 to-slate-800/90 backdrop-blur-xl border-white/10 shadow-2xl"
    : "bg-white border-slate-200 shadow-xl shadow-slate-200/50";
  
  const iconBox = isDark
    ? "bg-blue-500/20 text-blue-400"
    : "bg-slate-900 text-white";

  const titleText = isDark ? "text-white" : "text-slate-900";

  return (
    <div className={`${containerClass} rounded-3xl p-6 border`}>
      <div className="flex items-center gap-3 mb-6">
        <div className={`p-2 rounded-xl ${iconBox}`}>
          <Icon className="w-5 h-5" />
        </div>
        <h3 className={`text-xl font-bold ${titleText}`}>{title}</h3>
      </div>
      {children}
    </div>
  );
}