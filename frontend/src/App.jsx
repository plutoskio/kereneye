import React, { useState } from 'react';
import { Search, Loader2, TrendingUp, AlertCircle, FileText, Database } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import ReactMarkdown from 'react-markdown';
import './index.css';

function App() {
  const [ticker, setTicker] = useState('');
  const [loadingInitial, setLoadingInitial] = useState(false);
  const [loadingReport, setLoadingReport] = useState(false);
  const [error, setError] = useState(null);

  const [companyData, setCompanyData] = useState(null);
  const [report, setReport] = useState(null);

  const fetchCompanyData = async (symbol) => {
    try {
      const res = await fetch(`http://localhost:8000/api/company/${symbol}`);
      if (!res.ok) throw new Error('Company not found');
      const data = await res.json();
      setCompanyData(data);
    } catch (err) {
      setError(err.message);
      setLoadingInitial(false);
    }
  };

  const fetchResearchReport = async (symbol) => {
    try {
      setLoadingReport(true);
      const res = await fetch(`http://localhost:8000/api/research/${symbol}`);
      if (!res.ok) throw new Error('Failed to generate report');
      const data = await res.json();
      setReport(data.report);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingReport(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!ticker.trim()) return;

    setError(null);
    setCompanyData(null);
    setReport(null);
    setLoadingInitial(true);

    const symbol = ticker.trim().toUpperCase();

    // 1. Fetch fast initial data to draw the dashboard
    await fetchCompanyData(symbol);
    setLoadingInitial(false);

    // 2. Trigger the AI to write the detailed report
    if (!error) {
      fetchResearchReport(symbol);
    }
  };

  const formatCurrency = (val) => {
    if (!val) return 'N/A';
    if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
    if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
    if (val >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
    return `$${val.toFixed(2)}`;
  };

  const formatPct = (val) => {
    if (val === undefined || val === null) return 'N/A';
    return `${(val * 100).toFixed(2)}%`;
  };

  return (
    <div className="min-h-screen bg-grad-dark text-slate-100 font-sans selection:bg-indigo-500/30">
      {/* HEADER */}
      <header className={`transition-all duration-700 ease-in-out flex flex-col items-center justify-center
        ${companyData ? 'py-8 border-b border-white/5 bg-black/40 backdrop-blur-xl' : 'h-screen'}`}>

        <div className="flex items-center gap-3 mb-8">
          <div className="p-3 bg-indigo-500/20 rounded-xl border border-indigo-400/30 ring-1 ring-inset ring-white/10 shadow-[0_0_30px_rgba(99,102,241,0.2)]">
            <TrendingUp className="w-8 h-8 text-indigo-400" />
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400">
            KerenEye
          </h1>
        </div>

        {!companyData && (
          <p className="text-slate-400 mb-8 max-w-md text-center text-lg leading-relaxed">
            Institutional-grade equity research powered by multi-agent AI orchestration.
          </p>
        )}

        <form onSubmit={handleSearch} className="relative w-full max-w-lg group">
          <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl blur opacity-25 group-focus-within:opacity-50 transition duration-500"></div>
          <div className="relative flex items-center bg-[#131620] ring-1 ring-white/10 rounded-2xl overflow-hidden backdrop-blur-sm">
            <Search className="w-6 h-6 text-slate-400 ml-4" />
            <input
              type="text"
              placeholder="Enter stock ticker (e.g. AAPL, NVDA)..."
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              disabled={loadingInitial}
              className="w-full bg-transparent text-slate-100 placeholder-slate-500 py-4 px-4 text-lg outline-none uppercase font-semibold disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loadingInitial || !ticker.trim()}
              className="bg-indigo-500 hover:bg-indigo-400 text-white px-6 py-4 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center min-w-[120px]"
            >
              {loadingInitial ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Analyze'}
            </button>
          </div>
        </form>

        {error && (
          <div className="mt-6 flex items-center gap-2 text-red-400 bg-red-400/10 px-4 py-3 rounded-xl border border-red-400/20">
            <AlertCircle className="w-5 h-5" />
            <p className="font-medium">{error}</p>
          </div>
        )}
      </header>

      {/* DASHBOARD */}
      {companyData && (
        <main className="max-w-7xl mx-auto px-6 py-12 animate-fade-in-up">

          <div className="flex items-baseline justify-between mb-10">
            <div>
              <h2 className="text-4xl font-bold text-white tracking-tight">{companyData.name} <span className="text-slate-500 font-medium ml-2">({companyData.ticker})</span></h2>
              <p className="text-indigo-300 mt-2 font-medium">{companyData.sector} • {companyData.industry}</p>
            </div>
            <div className="text-right">
              <p className="text-4xl font-bold tabular-nums text-white">${companyData.current_price?.toFixed(2)}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

            {/* LEFT COLUMN: Chart & Stats */}
            <div className="lg:col-span-2 space-y-8">

              {/* Chart Panel */}
              <div className="glass-panel p-6 h-[400px]">
                <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                  <Database className="w-5 h-5 text-indigo-400" />
                  5-Year Price History
                </h3>
                {companyData.price_history?.length > 0 ? (
                  <ResponsiveContainer width="100%" height="90%">
                    <LineChart data={companyData.price_history} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2e334d" vertical={false} />
                      <XAxis dataKey="date" stroke="#64748b" tick={{ fill: '#64748b', fontSize: 12 }} minTickGap={50} />
                      <YAxis stroke="#64748b" tick={{ fill: '#64748b', fontSize: 12 }} domain={['auto', 'auto']} tickFormatter={(v) => `$${v}`} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1e2235', border: '1px solid #333a52', borderRadius: '8px', color: '#fff' }}
                        itemStyle={{ color: '#8b5cf6', fontWeight: 'bold' }}
                      />
                      <Line type="monotone" dataKey="price" stroke="#8b5cf6" strokeWidth={2} dot={false} activeDot={{ r: 6, fill: '#8b5cf6', stroke: '#1e2235', strokeWidth: 2 }} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500">No price history available</div>
                )}
              </div>

              {/* Ratios Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  { label: "Market Cap", value: formatCurrency(companyData.market_cap) },
                  { label: "P/E (TTM)", value: companyData.ratios?.trailingPE?.toFixed(2) || 'N/A' },
                  { label: "EV/EBITDA", value: companyData.ratios?.enterpriseToEbitda?.toFixed(2) || 'N/A' },
                  { label: "Price / Book", value: companyData.ratios?.priceToBook?.toFixed(2) || 'N/A' },
                  { label: "Net Margin", value: formatPct(companyData.ratios?.profitMargins) },
                  { label: "Oper. Margin", value: formatPct(companyData.ratios?.operatingMargins) },
                  { label: "ROE", value: formatPct(companyData.ratios?.returnOnEquity) },
                  { label: "Rev Growth", value: formatPct(companyData.ratios?.revenueGrowth) },
                ].map((stat, i) => (
                  <div key={i} className="glass-panel p-4 flex flex-col justify-center">
                    <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">{stat.label}</p>
                    <p className="text-xl font-bold text-slate-100">{stat.value}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* RIGHT COLUMN: AI Report */}
            <div className="lg:col-span-1 border border-white/10 bg-black/40 backdrop-blur-md rounded-2xl overflow-hidden flex flex-col h-[650px]">
              <div className="border-b border-white/10 bg-[#131620] p-4 flex items-center justify-between sticky top-0 z-10">
                <h3 className="font-semibold flex items-center gap-2">
                  <FileText className="w-5 h-5 text-indigo-400" />
                  AI Equity Report
                </h3>
                {loadingReport && (
                  <span className="flex items-center gap-2 text-xs font-medium text-indigo-400 bg-indigo-500/10 px-3 py-1 rounded-full animate-pulse border border-indigo-400/20">
                    <Loader2 className="w-3 h-3 animate-spin" /> Orchestrating Crew...
                  </span>
                )}
              </div>

              <div className="p-6 overflow-y-auto custom-scrollbar flex-1 relative">
                {report ? (
                  <div className="prose prose-invert prose-indigo max-w-none text-sm leading-relaxed
                                  prose-headings:font-bold prose-headings:tracking-tight
                                  prose-h1:text-2xl prose-h2:text-lg prose-h2:text-indigo-300 prose-h2:mt-8 prose-h2:mb-4
                                  prose-p:text-slate-300 prose-li:text-slate-300
                                  prose-hr:border-white/10">
                    <ReactMarkdown>{report}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center opacity-50 space-y-6">
                    <div className="relative">
                      <Loader2 className="w-12 h-12 text-indigo-500 animate-spin" />
                      <div className="absolute inset-0 bg-indigo-500 blur-xl opacity-20 rounded-full animate-pulse"></div>
                    </div>
                    <div className="space-y-2">
                      <p className="text-lg font-medium text-slate-200">Agents analyzing data...</p>
                      <p className="text-sm text-slate-400 max-w-[200px]">This usually takes 1-2 minutes depending on API response times.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

          </div>
        </main>
      )}
    </div>
  );
}

export default App;
