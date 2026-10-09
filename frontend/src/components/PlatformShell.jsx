import PrivateWorkspaceControl from '../features/workspace/PrivateWorkspace.jsx';
import { Moon, Sun } from 'lucide-react';

const WORKSPACES = [
  { id: 'overview', label: 'Overview', group: 'Portfolio', title: 'Portfolio overview', description: 'Review your recorded accounts and holdings, then choose what to work on next.' },
  { id: 'ledger', label: 'Ledger', group: 'Portfolio', title: 'Transaction ledger', description: 'Record immutable transactions, review derived holdings and trade-date cash, and value the account from supplied dated marks.' },
  { id: 'construction', label: 'Construction', group: 'Portfolio', title: 'Portfolio construction', description: 'Compare allocations, inspect constraints, and understand how each security contributes to portfolio risk.' },
  { id: 'thesis', label: 'Thesis', group: 'Research', title: 'Investment theses', description: 'Keep your reasoning, evidence, and investment decisions in a versioned research record.' },
  { id: 'valuation', label: 'Valuation', group: 'Research', title: 'Valuation & return views', description: 'Make assumptions explicit. Review conditional model outcomes before recording an investor return view.' },
  { id: 'single', label: 'Single-asset Risk Lab', group: 'Risk & scenarios', title: 'Single-asset Risk Lab', description: 'Explore conditional scenarios for one asset. Historical data informs risk inputs; simulations are not return forecasts.' },
  { id: 'portfolio', label: 'Portfolio Risk Lab', group: 'Risk & scenarios', title: 'Portfolio Risk Lab', description: 'Explore joint conditional scenarios with explicit weights, rebalancing, horizon, and distribution assumptions.' },
  { id: 'stress', label: 'Historical & shocks', group: 'Risk & scenarios', title: 'Historical scenarios & shocks', description: 'Replay supplied historical observations, resample joint returns, or examine an explicitly defined security shock.' },
  { id: 'performance', label: 'Performance', group: 'Performance', title: 'Portfolio performance', description: 'Measure recorded investment returns and your capital experience using the ledger and explicit dated valuations.' },
];

export default function PlatformShell({ activeWorkspace, onNavigate, isDark, onToggleTheme, children }) {
  const current = WORKSPACES.find((workspace) => workspace.id === activeWorkspace) || WORKSPACES[0];
  return (
    <div className={`platform-shell ${isDark ? 'platform-dark' : ''}`}>
      <a className="platform-skip-link" href="#workspace-content">Skip to workspace</a>
      <aside className="platform-sidebar">
        <div className="platform-identity">
          <p className="platform-brand">Investment Management Workspace</p>
          <p className="platform-brand-detail">Research, portfolios & decisions</p>
        </div>
        <nav className="platform-navigation" aria-label="Workspace navigation">
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
                    onClick={() => onNavigate(workspace.id)}
                  >{workspace.label}</button>
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="platform-sidebar-footer">
          <p>Evidence informs.<br />You decide.</p>
          <button type="button" className="platform-theme-button" onClick={onToggleTheme} aria-label={`Switch to ${isDark ? 'light' : 'dark'} theme`}>
            {isDark ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
          </button>
        </div>
      </aside>
      <main className="platform-main" id="workspace-content" tabIndex={-1}>
        <PrivateWorkspaceControl />
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
