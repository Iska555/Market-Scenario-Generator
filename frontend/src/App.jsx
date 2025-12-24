import React, { useState } from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { 
  Settings, 
  Play, 
  TrendingUp, 
  Activity, 
  Moon, 
  Sun, 
  Layout, 
  BarChart3,
  AlertTriangle,
  ArrowRight
} from 'lucide-react';

// --- Helper Components ---

const Card = ({ children, className = "", darkMode }) => (
  <div className={`p-6 rounded-xl border transition-all duration-300 ${
    darkMode 
      ? 'bg-[#1e293b] border-slate-700/50 shadow-lg shadow-black/20' 
      : 'bg-white border-slate-200 shadow-sm' // Gray-ish white in light mode
  } ${className}`}>
    {children}
  </div>
);

const InputGroup = ({ label, value, onChange, type = "text", darkMode }) => (
  <div className="flex flex-col gap-2">
    <label className={`text-sm font-medium ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
      {label}
    </label>
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`w-full px-4 py-3 rounded-lg outline-none transition-colors border ${
        darkMode 
          ? 'bg-[#0f172a] border-slate-700 text-slate-100 focus:border-blue-500' 
          : 'bg-slate-50 border-slate-200 text-slate-900 focus:border-blue-600'
      }`}
    />
  </div>
);

const ModelCard = ({ title, desc, icon: Icon, selected, onClick, darkMode }) => (
  <button
    onClick={onClick}
    className={`relative flex flex-col items-center justify-center p-6 rounded-xl border-2 transition-all duration-200 w-full text-center group ${
      selected
        ? darkMode 
          ? 'bg-blue-600/10 border-blue-500 text-blue-100' 
          : 'bg-blue-50 border-blue-600 text-blue-900'
        : darkMode
          ? 'bg-[#0f172a] border-slate-800 text-slate-400 hover:border-slate-600'
          : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300'
    }`}
  >
    <Icon className={`w-8 h-8 mb-3 ${
      selected 
        ? darkMode ? 'text-blue-400' : 'text-blue-600'
        : 'text-current'
    }`} />
    <span className="font-semibold text-lg mb-1">{title}</span>
    <span className={`text-xs ${darkMode ? 'text-slate-500' : 'text-slate-500'}`}>{desc}</span>
  </button>
);

const StatCard = ({ label, value, sub, darkMode, trend }) => (
  <Card darkMode={darkMode} className="flex flex-col">
    <span className={`text-sm ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>{label}</span>
    <div className="flex items-end gap-2 mt-2">
      <span className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-slate-900'}`}>{value}</span>
      {sub && (
        <span className={`text-sm mb-1 ${
          trend === 'up' ? 'text-emerald-500' : trend === 'down' ? 'text-rose-500' : 'text-slate-500'
        }`}>
          {sub}
        </span>
      )}
    </div>
  </Card>
);

// --- Main Application ---

const App = () => {
  const [darkMode, setDarkMode] = useState(true);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  
  // Configuration State
  const [config, setConfig] = useState({
    ticker: 'BTC-USD',
    histYears: 3,
    simHorizon: 252,
    paths: 1000,
    model: 'GMM' // Options: Gaussian, GMM, EWMA
  });

  // Mock Data Generator
  const runSimulation = () => {
    setLoading(true);
    setTimeout(() => {
      // Generate dummy chart data
      const newChartData = Array.from({ length: 30 }, (_, i) => {
        const base = 100;
        const random = Math.random() * 20 - 10;
        return {
          day: i,
          p5: base + random - 15,
          mean: base + random,
          p95: base + random + 15,
        };
      });

      // Generate dummy extreme scenarios
      const newExtremes = [
        { name: "Best Case (99%)", return: "+145.2%", price: "$124,500", prob: "1%" },
        { name: "Bullish (75%)", return: "+45.8%", price: "$98,200", prob: "25%" },
        { name: "Base Case (Mean)", return: "+12.4%", price: "$68,400", prob: "50%" },
        { name: "Bearish (25%)", return: "-15.2%", price: "$42,100", prob: "25%" },
        { name: "Worst Case (1%)", return: "-65.4%", price: "$21,300", prob: "1%" },
      ];

      setResults({
        chartData: newChartData,
        extremes: newExtremes,
        metrics: {
          var: "-12.5%",
          cvar: "-18.2%",
          sharpe: "1.85",
          volatility: "45.2%"
        }
      });
      setLoading(false);
    }, 1500);
  };

  return (
    <div className={`min-h-screen transition-colors duration-300 font-sans selection:bg-blue-500/30 ${
      darkMode ? 'bg-[#0B1120] text-slate-100' : 'bg-slate-100 text-slate-900'
    }`}>
      
      {/* Navbar */}
      <nav className={`border-b backdrop-blur-md sticky top-0 z-50 ${
        darkMode ? 'border-slate-800 bg-[#0B1120]/80' : 'border-slate-200 bg-white/80'
      }`}>
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              darkMode ? 'bg-blue-600 text-white' : 'bg-blue-600 text-white'
            }`}>
              <TrendingUp size={20} />
            </div>
            <span className="font-bold text-lg tracking-tight">Market Scenario Generator</span>
          </div>
          
          <div className="flex items-center gap-4">
            <div className={`px-3 py-1 rounded-full text-xs font-medium flex items-center gap-2 ${
              darkMode ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-emerald-100 text-emerald-700 border border-emerald-200'
            }`}>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              System Operational
            </div>
            <button 
              onClick={() => setDarkMode(!darkMode)}
              className={`p-2 rounded-lg transition-colors ${
                darkMode ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-slate-100 text-slate-600'
              }`}
            >
              {darkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        
        {/* Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-slate-900'}`}>Risk Simulation</h1>
            <p className={`mt-1 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              Configure parameters to run Monte Carlo simulations
            </p>
          </div>
          <div className="flex gap-2">
            <button className={`px-4 py-2 rounded-lg font-medium text-sm border transition-colors ${
              darkMode 
                ? 'border-slate-700 hover:bg-slate-800 text-slate-300' 
                : 'border-slate-200 hover:bg-slate-50 text-slate-700'
            }`}>
              Load Preset
            </button>
            <button className={`px-4 py-2 rounded-lg font-medium text-sm border transition-colors ${
               darkMode 
                ? 'border-slate-700 hover:bg-slate-800 text-slate-300' 
                : 'border-slate-200 hover:bg-slate-50 text-slate-700'
            }`}>
              Compare Models
            </button>
          </div>
        </div>

        {/* Configuration Card */}
        <Card darkMode={darkMode}>
          <div className="flex items-center gap-2 mb-6">
            <Settings className={darkMode ? 'text-blue-400' : 'text-blue-600'} size={20} />
            <h2 className="text-xl font-semibold">Configuration</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <InputGroup 
              label="Ticker Symbol" 
              value={config.ticker} 
              onChange={(v) => setConfig({...config, ticker: v})} 
              darkMode={darkMode}
            />
            <InputGroup 
              label="Historical Years" 
              value={config.histYears} 
              type="number"
              onChange={(v) => setConfig({...config, histYears: v})} 
              darkMode={darkMode}
            />
             <InputGroup 
              label="Simulation Horizon (days)" 
              value={config.simHorizon} 
              type="number"
              onChange={(v) => setConfig({...config, simHorizon: v})} 
              darkMode={darkMode}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
             <div className="md:col-span-1">
                <InputGroup 
                  label="Number of Paths" 
                  value={config.paths} 
                  type="number"
                  onChange={(v) => setConfig({...config, paths: v})} 
                  darkMode={darkMode}
                />
             </div>
             
             <div className="md:col-span-3 flex flex-col gap-2">
                <label className={`text-sm font-medium ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                  Model Type
                </label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <ModelCard 
                    title="Gaussian" 
                    desc="Normal distribution baseline"
                    icon={Activity}
                    selected={config.model === 'Gaussian'}
                    onClick={() => setConfig({...config, model: 'Gaussian'})}
                    darkMode={darkMode}
                  />
                  <ModelCard 
                    title="GMM" 
                    desc="Fat-tailed multi-regime"
                    icon={BarChart3}
                    selected={config.model === 'GMM'}
                    onClick={() => setConfig({...config, model: 'GMM'})}
                    darkMode={darkMode}
                  />
                  <ModelCard 
                    title="EWMA" 
                    desc="Time-varying volatility"
                    icon={TrendingUp}
                    selected={config.model === 'EWMA'}
                    onClick={() => setConfig({...config, model: 'EWMA'})}
                    darkMode={darkMode}
                  />
                </div>
             </div>
          </div>

          <button 
            onClick={runSimulation}
            disabled={loading}
            className={`w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all transform active:scale-[0.99] ${
              loading 
                ? 'opacity-70 cursor-not-allowed'
                : 'hover:shadow-lg hover:shadow-blue-500/25'
            } ${
              darkMode 
                ? 'bg-slate-100 text-slate-900 hover:bg-white' // High contrast button in dark mode
                : 'bg-slate-900 text-white hover:bg-slate-800' // Dark button in light mode
            }`}
          >
            {loading ? (
              <>Running Simulation...</>
            ) : (
              <>
                <Play size={20} fill="currentColor" /> Run Simulation
              </>
            )}
          </button>
        </Card>

        {/* Results Section */}
        {results && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
               <StatCard label="Value at Risk (95%)" value={results.metrics.var} sub="Daily" darkMode={darkMode} trend="down" />
               <StatCard label="Conditional VaR" value={results.metrics.cvar} sub="Tail Risk" darkMode={darkMode} trend="down" />
               <StatCard label="Sharpe Ratio" value={results.metrics.sharpe} sub="Risk Adj. Return" darkMode={darkMode} trend="up" />
               <StatCard label="Annualized Volatility" value={results.metrics.volatility} darkMode={darkMode} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Chart */}
              <Card className="lg:col-span-2 h-[400px] flex flex-col" darkMode={darkMode}>
                 <div className="flex justify-between items-center mb-4">
                    <h3 className="font-semibold text-lg">Projected Paths</h3>
                    <div className="flex gap-2 text-xs">
                        <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-blue-500"></div> Mean</span>
                        <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-slate-500"></div> Confidence</span>
                    </div>
                 </div>
                 <div className="flex-1 w-full min-h-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={results.chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke={darkMode ? "#334155" : "#e2e8f0"} vertical={false} />
                        <XAxis 
                          dataKey="day" 
                          stroke={darkMode ? "#94a3b8" : "#64748b"} 
                          tickLine={false}
                          axisLine={false}
                        />
                        <YAxis 
                          stroke={darkMode ? "#94a3b8" : "#64748b"} 
                          tickLine={false}
                          axisLine={false}
                          domain={['auto', 'auto']}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: darkMode ? '#1e293b' : '#fff',
                            borderColor: darkMode ? '#334155' : '#e2e8f0',
                            borderRadius: '8px',
                            color: darkMode ? '#fff' : '#000'
                          }}
                        />
                        <Line type="monotone" dataKey="p95" stroke="#64748b" strokeWidth={1} strokeDasharray="5 5" dot={false} />
                        <Line type="monotone" dataKey="mean" stroke="#3b82f6" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="p5" stroke="#64748b" strokeWidth={1} strokeDasharray="5 5" dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                 </div>
              </Card>

              {/* Extreme Scenarios Table */}
              <Card className="lg:col-span-1" darkMode={darkMode}>
                <div className="flex items-center gap-2 mb-4">
                  <AlertTriangle size={18} className="text-amber-500" />
                  <h3 className="font-semibold text-lg">Extreme Scenarios</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className={`border-b ${darkMode ? 'border-slate-700' : 'border-slate-200'}`}>
                        <th className={`pb-3 text-left font-medium ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Scenario</th>
                        <th className={`pb-3 text-right font-medium ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Return</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {results.extremes.map((item, idx) => (
                        <tr key={idx} className="group">
                          <td className="py-3 pr-4">
                            <div className="font-medium">{item.name}</div>
                            <div className={`text-xs ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                               Prob: {item.prob}
                            </div>
                          </td>
                          <td className={`py-3 text-right font-mono font-medium ${
                            item.return.startsWith('+') ? 'text-emerald-500' : 'text-rose-500'
                          }`}>
                            {item.return}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <button className={`w-full mt-4 text-xs flex items-center justify-center gap-1 py-2 rounded transition-colors ${
                      darkMode 
                        ? 'bg-slate-800 hover:bg-slate-700 text-slate-400' 
                        : 'bg-slate-100 hover:bg-slate-200 text-slate-600'
                    }`}>
                      View Full Distribution <ArrowRight size={12} />
                  </button>
                </div>
              </Card>
            </div>
          </div>
        )}

      </main>
    </div>
  );
};

export default App;