import React from 'react';
import { TrendingUp, TrendingDown, Activity, BarChart3, Zap } from 'lucide-react';

export default function PerformanceCards({ performance }) {
  if (!performance) return null;

  const cards = [
    {
      label: 'Total Return',
      value: performance.total_return_pct != null ? `${performance.total_return_pct >= 0 ? '+' : ''}${performance.total_return_pct.toFixed(2)}%` : '—',
      color: (performance.total_return_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600',
      icon: TrendingUp,
    },
    {
      label: 'Annualized Return',
      value: performance.annualized_return_pct != null ? `${performance.annualized_return_pct >= 0 ? '+' : ''}${performance.annualized_return_pct.toFixed(2)}%` : '—',
      color: (performance.annualized_return_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600',
      icon: BarChart3,
    },
    {
      label: 'Sharpe Ratio',
      value: performance.sharpe_ratio != null ? performance.sharpe_ratio.toFixed(2) : '—',
      color: (performance.sharpe_ratio || 0) >= 1 ? 'text-green-600' : (performance.sharpe_ratio || 0) >= 0 ? 'text-altruistGray-800' : 'text-red-600',
      icon: Zap,
    },
    {
      label: 'Beta (vs S&P 500)',
      value: performance.beta != null ? performance.beta.toFixed(2) : '—',
      color: 'text-altruistGray-800',
      icon: Activity,
    },
    {
      label: 'Volatility',
      value: performance.volatility_pct != null ? `${performance.volatility_pct.toFixed(2)}%` : '—',
      color: 'text-altruistGray-800',
      icon: BarChart3,
    },
  ];

  return (
    <div className="panel-structured overflow-hidden">
      <div className="border-b border-altruistGray-200 px-6 py-4 bg-altruistGray-50">
        <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide">Performance Metrics</h3>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
        {cards.map((card, i) => {
          const Icon = card.icon;
          return (
            <div key={i} className="flex flex-col px-5 py-4 border-b border-altruistGray-200 sm:border-r last:border-r-0 hover:bg-altruistGray-50 transition-colors">
              <div className="flex items-center gap-1.5 mb-2">
                <Icon className="w-3.5 h-3.5 text-altruistBlue" />
                <span className="text-altruistGray-500 text-[10px] font-bold uppercase tracking-widest">{card.label}</span>
              </div>
              <span className={`font-mono font-bold tabular-nums text-[18px] ${card.color}`}>{card.value}</span>
            </div>
          );
        })}
      </div>

      {/* Best / Worst performers */}
      {(performance.best_performer || performance.worst_performer) && (
        <div className="grid grid-cols-2 border-t border-altruistGray-200">
          {performance.best_performer && (
            <div className="flex items-center gap-3 px-5 py-3 border-r border-altruistGray-200">
              <TrendingUp className="w-4 h-4 text-green-600 shrink-0" />
              <div>
                <p className="text-[10px] font-bold text-altruistGray-500 uppercase tracking-widest">Best Performer</p>
                <p className="text-[13px] font-bold text-green-600">
                  {performance.best_performer.ticker}
                  <span className="text-[12px] ml-1 font-medium">
                    ({performance.best_performer.pnl_pct >= 0 ? '+' : ''}{performance.best_performer.pnl_pct.toFixed(2)}%)
                  </span>
                </p>
              </div>
            </div>
          )}
          {performance.worst_performer && (
            <div className="flex items-center gap-3 px-5 py-3">
              <TrendingDown className="w-4 h-4 text-red-600 shrink-0" />
              <div>
                <p className="text-[10px] font-bold text-altruistGray-500 uppercase tracking-widest">Worst Performer</p>
                <p className="text-[13px] font-bold text-red-600">
                  {performance.worst_performer.ticker}
                  <span className="text-[12px] ml-1 font-medium">
                    ({performance.worst_performer.pnl_pct >= 0 ? '+' : ''}{performance.worst_performer.pnl_pct.toFixed(2)}%)
                  </span>
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
