import React, { useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import ReactMarkdown from 'react-markdown';
import { Search, TrendingUp, Sparkles, AlertCircle } from 'lucide-react';
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
      if (!res.ok) throw new Error("We couldn't find that company. Please check the ticker symbol.");
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
      if (!res.ok) throw new Error("We ran into an issue generating your report.");
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

    // Fetch fast structural data
    await fetchCompanyData(symbol);
    setLoadingInitial(false);

    // Trigger AI writing
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
    return `${(val * 100).toFixed(1)}%`;
  };

  return (
    <div className="min-h-screen flex flex-col selection:bg-primary-100 selection:text-primary-700">

      {/* NAVIGATION BAR (Active State) */}
      <header className={`transition-all duration-700 ease-in-out w-full
        ${companyData ? 'nav-blur sticky top-0 z-50 py-4 px-6 sm:px-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4' :
          'pt-32 pb-12 px-6 flex flex-col items-center justify-center'}`}>

        <div className={`flex items-center gap-3 ${!companyData && 'mb-8'}`}>
          <div className="w-10 h-10 bg-primary-100 text-primary-600 rounded-xl flex items-center justify-center shadow-sm">
            <TrendingUp strokeWidth={2.5} className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-text-main">KerenEye</h1>
        </div>

        {!companyData && (
          <div className="text-center max-w-xl mx-auto mb-10 space-y-3">
            <h2 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-text-main">Understand any stock,<br />instantly.</h2>
            <p className="text-lg text-text-muted">Enter a ticker symbol below and let our AI agents write a comprehensive, easy-to-read financial research report just for you.</p>
          </div>
        )}

        <form onSubmit={handleSearch} className={`relative group ${companyData ? 'w-full sm:w-96' : 'w-full max-w-lg mx-auto'}`}>
          <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
            <Search className="w-5 h-5 text-text-soft" />
          </div>
          <input
            type="text"
            placeholder="Search Apple, Tesla, etc. (AAPL, TSLA)"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            disabled={loadingInitial}
            className={`w-full bg-surface border border-borderline/80 focus:border-primary-500 focus:ring-4 focus:ring-primary-500/10 rounded-full pl-12 pr-24 py-3 sm:py-4 text-text-main placeholder:text-text-soft outline-none transition-all shadow-sm ${loadingInitial && 'opacity-70'}`}
          />
          <button
            type="submit"
            disabled={loadingInitial || !ticker.trim()}
            className="absolute right-2 top-2 bottom-2 bg-primary-600 hover:bg-primary-700 text-white px-5 rounded-full font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm text-sm"
          >
            {loadingInitial ? 'Searching...' : 'Analyze'}
          </button>
        </form>
      </header>

      {/* ERROR FEEDBACK */}
      {error && !companyData && (
        <div className="max-w-lg mx-auto mt-6 flex items-center gap-3 text-red-600 bg-red-50 px-5 py-4 rounded-friendly border border-red-100">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p className="font-medium text-sm">{error}</p>
        </div>
      )}

      {/* MAIN LAYOUT */}
      <main className="flex-1 w-full p-4 sm:p-8 max-w-[1400px] mx-auto">
        {companyData && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 animate-fade-in-up">

            {/* LEFT COLUMN: Data & Stats (7 cols) */}
            <div className="col-span-1 lg:col-span-7 flex flex-col gap-6 sm:gap-8">

              {/* Header Card */}
              <div className="card p-6 sm:p-8">
                <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h2 className="text-3xl sm:text-4xl font-bold text-text-main tracking-tight">{companyData.name}</h2>
                      <span className="bg-gray-100 text-gray-600 px-3 py-1 rounded-full text-sm font-semibold tracking-wide">{companyData.ticker}</span>
                    </div>
                    <p className="text-text-muted font-medium">{companyData.sector} • {companyData.industry}</p>
                  </div>
                  <div className="sm:text-right">
                    <p className="text-4xl sm:text-5xl font-bold text-text-main tracking-tight">${companyData.current_price?.toFixed(2)}</p>
                    <p className="text-text-muted mt-1 font-medium">Current Price</p>
                  </div>
                </div>
              </div>

              {/* Chart Panel */}
              <div className="card p-6 sm:p-8 h-[400px] flex flex-col">
                <h3 className="text-lg font-bold text-text-main mb-6">5-Year Performance</h3>
                <div className="flex-1 min-h-0 -ml-4 -mr-4 sm:-mr-8">
                  {companyData.price_history && companyData.price_history.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={companyData.price_history} margin={{ top: 10, right: 0, bottom: 0, left: 0 }}>
                        <defs>
                          <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="date" hide={true} />
                        <YAxis domain={['auto', 'auto']} hide={true} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#ffffff', border: 'none', borderRadius: '12px', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)', color: '#1F2937', fontWeight: '600' }}
                          itemStyle={{ color: '#2563EB', fontWeight: '700' }}
                          formatter={(value) => [`$${value.toFixed(2)}`, "Price"]}
                          labelStyle={{ color: '#6B7280', marginBottom: '4px', fontSize: '12px', fontWeight: '500' }}
                        />
                        <Area type="monotone" dataKey="price" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorPrice)" activeDot={{ r: 6, fill: '#ffffff', stroke: '#3b82f6', strokeWidth: 3 }} />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-text-muted font-medium bg-gray-50 rounded-2xl mx-4 sm:mx-8">No performance data available</div>
                  )}
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  { label: "Market Cap", value: formatCurrency(companyData.market_cap) },
                  { label: "P/E Ratio", value: companyData.ratios?.trailingPE?.toFixed(2) || '—' },
                  { label: "EV / EBITDA", value: companyData.ratios?.enterpriseToEbitda?.toFixed(2) || '—' },
                  { label: "Price / Book", value: companyData.ratios?.priceToBook?.toFixed(2) || '—' },
                  { label: "Net Margin", value: formatPct(companyData.ratios?.profitMargins) },
                  { label: "Operating Margin", value: formatPct(companyData.ratios?.operatingMargins) },
                  { label: "Return on Equity", value: formatPct(companyData.ratios?.returnOnEquity) },
                  { label: "Rev Growth", value: formatPct(companyData.ratios?.revenueGrowth) },
                ].map((stat, i) => (
                  <div key={i} className="card p-5 flex flex-col justify-center">
                    <p className="text-text-muted text-sm font-medium mb-1">{stat.label}</p>
                    <p className="text-xl sm:text-2xl font-bold text-text-main">{stat.value}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* RIGHT COLUMN: AI Report (5 cols) */}
            <div className="col-span-1 lg:col-span-5 relative">
              <div className="card h-full lg:h-[calc(100vh-8rem)] flex flex-col overflow-hidden lg:sticky lg:top-24">
                <div className="border-b border-borderline/60 p-6 flex flex-col sm:flex-row gap-4 sm:gap-0 justify-between sm:items-center bg-surface z-10">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-primary-500" />
                    <h3 className="text-lg font-bold text-text-main">AI Financial Insights</h3>
                  </div>
                  {loadingReport && (
                    <span className="text-primary-600 bg-primary-50 text-xs font-semibold px-3 py-1.5 rounded-full flex items-center gap-2 w-fit">
                      <div className="w-1.5 h-1.5 bg-primary-500 animate-pulse rounded-full" />
                      Analyzing data...
                    </span>
                  )}
                </div>

                <div className="p-6 sm:p-8 overflow-y-auto custom-scrollbar flex-1 bg-gray-50/30">
                  {report ? (
                    <div className="prose prose-slate max-w-none text-[15px] sm:text-[16px]">
                      <ReactMarkdown>{report}</ReactMarkdown>
                    </div>
                  ) : loadingReport ? (
                    <div className="w-full space-y-8 py-4">
                      <div className="pulse-soft h-8 w-3/4" />
                      <div className="space-y-3">
                        <div className="pulse-soft h-4 w-full" />
                        <div className="pulse-soft h-4 w-full" />
                        <div className="pulse-soft h-4 w-5/6" />
                      </div>
                      <div className="pulse-soft h-6 w-1/2 mt-10" />
                      <div className="space-y-3">
                        <div className="pulse-soft h-4 w-full" />
                        <div className="pulse-soft h-4 w-11/12" />
                        <div className="pulse-soft h-4 w-full" />
                      </div>
                    </div>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center space-y-4 py-12">
                      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-2">
                        <Sparkles className="w-8 h-8 text-gray-400" />
                      </div>
                      <p className="text-lg font-semibold text-text-main">Ready to analyze.</p>
                      <p className="text-text-muted max-w-xs mx-auto">Our AI agents read balance sheets, recent news, and technicals to write a friendly, comprehensive report.</p>
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
