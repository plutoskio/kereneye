import React, { useState } from 'react';
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

    // 1. Fetch fast initial data to draw the precision grid
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
    <div className="min-h-screen bg-obsidian text-neutral-300 font-sans flex flex-col">
      {/* GLOBAL HEADER */}
      <header className="border-b border-borderline bg-obsidian py-4 px-8 sticky top-0 z-50 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-medium tracking-[0.01em] text-neutral-100">KERENEYE</h1>
          <div className="h-4 w-px bg-borderline hidden sm:block" />
          <span className="text-xs text-neutral-500 uppercase tracking-[0.02em] hidden sm:block">Institutional Terminal</span>
        </div>

        <form onSubmit={handleSearch} className="flex items-center">
          <input
            type="text"
            placeholder="TICKER"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            disabled={loadingInitial}
            className="bg-transparent border border-borderline rounded-precision px-3 py-1.5 text-sm font-mono uppercase text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-institutional transition-colors w-32 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loadingInitial || !ticker.trim()}
            className="ml-2 px-4 py-1.5 bg-institutional hover:bg-blue-700 text-white rounded-precision text-xs font-medium uppercase tracking-[0.02em] transition-colors disabled:opacity-50"
          >
            {loadingInitial ? '...' : 'RUN'}
          </button>
        </form>
      </header>

      {/* ERROR FEEDBACK */}
      {error && (
        <div className="w-full bg-red-900/20 border-b border-red-900/50 py-2 px-8 text-red-500 text-[13px] font-mono tracking-wide">
          ERROR SYSTEM: {error.toUpperCase()}
        </div>
      )}

      {/* MAIN LAYOUT */}
      <main className="flex-1 w-full p-8 max-w-[1600px] mx-auto">
        {!companyData && !loadingInitial ? (
          // LANDING STATE
          <div className="h-full flex flex-col items-center justify-center pt-32 animate-fade-in-up">
            <h2 className="text-4xl font-medium tracking-[0.01em] text-neutral-200 mb-4">Precision Intelligence</h2>
            <p className="text-neutral-500 text-[15px] leading-relaxed max-w-lg text-center">
              Initiate a search sequence via the command bar above to render high-fidelity market data and deterministic agentic research.
            </p>
          </div>
        ) : (
          // 12-COLUMN DASHBOARD GRID
          <div className="grid grid-cols-12 gap-8 animate-fade-in-up">

            {/* LEFT COLUMN: Data & Stats (8 cols) */}
            <div className="col-span-12 lg:col-span-8 flex flex-col gap-8">

              {/* CHART PANEL */}
              <div className="panel p-8 h-[500px] flex flex-col">
                <div className="flex justify-between items-end mb-8">
                  {loadingInitial ? (
                    <div className="space-y-2">
                      <div className="skeleton h-8 w-48 rounded-precision" />
                      <div className="skeleton h-4 w-32 rounded-precision" />
                    </div>
                  ) : (
                    <div>
                      <h2 className="text-3xl font-medium text-neutral-100 mb-1 tracking-[0.01em]">{companyData.name} <span className="text-neutral-500 text-xl font-mono ml-3">{companyData.ticker}</span></h2>
                      <p className="text-sm text-neutral-500">{companyData.sector} &mdash; {companyData.industry}</p>
                    </div>
                  )}
                  {loadingInitial ? (
                    <div className="skeleton h-10 w-32 rounded-precision" />
                  ) : (
                    <div className="text-right">
                      <p className="text-4xl font-mono text-neutral-100 tabular-nums">${companyData.current_price?.toFixed(2)}</p>
                    </div>
                  )}
                </div>

                <div className="flex-1 min-h-0">
                  {loadingInitial ? (
                    <div className="skeleton h-full w-full rounded-precision" />
                  ) : companyData.price_history && companyData.price_history.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={companyData.price_history} margin={{ top: 5, right: 0, bottom: 0, left: -20 }}>
                        <CartesianGrid strokeDasharray="0" stroke="#171717" vertical={false} />
                        <XAxis dataKey="date" stroke="#525252" tick={{ fill: '#737373', fontSize: 11, fontFamily: 'monospace' }} minTickGap={50} axisLine={false} tickLine={false} />
                        <YAxis stroke="#525252" tick={{ fill: '#737373', fontSize: 11, fontFamily: 'monospace' }} domain={['auto', 'auto']} tickFormatter={(v) => `$${v}`} axisLine={false} tickLine={false} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#0a0a0a', border: '1px solid #262626', borderRadius: '6px', color: '#f5f5f5', fontFamily: 'monospace', fontSize: '12px' }}
                          itemStyle={{ color: '#2563EB', fontWeight: '500' }}
                          formatter={(value) => [`$${value.toFixed(2)}`, "Price"]}
                        />
                        <Line type="monotone" dataKey="price" stroke="#2563EB" strokeWidth={1.5} dot={false} activeDot={{ r: 4, fill: '#2563EB', stroke: '#0a0a0a', strokeWidth: 2 }} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-neutral-600 font-mono text-xs uppercase">No Chart Data</div>
                  )}
                </div>
              </div>

              {/* STATS TABLE */}
              <div className="panel p-8">
                <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-[0.02em] mb-6">Key Metrics</h3>
                {loadingInitial ? (
                  <div className="grid grid-cols-2 gap-x-8 gap-y-4">
                    {[...Array(8)].map((_, i) => (
                      <div key={i} className="flex justify-between py-3 border-b border-borderline">
                        <div className="skeleton h-4 w-24 rounded-precision" />
                        <div className="skeleton h-4 w-16 rounded-precision" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-12 gap-y-1">
                    {[
                      { label: "Market Cap", value: formatCurrency(companyData.market_cap) },
                      { label: "P/E (TTM)", value: companyData.ratios?.trailingPE?.toFixed(2) || 'N/A' },
                      { label: "EV/EBITDA", value: companyData.ratios?.enterpriseToEbitda?.toFixed(2) || 'N/A' },
                      { label: "Price / Book", value: companyData.ratios?.priceToBook?.toFixed(2) || 'N/A' },
                      { label: "Net Margin", value: formatPct(companyData.ratios?.profitMargins) },
                      { label: "Operating Margin", value: formatPct(companyData.ratios?.operatingMargins) },
                      { label: "Return on Equity", value: formatPct(companyData.ratios?.returnOnEquity) },
                      { label: "Revenue Growth", value: formatPct(companyData.ratios?.revenueGrowth) },
                    ].map((stat, i) => (
                      <div key={i} className="flex justify-between items-center py-3 border-b border-borderline last:border-0 hover:bg-rowhover transition-colors px-2 -mx-2 rounded-precision cursor-default">
                        <span className="text-neutral-400 text-[14px]">{stat.label}</span>
                        <span className="font-mono text-neutral-200 tabular-nums text-[14px]">{stat.value}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* RIGHT COLUMN: AI Report (4 cols) */}
            <div className="col-span-12 lg:col-span-4">
              <div className="panel h-[calc(100vh-8rem)] flex flex-col overflow-hidden sticky top-24">
                <div className="border-b border-borderline p-6 flex justify-between items-center bg-obsidian z-10">
                  <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-[0.02em]">Intelligence Report</h3>
                  {loadingReport && (
                    <span className="text-institutional text-[11px] lowercase flex items-center gap-2 font-mono tracking-tight">
                      <div className="w-1.5 h-1.5 bg-institutional animate-pulse rounded-full" />
                      synthesizing
                    </span>
                  )}
                </div>

                <div className="p-8 overflow-y-auto custom-scrollbar flex-1">
                  {report ? (
                    <div className="prose prose-invert prose-neutral max-w-none text-[15px] leading-relaxed
                                    prose-headings:font-medium prose-headings:tracking-[0.01em]
                                    prose-h1:text-2xl prose-h2:text-lg prose-h2:text-neutral-200 prose-h2:mt-10 prose-h2:mb-4
                                    prose-p:text-neutral-400 prose-li:text-neutral-400
                                    prose-hr:border-borderline prose-a:text-institutional">
                      <ReactMarkdown>{report}</ReactMarkdown>
                    </div>
                  ) : loadingReport || loadingInitial ? (
                    <div className="w-full space-y-8">
                      <div className="skeleton h-8 w-3/4 rounded-precision" />
                      <div className="space-y-3">
                        <div className="skeleton h-4 w-full rounded-precision" />
                        <div className="skeleton h-4 w-full rounded-precision" />
                        <div className="skeleton h-4 w-5/6 rounded-precision" />
                      </div>
                      <div className="skeleton h-6 w-1/2 rounded-precision mt-10" />
                      <div className="space-y-3">
                        <div className="skeleton h-4 w-full rounded-precision" />
                        <div className="skeleton h-4 w-11/12 rounded-precision" />
                        <div className="skeleton h-4 w-full rounded-precision" />
                      </div>
                    </div>
                  ) : (
                    <div className="h-full flex items-center justify-center text-neutral-600 text-[11px] font-mono uppercase text-center tracking-widest">
                      Analysis sequence pending
                    </div>
                  )}
                </div>
              </div>
            </div>

          </div>
        )}
      </main>
    </div>
  );
}

export default App;
