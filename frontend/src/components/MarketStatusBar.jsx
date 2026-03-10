import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Clock } from 'lucide-react';

export default function MarketStatusBar({ marketStatus, marketData }) {
  const [countdowns, setCountdowns] = useState({});

  // Live countdown timer
  useEffect(() => {
    if (!marketStatus) return;

    // Initialize countdowns from server data
    const initial = {};
    marketStatus.forEach(m => {
      initial[m.name] = m.countdown_seconds;
    });
    setCountdowns(initial);

    const timer = setInterval(() => {
      setCountdowns(prev => {
        const next = { ...prev };
        Object.keys(next).forEach(k => {
          if (next[k] > 0) next[k] -= 1;
        });
        return next;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [marketStatus]);

  const formatCountdown = (totalSeconds) => {
    if (totalSeconds <= 0) return '—';
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  return (
    <div className="panel-structured overflow-hidden">
      <div className="flex items-center justify-between px-6 py-3 flex-wrap gap-4">
        {/* Market Status Badges */}
        <div className="flex items-center gap-5">
          {marketStatus ? (
            marketStatus.map((m, i) => (
              <div key={i} className="flex items-center gap-2.5">
                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-sm border ${
                  m.is_open
                    ? 'bg-green-50 border-green-200 text-green-700'
                    : 'bg-altruistGray-50 border-altruistGray-200 text-altruistGray-500'
                }`}>
                  <div className={`w-2 h-2 rounded-full ${m.is_open ? 'bg-green-500 animate-pulse' : 'bg-altruistGray-400'}`} />
                  <span className="text-[11px] font-bold uppercase tracking-widest">{m.name}</span>
                  <span className="text-[10px] font-medium">{m.is_open ? 'OPEN' : 'CLOSED'}</span>
                </div>
                <span className="text-[10px] font-mono text-altruistGray-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {m.countdown_label} {formatCountdown(countdowns[m.name] ?? m.countdown_seconds)}
                </span>
              </div>
            ))
          ) : (
            <div className="text-[11px] font-medium text-altruistGray-400 uppercase tracking-widest animate-pulse">
              Loading market status...
            </div>
          )}
        </div>

        {/* Indices Ribbon */}
        <div className="flex items-center gap-6 overflow-x-auto hide-scrollbar">
          {marketData ? (
            marketData.indices.map((idx, i) => (
              <div key={i} className="flex items-center gap-2 shrink-0">
                <span className="text-[11px] font-bold text-altruistGray-600 uppercase tracking-wide">{idx.name}</span>
                <span className="font-mono text-[12px] font-medium text-altruistDark tabular-nums">{idx.price.toFixed(0)}</span>
                <span className={`flex items-center text-[11px] font-bold tabular-nums ${idx.change_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {idx.change_pct >= 0 ? <TrendingUp className="w-3 h-3 mr-0.5" /> : <TrendingDown className="w-3 h-3 mr-0.5" />}
                  {Math.abs(idx.change_pct).toFixed(2)}%
                </span>
              </div>
            ))
          ) : (
            <div className="text-[11px] font-medium text-altruistGray-400 uppercase tracking-widest animate-pulse">
              Loading indices...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
