import PrivateWorkspaceControl from '../features/workspace/PrivateWorkspace.jsx';
import { Moon, Sun, ArrowUpRight, Menu, X } from 'lucide-react';
import { useState } from 'react';

const WORKSPACES = [
  { id: 'overview', label: 'Overview', group: 'Portfolio', title: 'Portfolio overview', description: 'Review your recorded accounts and holdings, then choose what to work on next.' },
  { id: 'ledger', label: 'Ledger', group: 'Portfolio', title: 'Transaction ledger', description: 'Record trades, cash flows and corrections. Review holdings and cash by currency.' },
  { id: 'construction', label: 'Construction', group: 'Portfolio', title: 'Portfolio construction', description: 'Compare allocations, inspect constraints, and understand how each security contributes to portfolio risk.' },
  { id: 'thesis', label: 'Thesis', group: 'Research', title: 'Investment theses', description: 'Keep your reasoning, evidence, and investment decisions in a versioned research record.' },
  { id: 'valuation', label: 'Valuation', group: 'Research', title: 'Valuation & return views', description: 'Compare valuations, bear/base/bull cases and your declared return assumptions.' },
  { id: 'single', label: 'Single-asset Risk Lab', group: 'Risk & scenarios', title: 'Single-asset Risk Lab', description: 'Model conditional scenarios for one asset using historical volatility. Outputs are not forecasts.' },
  { id: 'portfolio', label: 'Portfolio Risk Lab', group: 'Risk & scenarios', title: 'Portfolio Risk Lab', description: 'Model joint scenarios and see where portfolio volatility and downside risk come from.' },
  { id: 'stress', label: 'Historical & shocks', group: 'Risk & scenarios', title: 'Historical scenarios & shocks', description: 'Replay supplied historical observations, resample joint returns, or examine an explicitly defined security shock.' },
  { id: 'performance', label: 'Performance', group: 'Performance', title: 'Portfolio performance', description: 'Measure recorded investment returns and your capital experience using the ledger and explicit dated valuations.' },
];

export default function PlatformShell({ activeWorkspace, onNavigate, isDark, onToggleTheme, children }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const current = WORKSPACES.find((workspace) => workspace.id === activeWorkspace) || WORKSPACES[0];
  return (
    <div className={`platform-shell ${isDark ? 'platform-dark' : ''}`}>
      <a className="platform-skip-link" href="#workspace-content">Skip to workspace</a>
      <aside className="platform-sidebar">
        <div className="platform-identity">
          <a href="/" className="platform-brand" aria-label="Portfolio Management home">Portfolio<br />Management</a>
        </div>
        <button className="platform-mobile-menu" type="button" aria-controls="workspace-navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={16} aria-hidden="true" /> : <Menu size={16} aria-hidden="true" />} Workspaces</button>
        <nav id="workspace-navigation" className={`platform-navigation ${menuOpen ? 'is-open' : ''}`} aria-label="Workspace navigation">
          {['Portfolio', 'Research', 'Risk & scenarios', 'Performance'].map((group) => (
            <div className="platform-navigation-group" key={group}>
              <p className="platform-navigation-label">{group}</p>
              <div className="platform-navigation-items">
                {WORKSPACES.filter((workspace) => workspace.group === group).map((workspace) => (
                  <button
                    type="button"
                    key={workspace.id}
                    data-workspace={workspace.id}
                    aria-current={current.id === workspace.id ? 'page' : undefined}
                    className="platform-navigation-button"
                    onClick={() => { onNavigate(workspace.id); setMenuOpen(false); }}
                  >{workspace.label}</button>
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="platform-sidebar-footer">
          <a href="https://github.com/Iska555/Market-Scenario-Generator" target="_blank" rel="noreferrer">Project <ArrowUpRight size={14} aria-hidden="true" /></a>
          <button type="button" className="platform-theme-button" onClick={onToggleTheme} aria-label={`Switch to ${isDark ? 'light' : 'dark'} theme`}>
            {isDark ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
          </button>
        </div>
      </aside>
      <main className="platform-main" id="workspace-content" tabIndex={-1}>
        {['single', 'portfolio'].includes(activeWorkspace) ? <div className="workspace-access"><div className="workspace-access-status"><span>No sign-in required</span><div className="workspace-access-actions"><a href="/demo">View demonstration ↗</a><button type="button" onClick={() => onNavigate('overview')}>Private workspace</button></div></div></div> : <PrivateWorkspaceControl />}
        <header className="platform-page-header">
          <p className="platform-eyebrow">{current.group}</p>
          <h1>{current.title}</h1>
          <p className="platform-page-description">{current.description}</p>
        </header>
        <div className="platform-workspace">{children}</div>
      </main>
    </div>
  );
}
