import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import ReactMarkdown from 'react-markdown';
import { Search, ShieldAlert } from 'lucide-react';
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
      if (!res.ok) throw new Error('Company not found. Please verify the ticker.');
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
      if (!res.ok) throw new Error('Failed to generate report.');
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

    await fetchCompanyData(symbol);
    setLoadingInitial(false);

    if (!error) {
      fetchResearchReport(symbol);
    }
  };

  const formatCurrency = (val) => {
    if (!val) return '—';
    if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
    if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
    if (val >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
    return `$${val.toFixed(2)}`;
  };

  const formatPct = (val) => {
    if (val === undefined || val === null) return '—';
    return `${(val * 100).toFixed(2)}%`;
  };

  return (
    <div className="min-h-screen bg-altruistGray-50 text-altruistGray-900 font-sans flex flex-col">
      {/* GLOBAL HEADER */}
      <header className="border-b border-altruistGray-200 bg-altruistWhite px-8 h-16 sticky top-0 z-50 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-6">
          <h1 className="text-xl font-bold tracking-tight text-altruistDark">KerenEye</h1>
        </div>

        <form onSubmit={handleSearch} className="flex items-center">
          <div className="relative flex items-center">
            <Search className="w-5 h-5 text-altruistGray-400 absolute left-3" />
            <input
              type="text"
              placeholder="Search ticker"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              disabled={loadingInitial}
              className="bg-altruistGray-50 border border-altruistGray-200 rounded-sm pl-10 pr-4 py-2 text-[14px] font-medium uppercase text-altruistDark placeholder-altruistGray-400 focus:outline-none focus:border-altruistBlue focus:bg-altruistWhite transition-colors w-64 disabled:opacity-50"
            />
          </div>
        </form>
      </header>

      {/* ERROR FEEDBACK */}
      {error && (
        <div className="w-full bg-red-50 border-b border-red-200 py-3 px-8 flex items-center gap-3 text-red-700 text-[13px] font-medium">
          <ShieldAlert className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* MAIN LAYOUT */}
      <main className="flex-1 w-full max-w-[1600px] mx-auto p-8">
        {!companyData && !loadingInitial ? (
          // LANDING STATE
          <div className="h-[60vh] flex flex-col items-center justify-center animate-fade-in-up text-center">
            <h2 className="text-4xl font-semibold tracking-tight text-altruistDark mb-4">Advisory Intelligence.</h2>
            <p className="text-altruistGray-500 text-[16px] leading-relaxed max-w-md">
              Enter a ticker symbol to access high-fidelity institutional data and AI-generated equity research reports.
            </p>
          </div>
        ) : (
          // DASHBOARD GRID
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 animate-fade-in-up items-start">

            {/* LEFT COLUMN: Data & Stats (7 cols) */}
            <div className="xl:col-span-7 flex flex-col gap-6">

              {/* HEADER INFO */}
              <div className="flex justify-between items-end mb-2">
                {loadingInitial ? (
                  <div className="space-y-2">
                    <div className="skeleton h-10 w-64 rounded-sm" />
                    <div className="skeleton h-4 w-48 rounded-sm" />
                  </div>
                ) : (
                  <div>
                    <h2 className="text-[32px] leading-tight font-semibold text-altruistDark tracking-tight mb-1">{companyData.name} <span className="text-altruistGray-400 font-mono text-[24px] ml-2">{companyData.ticker}</span></h2>
                    <p className="text-[14px] text-altruistGray-500 font-medium">{companyData.sector} &mdash; {companyData.industry}</p>
                  </div>
                )}
                {loadingInitial ? (
                  <div className="skeleton h-12 w-32 rounded-sm" />
                ) : (
                  <div className="text-right">
                    <p className="text-[40px] leading-tight font-mono font-medium text-altruistDark tabular-nums">${companyData.current_price?.toFixed(2)}</p>
                  </div>
                )}
              </div>

              {/* CHART FOCUS PANEL */}
              <div className="panel-structured h-[480px] flex flex-col">
                <div className="border-b border-altruistGray-200 px-6 py-4 bg-altruistWhite">
                  <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide">5-Year Equity Performance</h3>
                </div>
                <div className="flex-1 min-h-0 p-6 pt-8">
                  {loadingInitial ? (
                    <div className="skeleton h-full w-full rounded-sm" />
                  ) : companyData.price_history && companyData.price_history.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={companyData.price_history} margin={{ top: 5, right: 0, bottom: 0, left: -20 }}>
                        <XAxis dataKey="date" hide={true} />
                        <YAxis hide={true} domain={['auto', 'auto']} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #E5E7EB', borderRadius: '4px', color: '#111827', fontFamily: 'monospace', fontSize: '13px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                          itemStyle={{ color: '#1565C0', fontWeight: '600' }}
                          formatter={(value) => [`$${value.toFixed(2)}`, "Price"]}
                          labelStyle={{ color: '#6B7280', marginBottom: '4px' }}
                        />
                        <Line type="monotone" dataKey="price" stroke="#1565C0" strokeWidth={3} dot={false} activeDot={{ r: 5, fill: '#1565C0', stroke: '#ffffff', strokeWidth: 2 }} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-altruistGray-400 font-mono text-sm uppercase">Data Unavailable</div>
                  )}
                </div>
              </div>

              {/* STATS DOSSIER */}
              <div className="panel-structured overflow-hidden">
                <div className="border-b border-altruistGray-200 px-6 py-4 bg-altruistGray-50">
                  <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide">Fundamental Metrics</h3>
                </div>
                <div className="p-0">
                  {loadingInitial ? (
                    <div className="grid grid-cols-2">
                      {[...Array(8)].map((_, i) => (
                        <div key={i} className="flex justify-between px-6 py-4 border-b border-altruistGray-200 even:border-l">
                          <div className="skeleton h-4 w-24 rounded-sm" />
                          <div className="skeleton h-4 w-16 rounded-sm" />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2">
                      {[
                        { label: "Market Cap", value: formatCurrency(companyData.market_cap) },
                        { label: "P/E (TTM)", value: companyData.ratios?.trailingPE?.toFixed(2) || '—' },
                        { label: "EV/EBITDA", value: companyData.ratios?.enterpriseToEbitda?.toFixed(2) || '—' },
                        { label: "Price / Book", value: companyData.ratios?.priceToBook?.toFixed(2) || '—' },
                        { label: "Net Margin", value: formatPct(companyData.ratios?.profitMargins) },
                        { label: "Operating Margin", value: formatPct(companyData.ratios?.operatingMargins) },
                        { label: "Return on Equity", value: formatPct(companyData.ratios?.returnOnEquity) },
                        { label: "Revenue Growth", value: formatPct(companyData.ratios?.revenueGrowth) },
                      ].map((stat, i) => (
                        <div key={i} className="flex flex-col px-6 py-4 border-b border-altruistGray-200 sm:even:border-l hover:bg-altruistGray-50 transition-colors">
                          <span className="text-altruistGray-500 text-[12px] font-bold uppercase tracking-wide mb-1">{stat.label}</span>
                          <span className="font-mono text-altruistDark font-medium tabular-nums text-[16px]">{stat.value}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* RIGHT COLUMN: AI Report (5 cols) */}
            <div className="xl:col-span-5 relative">
              <div className="panel-structured h-full xl:h-[calc(100vh-8rem)] flex flex-col overflow-hidden xl:sticky xl:top-24 bg-altruistWhite">
                <div className="border-b border-altruistGray-200 px-6 py-4 flex justify-between items-center bg-altruistGray-50 z-10">
                  <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide">Executive Dossier</h3>
                  {loadingReport && (
                    <span className="text-altruistBlue text-[12px] font-medium flex items-center gap-2">
                      <div className="w-2 h-2 bg-altruistBlue animate-pulse rounded-full" />
                      Generating Analysis...
                    </span>
                  )}
                </div>

                <div className="p-8 overflow-y-auto custom-scrollbar flex-1">
                  {report ? (
                    <div className="prose prose-slate max-w-none text-[15px] leading-relaxed
                                    prose-headings:font-bold prose-headings:tracking-tight
                                    prose-h1:text-[22px] prose-h2:text-[18px] prose-h2:text-altruistDark prose-h2:mt-8 prose-h2:mb-4 prose-h2:pb-2 prose-h2:border-b prose-h2:border-altruistGray-200
                                    prose-p:text-altruistGray-800 prose-li:text-altruistGray-800
                                    prose-hr:border-altruistGray-200 prose-a:text-altruistBlue">
                      <ReactMarkdown>{report}</ReactMarkdown>
                    </div>
                  ) : loadingReport || loadingInitial ? (
                    <div className="w-full space-y-8">
                      <div className="skeleton h-8 w-3/4 rounded-sm" />
                      <div className="space-y-3">
                        <div className="skeleton h-4 w-full rounded-sm" />
                        <div className="skeleton h-4 w-full rounded-sm" />
                        <div className="skeleton h-4 w-5/6 rounded-sm" />
                      </div>
                      <div className="skeleton h-6 w-1/2 rounded-sm mt-10" />
                      <div className="space-y-3">
                        <div className="skeleton h-4 w-full rounded-sm" />
                        <div className="skeleton h-4 w-11/12 rounded-sm" />
                        <div className="skeleton h-4 w-full rounded-sm" />
                      </div>
                    </div>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-altruistGray-400">
                      <p className="text-[13px] font-medium uppercase tracking-widest text-center">Analysis pending<br />Search a ticker to synthesize report</p>
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
