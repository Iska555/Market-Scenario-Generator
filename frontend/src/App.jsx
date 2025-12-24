import React, { useState, useEffect } from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import { 
  Settings, 
  Play, 
  TrendingUp, 
  Activity, 
  Moon, 
  Sun, 
  BarChart3,
  AlertTriangle,
  ArrowRight,
  Download,
  Share2,
  Info,
  ChevronRight,
  Maximize2
} from 'lucide-react';

const App = () => {
  const [darkMode, setDarkMode] = useState(true);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  
  // Configuration State
  const [ticker, setTicker] = useState('BTC-USD');
  const [histYears, setHistYears] = useState(3);
  const [simHorizon, setSimHorizon] = useState(252);
  const [paths, setPaths] = useState(1000);
  const [selectedModel, setSelectedModel] = useState('GMM');

  // Simulation Runner (Mock Data Logic)
  const runSimulation = () => {
    setLoading(true);
    
    // Simulate API delay for realism
    setTimeout(() => {
      // Generate realistic-looking random walk data
      const newChartData = [];
      let currentPrice = 68000;
      
      for (let i = 0; i <= 30; i++) {
        const date = new Date();
        date.setDate(date.getDate() + i);
        
        // Random drift and volatility
        const drift = 1 + (Math.random() * 0.002);
        const shock = (Math.random() - 0.5) * 1000;
        
        // Diverging paths logic
        const p95 = currentPrice * (1 + (i * 0.015));
        const mean = currentPrice * (1 + (i * 0.005) + (Math.random() * 0.005));
        const p5 = currentPrice * (1 - (i * 0.012));

        newChartData.push({
          day: i,
          date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          p5: p5,
          mean: mean,
          p95: p95,
        });
        
        currentPrice = mean;
      }

      setResults({
        chartData: newChartData,
        metrics: {
          var: "-12.54%",
          cvar: "-18.21%",
          sharpe: "1.85",
          volatility: "45.2%"
        },
        extremes: [
          { name: "Best Case (99%)", return: "+145.2%", price: "$124,500", prob: "1%" },
          { name: "Bullish (75%)", return: "+45.8%", price: "$98,200", prob: "25%" },
          { name: "Base Case (Mean)", return: "+12.4%", price: "$68,400", prob: "50%" },
          { name: "Bearish (25%)", return: "-15.2%", price: "$42,100", prob: "25%" },
          { name: "Worst Case (1%)", return: "-65.4%", price: "$21,300", prob: "1%" },
        ]
      });
      setLoading(false);
    }, 2000);
  };

  return (
    <div className={`min-h-screen transition-colors duration-300 font-sans ${
      darkMode ? 'bg-[#0B1120] text-slate-100' : 'bg-slate-100 text-slate-900'
    }`}>
      
      {/* ---------------------------------------------------------------------------
          TOP NAVIGATION BAR
          Professional simplified header with status indicators
      --------------------------------------------------------------------------- */}
      <nav className={`border-b backdrop-blur-md sticky top-0 z-50 transition-colors duration-300 ${
        darkMode ? 'border-slate-800 bg-[#0B1120]/90' : 'border-slate-200 bg-white/90'
      }`}>
        <div className="max-w-[1600px] mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-lg ${
              darkMode ? 'bg-blue-600 text-white shadow-blue-900/20' : 'bg-blue-600 text-white shadow-blue-200'
            }`}>
              <TrendingUp size={22} strokeWidth={2.5} />
            </div>
            <div>
              <h1 className="font-bold text-xl tracking-tight leading-none">Market Scenario Generator</h1>
              <p className={`text-xs mt-1 font-medium ${darkMode ? 'text-slate-500' : 'text-slate-500'}`}>
                Advanced Monte Carlo Risk Simulation Platform
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-6">
            {/* Status Indicator */}
            <div className={`hidden md:flex px-4 py-1.5 rounded-full text-xs font-semibold items-center gap-2 border ${
              darkMode 
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                : 'bg-emerald-50 text-emerald-700 border-emerald-200'
            }`}>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              System Operational
            </div>

            <div className="h-8 w-[1px] bg-slate-700/50 hidden md:block"></div>

            <button 
              onClick={() => setDarkMode(!darkMode)}
              className={`p-2.5 rounded-lg transition-all duration-200 ${
                darkMode 
                  ? 'hover:bg-slate-800 text-slate-400 hover:text-white' 
                  : 'hover:bg-slate-200 text-slate-600 hover:text-slate-900'
              }`}
            >
              {darkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-[1600px] mx-auto px-6 py-10 space-y-10">
        
        {/* ---------------------------------------------------------------------------
            HEADER & ACTIONS
            Title and top-level action buttons
        --------------------------------------------------------------------------- */}
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
          <div>
            <h2 className={`text-4xl font-bold tracking-tight ${darkMode ? 'text-white' : 'text-slate-900'}`}>
              Risk Simulation
            </h2>
            <p className={`mt-2 text-lg ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              Configure parameters to run high-fidelity market simulations.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button className={`px-5 py-2.5 rounded-lg font-medium text-sm border transition-all duration-200 ${
              darkMode 
                ? 'border-slate-700 hover:bg-slate-800 text-slate-300' 
                : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-700 shadow-sm'
            }`}>
              Load Preset
            </button>
            <button className={`px-5 py-2.5 rounded-lg font-medium text-sm border transition-all duration-200 ${
               darkMode 
                ? 'border-slate-700 hover:bg-slate-800 text-slate-300' 
                : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-700 shadow-sm'
            }`}>
              Compare Models
            </button>
          </div>
        </div>

        {/* ---------------------------------------------------------------------------
            CONFIGURATION PANEL
            The "Original" heavy styling with specific spacing and card layout
        --------------------------------------------------------------------------- */}
        <div className={`p-1 rounded-2xl ${
          darkMode 
            ? 'bg-gradient-to-b from-slate-800 to-slate-900 border border-slate-800' 
            : 'bg-white border border-slate-200 shadow-xl shadow-slate-200/50'
        }`}>
          <div className={`rounded-xl p-8 ${
            darkMode ? 'bg-[#0f172a]' : 'bg-slate-50'
          }`}>
            <div className="flex items-center gap-3 mb-8">
              <div className={`p-2 rounded-lg ${darkMode ? 'bg-blue-500/10 text-blue-400' : 'bg-blue-100 text-blue-700'}`}>
                <Settings size={24} />
              </div>
              <h3 className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-slate-900'}`}>
                Configuration
              </h3>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              
              {/* Left Column: Text Inputs */}
              <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-8">
                <div className="space-y-3">
                  <label className={`text-sm font-semibold uppercase tracking-wider ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                    Ticker Symbol
                  </label>
                  <input
                    type="text"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value)}
                    className={`w-full px-5 py-4 rounded-xl text-lg outline-none transition-all duration-200 border-2 ${
                      darkMode 
                        ? 'bg-[#1e293b] border-slate-700 text-white focus:border-blue-500 focus:bg-slate-800' 
                        : 'bg-white border-slate-200 text-slate-900 focus:border-blue-500 shadow-sm'
                    }`}
                  />
                </div>

                <div className="space-y-3">
                  <label className={`text-sm font-semibold uppercase tracking-wider ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                    Historical Years
                  </label>
                  <input
                    type="number"
                    value={histYears}
                    onChange={(e) => setHistYears(e.target.value)}
                    className={`w-full px-5 py-4 rounded-xl text-lg outline-none transition-all duration-200 border-2 ${
                      darkMode 
                        ? 'bg-[#1e293b] border-slate-700 text-white focus:border-blue-500 focus:bg-slate-800' 
                        : 'bg-white border-slate-200 text-slate-900 focus:border-blue-500 shadow-sm'
                    }`}
                  />
                </div>

                <div className="space-y-3">
                  <label className={`text-sm font-semibold uppercase tracking-wider ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                    Simulation Horizon (Days)
                  </label>
                  <input
                    type="number"
                    value={simHorizon}
                    onChange={(e) => setSimHorizon(e.target.value)}
                    className={`w-full px-5 py-4 rounded-xl text-lg outline-none transition-all duration-200 border-2 ${
                      darkMode 
                        ? 'bg-[#1e293b] border-slate-700 text-white focus:border-blue-500 focus:bg-slate-800' 
                        : 'bg-white border-slate-200 text-slate-900 focus:border-blue-500 shadow-sm'
                    }`}
                  />
                </div>

                <div className="space-y-3">
                  <label className={`text-sm font-semibold uppercase tracking-wider ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                    Number of Paths
                  </label>
                  <input
                    type="number"
                    value={paths}
                    onChange={(e) => setPaths(e.target.value)}
                    className={`w-full px-5 py-4 rounded-xl text-lg outline-none transition-all duration-200 border-2 ${
                      darkMode 
                        ? 'bg-[#1e293b] border-slate-700 text-white focus:border-blue-500 focus:bg-slate-800' 
                        : 'bg-white border-slate-200 text-slate-900 focus:border-blue-500 shadow-sm'
                    }`}
                  />
                </div>
              </div>

              {/* Right Column: Model Selection Cards */}
              <div className="lg:col-span-12 mt-4">
                <label className={`block mb-4 text-sm font-semibold uppercase tracking-wider ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  Statistical Model
                </label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Gaussian Model Card */}
                  <button
                    onClick={() => setSelectedModel('Gaussian')}
                    className={`group relative flex flex-col items-center justify-center p-8 rounded-2xl border-2 transition-all duration-300 ${
                      selectedModel === 'Gaussian'
                        ? darkMode 
                          ? 'bg-blue-900/20 border-blue-500 shadow-[0_0_30px_rgba(59,130,246,0.15)]' 
                          : 'bg-blue-50 border-blue-600 shadow-md'
                        : darkMode
                          ? 'bg-[#1e293b] border-slate-800 hover:border-slate-600'
                          : 'bg-white border-slate-200 hover:border-slate-300 shadow-sm'
                    }`}
                  >
                    <Activity size={32} className={`mb-4 transition-colors duration-300 ${
                      selectedModel === 'Gaussian' ? 'text-blue-500' : darkMode ? 'text-slate-500' : 'text-slate-400'
                    }`} />
                    <span className={`text-lg font-bold mb-2 ${
                      selectedModel === 'Gaussian' ? (darkMode ? 'text-white' : 'text-blue-900') : (darkMode ? 'text-slate-300' : 'text-slate-600')
                    }`}>Gaussian</span>
                    <span className={`text-sm ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>Normal distribution baseline</span>
                  </button>

                  {/* GMM Model Card */}
                  <button
                    onClick={() => setSelectedModel('GMM')}
                    className={`group relative flex flex-col items-center justify-center p-8 rounded-2xl border-2 transition-all duration-300 ${
                      selectedModel === 'GMM'
                        ? darkMode 
                          ? 'bg-blue-900/20 border-blue-500 shadow-[0_0_30px_rgba(59,130,246,0.15)]' 
                          : 'bg-blue-50 border-blue-600 shadow-md'
                        : darkMode
                          ? 'bg-[#1e293b] border-slate-800 hover:border-slate-600'
                          : 'bg-white border-slate-200 hover:border-slate-300 shadow-sm'
                    }`}
                  >
                    <BarChart3 size={32} className={`mb-4 transition-colors duration-300 ${
                      selectedModel === 'GMM' ? 'text-blue-500' : darkMode ? 'text-slate-500' : 'text-slate-400'
                    }`} />
                    <span className={`text-lg font-bold mb-2 ${
                      selectedModel === 'GMM' ? (darkMode ? 'text-white' : 'text-blue-900') : (darkMode ? 'text-slate-300' : 'text-slate-600')
                    }`}>GMM</span>
                    <span className={`text-sm ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>Fat-tailed multi-regime</span>
                  </button>

                  {/* EWMA Model Card */}
                  <button
                    onClick={() => setSelectedModel('EWMA')}
                    className={`group relative flex flex-col items-center justify-center p-8 rounded-2xl border-2 transition-all duration-300 ${
                      selectedModel === 'EWMA'
                        ? darkMode 
                          ? 'bg-blue-900/20 border-blue-500 shadow-[0_0_30px_rgba(59,130,246,0.15)]' 
                          : 'bg-blue-50 border-blue-600 shadow-md'
                        : darkMode
                          ? 'bg-[#1e293b] border-slate-800 hover:border-slate-600'
                          : 'bg-white border-slate-200 hover:border-slate-300 shadow-sm'
                    }`}
                  >
                    <TrendingUp size={32} className={`mb-4 transition-colors duration-300 ${
                      selectedModel === 'EWMA' ? 'text-blue-500' : darkMode ? 'text-slate-500' : 'text-slate-400'
                    }`} />
                    <span className={`text-lg font-bold mb-2 ${
                      selectedModel === 'EWMA' ? (darkMode ? 'text-white' : 'text-blue-900') : (darkMode ? 'text-slate-300' : 'text-slate-600')
                    }`}>EWMA</span>
                    <span className={`text-sm ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>Time-varying volatility</span>
                  </button>
                </div>
              </div>

              {/* Action Button */}
              <div className="lg:col-span-12 pt-4">
                <button 
                  onClick={runSimulation}
                  disabled={loading}
                  className={`w-full py-5 rounded-xl font-bold text-xl tracking-wide flex items-center justify-center gap-3 transition-all duration-300 transform active:scale-[0.99] ${
                    loading 
                      ? 'opacity-70 cursor-not-allowed grayscale'
                      : 'hover:shadow-xl hover:-translate-y-0.5'
                  } ${
                    darkMode 
                      ? 'bg-gradient-to-r from-slate-200 to-white text-slate-900 hover:shadow-white/10' 
                      : 'bg-slate-900 text-white hover:bg-slate-800 hover:shadow-slate-500/30'
                  }`}
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-current"></div>
                      Running Simulation...
                    </>
                  ) : (
                    <>
                      <Play size={24} fill="currentColor" /> Run Simulation
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ---------------------------------------------------------------------------
            RESULTS SECTION
            Only shown after simulation runs. Contains detailed charts and tables.
        --------------------------------------------------------------------------- */}
        {results && (
          <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 space-y-8">
            
            {/* KPI CARDS */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Card 1 */}
              <div className={`p-6 rounded-xl border transition-all hover:border-blue-500/50 ${
                darkMode ? 'bg-[#1e293b] border-slate-700' : 'bg-white border-slate-200 shadow-sm'
              }`}>
                <div className="flex justify-between items-start mb-4">
                  <span className={`text-sm font-medium ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Value at Risk (95%)</span>
                  <div className="p-1.5 rounded bg-rose-500/10 text-rose-500">
                    <TrendingUp size={16} className="rotate-180" />
                  </div>
                </div>
                <div className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-slate-900'}`}>{results.metrics.var}</div>
                <div className="mt-2 text-xs text-rose-500 font-medium">Potential downside risk</div>
              </div>

              {/* Card 2 */}
              <div className={`p-6 rounded-xl border transition-all hover:border-blue-500/50 ${
                darkMode ? 'bg-[#1e293b] border-slate-700' : 'bg-white border-slate-200 shadow-sm'
              }`}>
                <div className="flex justify-between items-start mb-4">
                  <span className={`text-sm font-medium ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Conditional VaR</span>
                  <div className="p-1.5 rounded bg-rose-500/10 text-rose-500">
                    <Activity size={16} />
                  </div>
                </div>
                <div className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-slate-900'}`}>{results.metrics.cvar}</div>
                <div className="mt-2 text-xs text-rose-500 font-medium">Extreme tail loss avg</div>
              </div>

              {/* Card 3 */}
              <div className={`p-6 rounded-xl border transition-all hover:border-blue-500/50 ${
                darkMode ? 'bg-[#1e293b] border-slate-700' : 'bg-white border-slate-200 shadow-sm'
              }`}>
                <div className="flex justify-between items-start mb-4">
                  <span className={`text-sm font-medium ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Sharpe Ratio</span>
                  <div className="p-1.5 rounded bg-emerald-500/10 text-emerald-500">
                    <TrendingUp size={16} />
                  </div>
                </div>
                <div className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-slate-900'}`}>{results.metrics.sharpe}</div>
                <div className="mt-2 text-xs text-emerald-500 font-medium">Risk-adjusted return</div>
              </div>

              {/* Card 4 */}
              <div className={`p-6 rounded-xl border transition-all hover:border-blue-500/50 ${
                darkMode ? 'bg-[#1e293b] border-slate-700' : 'bg-white border-slate-200 shadow-sm'
              }`}>
                <div className="flex justify-between items-start mb-4">
                  <span className={`text-sm font-medium ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Annualized Volatility</span>
                  <div className="p-1.5 rounded bg-blue-500/10 text-blue-500">
                    <Activity size={16} />
                  </div>
                </div>
                <div className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-slate-900'}`}>{results.metrics.volatility}</div>
                <div className="mt-2 text-xs text-blue-500 font-medium">Standard deviation</div>
              </div>
            </div>

            {/* MAIN CONTENT SPLIT */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              
              {/* CHART SECTION (2/3 Width) */}
              <div className={`lg:col-span-2 p-6 rounded-xl border ${
                darkMode 
                  ? 'bg-[#1e293b] border-slate-700 shadow-lg' 
                  : 'bg-white border-slate-200 shadow-sm'
              }`}>
                <div className="flex justify-between items-center mb-6">
                  <div>
                    <h3 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-slate-900'}`}>Simulation Paths</h3>
                    <p className={`text-sm ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Projected performance range over {simHorizon} days</p>
                  </div>
                  <div className="flex gap-2">
                    <button className={`p-2 rounded hover:bg-slate-700/50 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                      <Download size={18} />
                    </button>
                    <button className={`p-2 rounded hover:bg-slate-700/50 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                      <Maximize2 size={18} />
                    </button>
                  </div>
                </div>
                
                <div className="h-[400px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={results.chartData}>
                      <defs>
                        <linearGradient id="colorMean" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke={darkMode ? "#334155" : "#e2e8f0"} vertical={false} />
                      <XAxis 
                        dataKey="date" 
                        stroke={darkMode ? "#94a3b8" : "#64748b"} 
                        tick={{fontSize: 12}}
                        tickLine={false}
                        axisLine={false}
                        dy={10}
                      />
                      <YAxis 
                        stroke={darkMode ? "#94a3b8" : "#64748b"} 
                        tick={{fontSize: 12}}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(value) => `$${value/1000}k`}
                      />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: darkMode ? '#0f172a' : '#fff',
                          borderColor: darkMode ? '#334155' : '#e2e8f0',
                          borderRadius: '8px',
                          color: darkMode ? '#fff' : '#000',
                          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                        }}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="p95" 
                        stroke="transparent" 
                        fill={darkMode ? "#334155" : "#cbd5e1"} 
                        fillOpacity={0.3} 
                      />
                      <Area 
                        type="monotone" 
                        dataKey="mean" 
                        stroke="#3b82f6" 
                        strokeWidth={3}
                        fill="url(#colorMean)" 
                      />
                      <Area 
                        type="monotone" 
                        dataKey="p5" 
                        stroke="transparent" 
                        fill={darkMode ? "#334155" : "#cbd5e1"} 
                        fillOpacity={0.3} 
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* EXTREME SCENARIOS TABLE (1/3 Width) */}
              <div className={`lg:col-span-1 flex flex-col p-0 rounded-xl border overflow-hidden ${
                darkMode 
                  ? 'bg-[#1e293b] border-slate-700 shadow-lg' 
                  : 'bg-white border-slate-200 shadow-sm'
              }`}>
                <div className={`p-5 border-b ${darkMode ? 'border-slate-700 bg-slate-800/50' : 'border-slate-100 bg-slate-50'}`}>
                   <div className="flex items-center gap-2">
                      <AlertTriangle size={20} className="text-amber-500" />
                      <h3 className={`font-bold text-lg ${darkMode ? 'text-white' : 'text-slate-900'}`}>Extreme Scenarios</h3>
                   </div>
                   <p className={`text-xs mt-1 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                     Probabilistic tail outcomes
                   </p>
                </div>
                
                <div className="flex-1 overflow-auto">
                  <table className="w-full text-left border-collapse">
                    <thead className={`${darkMode ? 'bg-slate-800/30' : 'bg-slate-50'}`}>
                      <tr>
                        <th className={`px-5 py-3 text-xs font-semibold uppercase tracking-wider ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Scenario</th>
                        <th className={`px-5 py-3 text-xs font-semibold uppercase tracking-wider text-right ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Return</th>
                      </tr>
                    </thead>
                    <tbody className={`divide-y ${darkMode ? 'divide-slate-700' : 'divide-slate-100'}`}>
                      {results.extremes.map((item, idx) => (
                        <tr key={idx} className={`group transition-colors ${darkMode ? 'hover:bg-slate-800/50' : 'hover:bg-slate-50'}`}>
                          <td className="px-5 py-4">
                            <div className={`font-medium ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>{item.name}</div>
                            <div className="flex items-center gap-2 mt-1">
                              <span className={`text-xs px-1.5 py-0.5 rounded ${darkMode ? 'bg-slate-700 text-slate-300' : 'bg-slate-200 text-slate-600'}`}>
                                {item.prob}
                              </span>
                              <span className={`text-xs ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>{item.price}</span>
                            </div>
                          </td>
                          <td className={`px-5 py-4 text-right font-mono font-bold ${
                            item.return.includes('+') ? 'text-emerald-500' : 'text-rose-500'
                          }`}>
                            {item.return}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                
                <div className={`p-4 border-t ${darkMode ? 'border-slate-700 bg-slate-800/30' : 'border-slate-100 bg-slate-50'}`}>
                  <button className={`w-full py-2.5 rounded-lg text-xs font-bold uppercase tracking-wide transition-colors flex items-center justify-center gap-2 ${
                    darkMode 
                      ? 'bg-slate-800 hover:bg-slate-700 text-slate-300' 
                      : 'bg-white border border-slate-200 hover:bg-slate-50 text-slate-600'
                  }`}>
                    View Full Distribution <ArrowRight size={14} />
                  </button>
                </div>
              </div>

            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;