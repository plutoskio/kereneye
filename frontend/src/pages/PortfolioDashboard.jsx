import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp, TrendingDown, Plus, RefreshCw, Activity, DollarSign,
  LayoutDashboard, Newspaper, Clock, ExternalLink, Wallet
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, LineChart, Line, XAxis, YAxis } from 'recharts';
import AddHoldingModal from '../components/AddHoldingModal';
import SellModal from '../components/SellModal';
import CashModal from '../components/CashModal';
import PerformanceCards from '../components/PerformanceCards';
import MarketStatusBar from '../components/MarketStatusBar';
import Background3D from '../Background3D';

const API = 'http://localhost:8000';

const SECTOR_COLORS = [
  '#1565C0', '#0D47A1', '#2196F3', '#42A5F5', '#64B5F6',
  '#1B5E20', '#2E7D32', '#43A047', '#66BB6A',
  '#E65100', '#EF6C00', '#F57C00', '#FB8C00',
  '#4A148C', '#6A1B9A', '#7B1FA2',
];

export default function PortfolioDashboard() {
  const navigate = useNavigate();
  const [holdings, setHoldings] = useState([]);
  const [summary, setSummary] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [perfPeriod, setPerfPeriod] = useState('1y');
  const [loadingHoldings, setLoadingHoldings] = useState(true);
  const [loadingPerf, setLoadingPerf] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showSellModal, setShowSellModal] = useState(null); // holds the holding to sell
  const [showCashModal, setShowCashModal] = useState(false);
  const [marketData, setMarketData] = useState(null);

  // Daily Market Brief state
  const [marketBrief, setMarketBrief] = useState(null);
  const [loadingBrief, setLoadingBrief] = useState(false);
  const [briefStatus, setBriefStatus] = useState('');
  const [briefCacheAge, setBriefCacheAge] = useState(0);

  // Holdings news
  const [holdingsNews, setHoldingsNews] = useState([]);
  const [loadingNews, setLoadingNews] = useState(false);

  // Market status
  const [marketStatus, setMarketStatus] = useState(null);

  // Time since last refresh
  const [secondsSinceUpdate, setSecondsSinceUpdate] = useState(0);

  // ---------------------------------------------------------------
  // Fetch helpers
  // ---------------------------------------------------------------
  const fetchHoldings = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/portfolio/summary`);
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
        setHoldings(data.holdings || []);
        setLastUpdated(new Date());
        setSecondsSinceUpdate(0);
      }
    } catch (err) {
      console.error('Failed to fetch holdings:', err);
    } finally {
      setLoadingHoldings(false);
    }
  }, []);

  const fetchPerformance = useCallback(async (period = perfPeriod) => {
    setLoadingPerf(true);
    try {
      const res = await fetch(`${API}/api/portfolio/performance?period=${period}`);
      if (res.ok) {
        const data = await res.json();
        setPerformance(data);
      }
    } catch (err) {
      console.error('Failed to fetch performance:', err);
    } finally {
      setLoadingPerf(false);
    }
  }, [perfPeriod]);

  const fetchMarketStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/portfolio/market-status`);
      if (res.ok) {
        const data = await res.json();
        setMarketStatus(data.markets);
      }
    } catch (err) {
      console.error('Failed to fetch market status:', err);
    }
  }, []);

  const fetchMarketOverview = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/market/overview`);
      if (res.ok) {
        const data = await res.json();
        setMarketData(data);
      }
    } catch (err) {
      console.error('Failed to fetch market overview:', err);
    }
  }, []);

  const fetchBriefCache = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/market/brief`);
      if (res.ok) {
        const data = await res.json();
        setMarketBrief(data.brief);
        setBriefCacheAge(data.age_hours || 0);
      }
    } catch (err) {
      console.error('Failed to fetch brief cache:', err);
    }
  }, []);

  const fetchHoldingsNews = useCallback(async () => {
    if (holdings.length === 0) return;
    setLoadingNews(true);
    try {
      const res = await fetch(`${API}/api/portfolio/news`);
      if (res.ok) {
        const data = await res.json();
        setHoldingsNews(data.holdings_news || []);
      }
    } catch (err) {
      console.error('Failed to fetch holdings news:', err);
    } finally {
      setLoadingNews(false);
    }
  }, [holdings.length]);

  // ---------------------------------------------------------------
  // Initial load
  // ---------------------------------------------------------------
  useEffect(() => {
    fetchHoldings();
    fetchMarketStatus();
    fetchMarketOverview();
    fetchBriefCache();
  }, []);

  // Fetch performance when holdings change
  useEffect(() => {
    if (holdings.length > 0) {
      fetchPerformance();
      fetchHoldingsNews();
    }
  }, [holdings.length]);

  // ---------------------------------------------------------------
  // Auto-refresh holdings (30s market open, 5min closed)
  // ---------------------------------------------------------------
  useEffect(() => {
    const isAnyMarketOpen = marketStatus?.some(m => m.is_open) || false;
    const interval = isAnyMarketOpen ? 30000 : 300000; // 30s or 5min

    const timer = setInterval(() => {
      fetchHoldings();
      fetchMarketStatus();
    }, interval);

    return () => clearInterval(timer);
  }, [marketStatus, fetchHoldings, fetchMarketStatus]);

  // Seconds since last update counter
  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsSinceUpdate(prev => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // ---------------------------------------------------------------
  // Market brief generation
  // ---------------------------------------------------------------
  const generateMarketBrief = async () => {
    try {
      setLoadingBrief(true);
      setBriefStatus('Collecting Market Data');

      const statusInterval = setInterval(async () => {
        try {
          const statusRes = await fetch(`${API}/api/market/brief/status`);
          if (statusRes.ok) {
            const statusData = await statusRes.json();
            setBriefStatus(statusData.status || '');
          }
        } catch (e) { /* ignore */ }
      }, 2000);

      const res = await fetch(`${API}/api/market/brief`, { method: 'POST' });
      clearInterval(statusInterval);

      if (!res.ok) throw new Error('Failed to generate brief.');
      const data = await res.json();
      setMarketBrief(data.brief);
      setBriefCacheAge(0);
    } catch (err) {
      console.error(err);
      setMarketBrief('Failed to generate daily brief.');
    } finally {
      setLoadingBrief(false);
    }
  };

  // ---------------------------------------------------------------
  // Holding actions
  // ---------------------------------------------------------------
  const handleAddHolding = async (ticker, shares, avgCost) => {
    try {
      const res = await fetch(`${API}/api/portfolio/holdings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, shares, avg_cost: avgCost }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to add holding');
      }
      setShowAddModal(false);
      fetchHoldings();
    } catch (err) {
      throw err; // Let the modal handle the error
    }
  };

  const handleSellHolding = async (ticker, shares, price) => {
    try {
      const res = await fetch(`${API}/api/portfolio/holdings/${ticker}/sell`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shares, price }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to sell');
      }
      setShowSellModal(null);
      fetchHoldings();
    } catch (err) {
      throw err;
    }
  };

  const handleSetCash = async (amount) => {
    try {
      const res = await fetch(`${API}/api/portfolio/cash`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount }),
      });
      if (res.ok) {
        setShowCashModal(false);
        fetchHoldings();
      }
    } catch (err) {
      console.error('Failed to set cash:', err);
    }
  };

  // ---------------------------------------------------------------
  // Formatting helpers
  // ---------------------------------------------------------------
  const formatCurrency = (val) => {
    if (val === null || val === undefined) return '—';
    if (Math.abs(val) >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
    if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
    if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
    return `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatUpdateTime = (secs) => {
    if (secs < 60) return `${secs}s ago`;
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
    return `${Math.floor(secs / 3600)}h ago`;
  };

  // ---------------------------------------------------------------
  // Derived data
  // ---------------------------------------------------------------
  const sectorData = summary?.sector_allocation
    ? Object.entries(summary.sector_allocation).map(([name, value], i) => ({
        name,
        value,
        color: SECTOR_COLORS[i % SECTOR_COLORS.length],
      }))
    : [];

  const isEmpty = !loadingHoldings && holdings.length === 0;

  // ---------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------
  return (
    <div className="animate-fade-in-up space-y-6">
      {/* MARKET STATUS BAR */}
      <MarketStatusBar marketStatus={marketStatus} marketData={marketData} />

      {isEmpty ? (
        // EMPTY STATE — with 3D background
        <div className="relative h-[70vh] flex flex-col rounded-sm overflow-hidden bg-altruistWhite border border-altruistGray-200 shadow-sm">
          <Background3D />
          <div className="relative z-10 flex-1 flex flex-col items-center justify-center p-12">
            <LayoutDashboard className="w-12 h-12 text-altruistBlue mb-6 opacity-60" />
            <h2 className="text-[24px] font-semibold text-altruistDark tracking-tight mb-2">Your Portfolio is Empty</h2>
            <p className="text-[14px] text-altruistGray-500 font-medium mb-8 text-center max-w-md">
              Start building your portfolio by adding stock holdings. Track performance, analyze risk, and get AI-powered insights.
            </p>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-altruistBlue text-white px-6 py-3 rounded-sm text-[13px] font-bold uppercase tracking-wide hover:bg-blue-800 transition-colors flex items-center gap-2 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Add Your First Holding
            </button>
          </div>

          {/* DAILY BRIEF (also shown in empty state) */}
          <div className="relative z-10 w-full px-6 pb-6">
            <div className="bg-altruistWhite/85 backdrop-blur-md border border-altruistGray-200/50 rounded-sm shadow-lg overflow-hidden pointer-events-auto max-w-3xl mx-auto">
              <div className="border-b border-altruistGray-200 px-6 py-3 flex justify-between items-center bg-altruistGray-50/80">
                <h3 className="text-[12px] font-bold text-altruistGray-800 uppercase tracking-wide flex items-center gap-2">
                  <LayoutDashboard className="w-3.5 h-3.5 text-altruistBlue" /> Daily Market & World Brief
                </h3>
                <div className="flex items-center gap-3">
                  {marketBrief && !loadingBrief && (
                    <span className="text-[10px] font-medium text-altruistGray-400 uppercase tracking-widest">
                      {briefCacheAge === 0 ? 'Live' : `${briefCacheAge}h ago`}
                    </span>
                  )}
                  {marketBrief && !loadingBrief && (
                    <button onClick={generateMarketBrief} disabled={loadingBrief} className="text-[10px] font-bold text-altruistBlue uppercase tracking-widest hover:text-blue-800 transition-colors disabled:opacity-50 flex items-center gap-1 bg-altruistBlue/10 px-2.5 py-1 rounded-sm">
                      <RefreshCw className="w-3 h-3" /> Refresh
                    </button>
                  )}
                </div>
              </div>
              <div className="p-5">
                {marketBrief ? (
                  <div className="prose prose-sm max-w-none prose-slate prose-headings:font-bold prose-headings:text-altruistDark prose-h2:text-[15px] prose-h2:mt-0 prose-h2:mb-3 prose-h2:text-altruistBlue prose-p:text-[13px] prose-p:leading-relaxed prose-p:text-altruistGray-800 prose-p:my-1.5 prose-strong:text-altruistDark">
                    <ReactMarkdown>{marketBrief}</ReactMarkdown>
                  </div>
                ) : loadingBrief ? (
                  <div className="flex flex-col items-center justify-center py-6 animate-fade-in-up">
                    <div className="w-10 h-10 rounded-full border-2 border-altruistBlue border-t-transparent animate-spin mb-3" />
                    <p className="text-[13px] font-bold text-altruistDark tracking-wide">{briefStatus || 'Synthesizing Intelligence'}</p>
                    <p className="text-[11px] text-altruistGray-500 font-medium mt-1">Analyzing Finnhub, FRED, GDELT sources...</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-6">
                    <p className="text-[13px] font-medium text-altruistGray-600 mb-4 text-center">
                      Get today's AI-generated summary of global markets, macro data, and world events.
                    </p>
                    <button onClick={generateMarketBrief} className="bg-altruistBlue text-white px-5 py-2 rounded-sm text-[12px] font-bold uppercase tracking-wide hover:bg-blue-800 transition-colors flex items-center gap-2">
                      <Activity className="w-3.5 h-3.5" /> Generate Daily Brief
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        // PORTFOLIO DASHBOARD
        <div className="space-y-6">
          {/* PORTFOLIO HEADER */}
          <div className="flex justify-between items-end">
            <div>
              <p className="text-[12px] font-bold text-altruistGray-400 uppercase tracking-widest mb-1">Portfolio Value</p>
              <h2 className="text-[40px] leading-tight font-mono font-medium text-altruistDark tabular-nums">
                {formatCurrency(summary?.total_value)}
              </h2>
              <div className="flex items-center gap-4 mt-1 flex-wrap">
                {/* Unrealized P&L */}
                <span className={`flex items-center gap-1 text-[14px] font-bold ${(summary?.total_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {(summary?.total_pnl || 0) >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                  {formatCurrency(Math.abs(summary?.total_pnl || 0))}
                  <span className="text-[12px] ml-1">({(summary?.total_pnl_pct || 0).toFixed(2)}%)</span>
                  <span className="text-[10px] text-altruistGray-400 font-medium uppercase tracking-widest ml-1">unrealized</span>
                </span>
                {/* Realized P&L */}
                {(summary?.realized_pnl || 0) !== 0 && (
                  <span className={`flex items-center gap-1 text-[13px] font-bold ${(summary?.realized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    <DollarSign className="w-3.5 h-3.5" />
                    {(summary?.realized_pnl || 0) >= 0 ? '+' : ''}{formatCurrency(summary?.realized_pnl || 0)}
                    <span className="text-[10px] text-altruistGray-400 font-medium uppercase tracking-widest ml-1">realized</span>
                  </span>
                )}
                {/* Cash */}
                <button
                  onClick={() => setShowCashModal(true)}
                  className="flex items-center gap-1 text-[13px] font-bold text-altruistGray-600 hover:text-altruistBlue transition-colors cursor-pointer"
                  title="Click to edit cash balance"
                >
                  <Wallet className="w-3.5 h-3.5" />
                  {formatCurrency(summary?.cash_balance || 0)}
                  <span className="text-[10px] text-altruistGray-400 font-medium uppercase tracking-widest ml-1">cash</span>
                </button>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[10px] font-medium text-altruistGray-400 uppercase tracking-widest flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Updated {formatUpdateTime(secondsSinceUpdate)}
              </span>
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-altruistBlue text-white px-4 py-2.5 rounded-sm text-[12px] font-bold uppercase tracking-wide hover:bg-blue-800 transition-colors flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Holding
              </button>
            </div>
          </div>

          {/* MAIN GRID */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
            {/* LEFT: Holdings Table + Performance */}
            <div className="xl:col-span-8 space-y-6">
              {/* HOLDINGS TABLE */}
              <div className="panel-structured overflow-hidden">
                <div className="border-b border-altruistGray-200 px-6 py-4 bg-altruistGray-50">
                  <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide">
                    Holdings ({holdings.length})
                  </h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-[13px]">
                    <thead>
                      <tr className="border-b border-altruistGray-200 bg-altruistGray-50/50">
                        <th className="text-left px-6 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">Ticker</th>
                        <th className="text-left px-4 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">Name</th>
                        <th className="text-right px-4 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">Shares</th>
                        <th className="text-right px-4 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">Avg Cost</th>
                        <th className="text-right px-4 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">Price</th>
                        <th className="text-right px-4 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">P&L</th>
                        <th className="text-right px-4 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">Weight</th>
                        <th className="text-right px-6 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {holdings.map((h, i) => (
                        <tr
                          key={h.ticker}
                          className="border-b border-altruistGray-100 hover:bg-altruistGray-50 transition-colors cursor-pointer"
                          onClick={() => navigate(`/stock/${h.ticker}`)}
                        >
                          <td className="px-6 py-4 font-mono font-bold text-altruistBlue">{h.ticker}</td>
                          <td className="px-4 py-4 text-altruistGray-800 font-medium truncate max-w-[200px]">{h.name}</td>
                          <td className="px-4 py-4 text-right font-mono tabular-nums">{h.shares}</td>
                          <td className="px-4 py-4 text-right font-mono tabular-nums">${h.avg_cost?.toFixed(2)}</td>
                          <td className="px-4 py-4 text-right font-mono tabular-nums font-medium">${h.current_price?.toFixed(2)}</td>
                          <td className={`px-4 py-4 text-right font-mono tabular-nums font-bold ${h.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {h.pnl >= 0 ? '+' : ''}${h.pnl?.toFixed(2)}
                            <span className="text-[11px] ml-1 font-medium">({h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct?.toFixed(2)}%)</span>
                          </td>
                          <td className="px-4 py-4 text-right font-mono tabular-nums text-altruistGray-500">{h.weight_pct?.toFixed(1)}%</td>
                          <td className="px-6 py-4 text-right">
                            <button
                              onClick={(e) => { e.stopPropagation(); setShowSellModal(h); }}
                              className="text-[10px] font-bold text-red-500 uppercase tracking-widest hover:text-red-700 hover:bg-red-50 px-2 py-1 rounded-sm transition-colors"
                              title="Sell shares"
                            >
                              Sell
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* PERFORMANCE CARDS */}
              {performance && <PerformanceCards performance={performance} />}

              {/* BENCHMARK CHART */}
              {performance && performance.portfolio_history.length > 0 && (
                <div className="panel-structured overflow-hidden">
                  <div className="border-b border-altruistGray-200 px-6 py-4 bg-altruistGray-50 flex justify-between items-center">
                    <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide">Portfolio vs S&P 500</h3>
                    <div className="flex items-center gap-2">
                      {['1mo', '3mo', '6mo', '1y', '2y', '5y'].map((p) => (
                        <button
                          key={p}
                          onClick={() => { setPerfPeriod(p); fetchPerformance(p); }}
                          className={`text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-sm transition-colors ${
                            perfPeriod === p
                              ? 'bg-altruistBlue text-white'
                              : 'text-altruistGray-400 hover:text-altruistDark hover:bg-altruistGray-100'
                          }`}
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="p-6 h-[350px]">
                    {loadingPerf ? (
                      <div className="h-full flex items-center justify-center">
                        <div className="w-10 h-10 rounded-full border-2 border-altruistBlue border-t-transparent animate-spin" />
                      </div>
                    ) : (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart margin={{ top: 5, right: 0, bottom: 0, left: -20 }}>
                          <XAxis dataKey="date" data={performance.portfolio_history} hide />
                          <YAxis hide domain={['auto', 'auto']} />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #E5E7EB', borderRadius: '4px', color: '#111827', fontFamily: 'monospace', fontSize: '12px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                            formatter={(value) => [`$${value.toFixed(2)}`, '']}
                          />
                          <Line data={performance.portfolio_history} type="monotone" dataKey="value" stroke="#1565C0" strokeWidth={2.5} dot={false} name="Portfolio" />
                          {performance.benchmark_history.length > 0 && (
                            <Line data={performance.benchmark_history} type="monotone" dataKey="value" stroke="#9CA3AF" strokeWidth={1.5} dot={false} strokeDasharray="5 5" name="S&P 500" />
                          )}
                        </LineChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </div>
              )}

              {/* HOLDINGS NEWS */}
              {holdingsNews.length > 0 && (
                <div className="panel-structured overflow-hidden">
                  <div className="border-b border-altruistGray-200 px-6 py-4 bg-altruistGray-50 flex items-center justify-between">
                    <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide flex items-center gap-2">
                      <Newspaper className="w-4 h-4 text-altruistBlue" /> Holdings News Feed
                    </h3>
                    <button
                      onClick={fetchHoldingsNews}
                      disabled={loadingNews}
                      className="text-[10px] font-bold text-altruistBlue uppercase tracking-widest hover:text-blue-800 transition-colors disabled:opacity-50 flex items-center gap-1 bg-altruistBlue/10 px-2.5 py-1 rounded-sm"
                    >
                      {loadingNews ? <RefreshCw className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                      Refresh
                    </button>
                  </div>
                  <div className="divide-y divide-altruistGray-100 max-h-[500px] overflow-y-auto custom-scrollbar">
                    {holdingsNews.map((hn) =>
                      hn.news.map((article, j) => (
                        <a
                          key={`${hn.ticker}-${j}`}
                          href={article.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-start gap-4 px-6 py-3 hover:bg-altruistGray-50 transition-colors group"
                        >
                          <span className="text-[11px] font-mono font-bold text-altruistBlue bg-altruistBlue/10 px-2 py-0.5 rounded-sm mt-0.5 shrink-0">
                            {hn.ticker}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="text-[13px] font-medium text-altruistGray-800 truncate group-hover:text-altruistBlue transition-colors">
                              {article.title}
                            </p>
                            <p className="text-[11px] text-altruistGray-400 mt-0.5">{article.publisher}</p>
                          </div>
                          <ExternalLink className="w-3.5 h-3.5 text-altruistGray-300 shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </a>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* RIGHT: Allocation + Brief */}
            <div className="xl:col-span-4 space-y-6">
              {/* SECTOR ALLOCATION */}
              {sectorData.length > 0 && (
                <div className="panel-structured overflow-hidden">
                  <div className="border-b border-altruistGray-200 px-6 py-4 bg-altruistGray-50">
                    <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide">Sector Allocation</h3>
                  </div>
                  <div className="p-6">
                    <div className="h-[250px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={sectorData}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={100}
                            paddingAngle={2}
                            strokeWidth={0}
                          >
                            {sectorData.map((entry, i) => (
                              <Cell key={i} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{ backgroundColor: '#fff', border: '1px solid #E5E7EB', borderRadius: '4px', fontSize: '12px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                            formatter={(value) => [`${value.toFixed(1)}%`, '']}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    {/* Legend */}
                    <div className="space-y-2 mt-4">
                      {sectorData.map((s, i) => (
                        <div key={i} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: s.color }} />
                            <span className="text-[12px] font-medium text-altruistGray-800">{s.name}</span>
                          </div>
                          <span className="text-[12px] font-mono font-bold text-altruistGray-600">{s.value.toFixed(1)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* MARKET BRIEF */}
              <div className="panel-structured overflow-hidden">
                <div className="border-b border-altruistGray-200 px-6 py-3 flex justify-between items-center bg-altruistGray-50">
                  <h3 className="text-[12px] font-bold text-altruistGray-800 uppercase tracking-wide flex items-center gap-2">
                    <LayoutDashboard className="w-3.5 h-3.5 text-altruistBlue" /> Daily Brief
                  </h3>
                  <div className="flex items-center gap-3">
                    {marketBrief && !loadingBrief && (
                      <span className="text-[10px] font-medium text-altruistGray-400 uppercase tracking-widest">
                        {briefCacheAge === 0 ? 'Live' : `${briefCacheAge}h ago`}
                      </span>
                    )}
                    {marketBrief && !loadingBrief && (
                      <button onClick={generateMarketBrief} disabled={loadingBrief} className="text-[10px] font-bold text-altruistBlue uppercase tracking-widest hover:text-blue-800 transition-colors disabled:opacity-50 flex items-center gap-1 bg-altruistBlue/10 px-2.5 py-1 rounded-sm">
                        <RefreshCw className="w-3 h-3" /> Refresh
                      </button>
                    )}
                  </div>
                </div>
                <div className="p-5 max-h-[500px] overflow-y-auto custom-scrollbar">
                  {marketBrief ? (
                    <div className="prose prose-sm max-w-none prose-slate prose-headings:font-bold prose-headings:text-altruistDark prose-h2:text-[15px] prose-h2:mt-0 prose-h2:mb-3 prose-h2:text-altruistBlue prose-p:text-[13px] prose-p:leading-relaxed prose-p:text-altruistGray-800 prose-p:my-1.5 prose-strong:text-altruistDark">
                      <ReactMarkdown>{marketBrief}</ReactMarkdown>
                    </div>
                  ) : loadingBrief ? (
                    <div className="flex flex-col items-center justify-center py-6 animate-fade-in-up">
                      <div className="w-10 h-10 rounded-full border-2 border-altruistBlue border-t-transparent animate-spin mb-3" />
                      <p className="text-[13px] font-bold text-altruistDark tracking-wide">{briefStatus || 'Synthesizing Intelligence'}</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-6">
                      <p className="text-[13px] font-medium text-altruistGray-600 mb-4 text-center">
                        Get today's AI-generated summary of global markets.
                      </p>
                      <button onClick={generateMarketBrief} className="bg-altruistBlue text-white px-5 py-2 rounded-sm text-[12px] font-bold uppercase tracking-wide hover:bg-blue-800 transition-colors flex items-center gap-2">
                        <Activity className="w-3.5 h-3.5" /> Generate Brief
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODALS */}
      {showAddModal && (
        <AddHoldingModal
          onClose={() => setShowAddModal(false)}
          onAdd={handleAddHolding}
        />
      )}
      {showSellModal && (
        <SellModal
          holding={showSellModal}
          onClose={() => setShowSellModal(null)}
          onSell={handleSellHolding}
        />
      )}
      {showCashModal && (
        <CashModal
          currentCash={summary?.cash_balance || 0}
          onClose={() => setShowCashModal(false)}
          onSave={handleSetCash}
        />
      )}
    </div>
  );
}
