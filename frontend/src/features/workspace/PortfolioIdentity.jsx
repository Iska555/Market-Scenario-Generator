import { modeLabel } from './portfolioIdentity.js';

export default function PortfolioIdentity({ portfolio }) {
  if (!portfolio) return null;
  return <aside aria-label="Portfolio identity" className="mt-4 rounded-xl border border-slate-400/40 bg-slate-500/5 p-4 text-sm">
    <p className="font-semibold">{modeLabel(portfolio)}</p>
    <p className="mt-2 text-xs opacity-75">Private workspace · publication is managed separately. History belongs to this portfolio identity and cannot be relabelled or combined with another mode.</p>
    {portfolio.identity?.recorded_at && <p className="mt-2 text-xs opacity-75">Identity recorded {portfolio.identity.recorded_at}. This is the actual creation time, distinct from any example transaction date.</p>}
  </aside>;
}
