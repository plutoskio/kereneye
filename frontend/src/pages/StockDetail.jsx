import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import ReactMarkdown from 'react-markdown';
import {
  ArrowLeft, Search, ShieldAlert, TrendingUp, TrendingDown, Newspaper, Activity,
  Database, DollarSign, Scale, Users, Target, FileText, CheckCircle2, Loader2, RefreshCw, LayoutDashboard
} from 'lucide-react';

const API = 'http://localhost:8000';

const REPORT_STEPS = [
  { id: "Collecting Data", label: "Data Collection", icon: Database },
  { id: "Analyzing Financials & Margins", label: "Financial Analysis", icon: DollarSign },
  { id: "Running Valuation Models", label: "Valuation Modeling", icon: Scale },
  { id: "Assessing Market Sentiment", label: "Market Sentiment", icon: Users },
  { id: "Evaluating Technical Action", label: "Technical Analysis", icon: Activity },
  { id: "Scanning for Industry Threats", label: "Industry Threats", icon: Target },
  { id: "Drafting Executive Report", label: "Report Generation", icon: FileText },
];

const getStepState = (index, status) => {
  if (!status) return { isCompleted: false, isActive: index === 0, isPending: index > 0 };
  if (status === "Complete" || status === "Finalizing") return { isCompleted: true, isActive: false, isPending: false };

  if (status === "Collecting Data") {
    return { isCompleted: false, isActive: index === 0, isPending: index > 0 };
  }
  if (status.startsWith("Concurrent Analysis")) {
    if (index === 0) return { isCompleted: true, isActive: false, isPending: false };
    if (index >= 1 && index <= 5) return { isCompleted: false, isActive: true, isPending: false };
    return { isCompleted: false, isActive: false, isPending: true };
  }
  if (status === "Drafting Executive Report") {
    if (index <= 5) return { isCompleted: true, isActive: false, isPending: false };
    if (index === 6) return { isCompleted: false, isActive: true, isPending: false };
  }
  return { isCompleted: false, isActive: false, isPending: true };
};

export default function StockDetail() {
  const { ticker: routeTicker } = useParams();
  const navigate = useNavigate();

  const [companyData, setCompanyData] = useState(null);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [error, setError] = useState(null);

  const [report, setReport] = useState(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [reportStatus, setReportStatus] = useState('');

  const [newsAnalysis, setNewsAnalysis] = useState(null);
  const [loadingNews, setLoadingNews] = useState(false);
  const [newsStatus, setNewsStatus] = useState('');
  const [newsCacheAge, setNewsCacheAge] = useState(0);

  // ---------------------------------------------------------------
  // Fetch data on mount
  // ---------------------------------------------------------------
  useEffect(() => {
    if (routeTicker) {
      fetchCompanyData(routeTicker.toUpperCase());
    }
  }, [routeTicker]);

  // Report status polling
  useEffect(() => {
    let intervalId;
    if (loadingReport && companyData?.ticker) {
      const poll = async () => {
        try {
          const res = await fetch(`${API}/api/research/status/${companyData.ticker}`);
          if (res.ok) {
            const data = await res.json();
            setReportStatus(data.status);
          }
        } catch (err) { /* ignore */ }
      };
      poll();
      intervalId = setInterval(poll, 1000);
    } else if (!loadingReport) {
      setReportStatus('');
    }
    return () => clearInterval(intervalId);
  }, [loadingReport, companyData]);

  // News status polling
  useEffect(() => {
    let intervalId;
    if (loadingNews && companyData?.ticker) {
      const poll = async () => {
        try {
          const res = await fetch(`${API}/api/news_analysis/status/${companyData.ticker}`);
          if (res.ok) {
            const data = await res.json();
            setNewsStatus(data.status);
          }
        } catch (err) { /* ignore */ }
      };
      poll();
      intervalId = setInterval(poll, 1000);
    } else if (!loadingNews) {
      setNewsStatus('');
    }
    return () => clearInterval(intervalId);
  }, [loadingNews, companyData]);

  // ---------------------------------------------------------------
  // API calls
  // ---------------------------------------------------------------
  const fetchCompanyData = async (symbol) => {
    try {
      setLoadingInitial(true);
      setError(null);
      const res = await fetch(`${API}/api/company/${symbol}`);
      if (!res.ok) throw new Error('Company not found.');
      const data = await res.json();
      setCompanyData(data);
      // Also check caches
      fetchResearchCache(symbol);
      fetchNewsCache(symbol);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingInitial(false);
    }
  };

  const fetchResearchCache = async (symbol) => {
    try {
      const res = await fetch(`${API}/api/research/${symbol}`);
      if (res.ok) {
        const data = await res.json();
        setReport(data.report);
      }
    } catch (err) { console.error(err); }
  };

  const fetchNewsCache = async (symbol) => {
    try {
      const res = await fetch(`${API}/api/news_analysis/${symbol}`);
      if (res.ok) {
        const data = await res.json();
        setNewsAnalysis(data.news_analysis);
        setNewsCacheAge(data.age_days || 0);
      }
    } catch (err) { console.error(err); }
  };

  const generateReport = async (symbol) => {
    try {
      setLoadingReport(true);
      const res = await fetch(`${API}/api/research/${symbol}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to generate report.');
      const data = await res.json();
      setReport(data.report);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingReport(false);
    }
  };

  const generateNewsAnalysis = async (symbol) => {
    try {
      setLoadingNews(true);
      const res = await fetch(`${API}/api/news_analysis/${symbol}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to generate news analysis.');
      const data = await res.json();
      setNewsAnalysis(data.news_analysis);
      setNewsCacheAge(0);
    } catch (err) {
      setNewsAnalysis('Failed to load news analysis.');
    } finally {
      setLoadingNews(false);
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

  // ---------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------
  return (
    <div className="animate-fade-in-up">
      {/* BACK BUTTON */}
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-2 text-[12px] font-bold text-altruistGray-500 uppercase tracking-widest hover:text-altruistDark transition-colors mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Portfolio
      </button>

      {error && (
        <div className="w-full bg-red-50 border border-red-200 rounded-sm py-3 px-6 flex items-center gap-3 text-red-700 text-[13px] font-medium mb-6">
          <ShieldAlert className="w-4 h-4" />
          {error}
        </div>
      )}

      {loadingInitial ? (
        <div className="space-y-6">
          <div className="flex justify-between items-end mb-2">
            <div className="space-y-2">
              <div className="skeleton h-10 w-64 rounded-sm" />
              <div className="skeleton h-4 w-48 rounded-sm" />
            </div>
            <div className="skeleton h-12 w-32 rounded-sm" />
          </div>
          <div className="panel-structured h-[480px]">
            <div className="skeleton h-full w-full rounded-sm" />
          </div>
        </div>
      ) : companyData ? (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
          {/* LEFT: Data & Charts */}
          <div className="xl:col-span-7 flex flex-col gap-6">
            {/* Header */}
            <div className="flex justify-between items-end mb-2">
              <div>
                <h2 className="text-[32px] leading-tight font-semibold text-altruistDark tracking-tight mb-1">
                  {companyData.name} <span className="text-altruistGray-400 font-mono text-[24px] ml-2">{companyData.ticker}</span>
                </h2>
                <p className="text-[14px] text-altruistGray-500 font-medium">{companyData.sector} &mdash; {companyData.industry}</p>
              </div>
              <div className="text-right">
                <p className="text-[40px] leading-tight font-mono font-medium text-altruistDark tabular-nums">${companyData.current_price?.toFixed(2)}</p>
              </div>
            </div>

            {/* Chart */}
            <div className="panel-structured h-[480px] flex flex-col">
              <div className="border-b border-altruistGray-200 px-6 py-4 bg-altruistWhite">
                <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide">5-Year Equity Performance</h3>
              </div>
              <div className="flex-1 min-h-0 p-6 pt-8">
                {companyData.price_history && companyData.price_history.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={companyData.price_history} margin={{ top: 5, right: 0, bottom: 0, left: -20 }}>
                      <XAxis dataKey="date" hide />
                      <YAxis hide domain={['auto', 'auto']} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #E5E7EB', borderRadius: '4px', color: '#111827', fontFamily: 'monospace', fontSize: '13px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                        formatter={(value) => [`$${value.toFixed(2)}`, 'Price']}
                      />
                      <Line type="monotone" dataKey="price" stroke="#1565C0" strokeWidth={3} dot={false} activeDot={{ r: 5, fill: '#1565C0', stroke: '#fff', strokeWidth: 2 }} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-altruistGray-400 font-mono text-sm uppercase">Data Unavailable</div>
                )}
              </div>
            </div>

            {/* News Analysis */}
            <div className="panel-structured overflow-hidden bg-altruistWhite flex flex-col xl:h-[500px]">
              <div className="border-b border-altruistGray-200 px-6 py-4 flex justify-between items-center bg-altruistGray-50">
                <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide flex items-center gap-2">
                  <Newspaper className="w-4 h-4 text-altruistBlue" /> Recent News Analysis
                </h3>
                <div className="flex items-center gap-4">
                  {newsAnalysis && !loadingNews && (
                    <span className="text-[11px] font-medium text-altruistGray-400 uppercase tracking-widest">
                      {newsCacheAge === 0 ? 'Live' : `${newsCacheAge}d ago`}
                    </span>
                  )}
                  {newsAnalysis && (
                    <button onClick={() => generateNewsAnalysis(companyData.ticker)} disabled={loadingNews} className="text-[11px] font-bold text-altruistBlue uppercase tracking-widest hover:text-blue-800 transition-colors disabled:opacity-50 flex items-center gap-1 bg-altruistBlue/10 px-3 py-1.5 rounded-sm">
                      {loadingNews ? <Loader2 className="w-3 h-3 animate-spin" /> : <Activity className="w-3 h-3" />} Refresh
                    </button>
                  )}
                </div>
              </div>
              <div className="p-6 overflow-y-auto custom-scrollbar flex-1 relative">
                {newsAnalysis ? (
                  <div className="prose prose-sm max-w-none prose-slate prose-headings:font-bold prose-headings:text-altruistDark prose-h3:text-[15px] prose-h3:uppercase prose-h3:mt-0 prose-h3:mb-3 prose-h3:text-altruistBlue prose-p:text-[14px] prose-p:leading-relaxed prose-p:text-altruistGray-800">
                    <ReactMarkdown>{newsAnalysis}</ReactMarkdown>
                  </div>
                ) : loadingNews ? (
                  <div className="h-full flex flex-col items-center justify-center animate-fade-in-up">
                    <div className="w-12 h-12 rounded-full border-2 border-altruistBlue border-t-transparent animate-spin mb-4" />
                    <p className="text-[14px] font-bold text-altruistDark tracking-wide">{newsStatus || 'Synthesizing Premium Coverage'}</p>
                    <p className="text-[12px] text-altruistGray-500 font-medium mt-1">Filtering Benzinga & Polygon signals...</p>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center p-8 bg-altruistGray-50 rounded-sm border border-altruistGray-200">
                    <Newspaper className="w-8 h-8 text-altruistBlue mb-4 opacity-50" />
                    <p className="text-[14px] font-medium text-altruistGray-800 mb-6 text-center">
                      Generate a fresh analysis of the past 7 days of premium news.
                    </p>
                    <button onClick={() => generateNewsAnalysis(companyData.ticker)} className="bg-altruistBlue text-white px-6 py-2.5 rounded-sm text-[13px] font-bold uppercase tracking-wide hover:bg-blue-800 transition-colors flex items-center gap-2">
                      <Activity className="w-4 h-4" /> Generate Weekly News Analysis
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Metrics */}
            <div className="panel-structured overflow-hidden">
              <div className="border-b border-altruistGray-200 px-6 py-4 bg-altruistGray-50">
                <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide">Fundamental Metrics</h3>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2">
                {[
                  { label: 'Market Cap', value: formatCurrency(companyData.market_cap) },
                  { label: 'P/E (TTM)', value: companyData.ratios?.trailingPE?.toFixed(2) || '—' },
                  { label: 'EV/EBITDA', value: companyData.ratios?.enterpriseToEbitda?.toFixed(2) || '—' },
                  { label: 'Price / Book', value: companyData.ratios?.priceToBook?.toFixed(2) || '—' },
                  { label: 'Net Margin', value: formatPct(companyData.ratios?.profitMargins) },
                  { label: 'Operating Margin', value: formatPct(companyData.ratios?.operatingMargins) },
                  { label: 'Return on Equity', value: formatPct(companyData.ratios?.returnOnEquity) },
                  { label: 'Revenue Growth', value: formatPct(companyData.ratios?.revenueGrowth) },
                ].map((stat, i) => (
                  <div key={i} className="flex flex-col px-6 py-4 border-b border-altruistGray-200 sm:even:border-l hover:bg-altruistGray-50 transition-colors">
                    <span className="text-altruistGray-500 text-[12px] font-bold uppercase tracking-wide mb-1">{stat.label}</span>
                    <span className="font-mono text-altruistDark font-medium tabular-nums text-[16px]">{stat.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT: AI Report */}
          <div className="xl:col-span-5 relative">
            <div className="panel-structured h-full xl:h-[calc(100vh-8rem)] flex flex-col overflow-hidden xl:sticky xl:top-24 bg-altruistWhite">
              <div className="border-b border-altruistGray-200 px-6 py-4 flex justify-between items-center bg-altruistGray-50 z-10">
                <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide">Executive Dossier</h3>
                <div className="flex items-center gap-4">
                  {loadingReport && (
                    <span className="text-altruistBlue text-[12px] font-medium flex items-center gap-2">
                      <div className="w-2 h-2 bg-altruistBlue animate-pulse rounded-full" />
                      {reportStatus || 'Initializing...'}
                    </span>
                  )}
                  {report && !loadingReport && (
                    <button onClick={() => generateReport(companyData.ticker)} disabled={loadingReport} className="text-[11px] font-bold text-altruistBlue uppercase tracking-widest hover:text-blue-800 disabled:opacity-50 flex items-center gap-1 bg-altruistBlue/10 px-3 py-1.5 rounded-sm">
                      <RefreshCw className="w-3 h-3" /> Refresh
                    </button>
                  )}
                </div>
              </div>
              <div className="p-8 overflow-y-auto custom-scrollbar flex-1">
                {report ? (
                  <div className="prose prose-slate max-w-none text-[15px] leading-relaxed prose-headings:font-bold prose-headings:tracking-tight prose-h2:text-[18px] prose-h2:text-altruistDark prose-h2:mt-8 prose-h2:mb-4 prose-h2:pb-2 prose-h2:border-b prose-h2:border-altruistGray-200 prose-p:text-altruistGray-800 prose-a:text-altruistBlue">
                    <ReactMarkdown>{report}</ReactMarkdown>
                  </div>
                ) : loadingReport ? (
                  <div className="flex flex-col h-full items-center justify-center py-8 animate-fade-in-up">
                    <div className="w-full max-w-md">
                      <h4 className="text-[16px] font-bold text-altruistDark mb-10 text-center flex items-center justify-center gap-3">
                        <div className="w-4 h-4 rounded-full border-2 border-altruistBlue border-t-transparent animate-spin" />
                        Synthesizing Advisory Intelligence
                      </h4>
                      <div className="space-y-6 relative ml-4">
                        <div className="absolute left-[19px] top-6 bottom-6 w-[2px] bg-altruistGray-100 z-0" />
                        {REPORT_STEPS.map((step, index) => {
                          const { isCompleted, isActive, isPending } = getStepState(index, reportStatus);
                          const Icon = step.icon;
                          return (
                            <div key={step.id} className={`flex items-start gap-5 relative z-10 transition-all duration-500 ${isPending ? 'opacity-40' : 'opacity-100'}`}>
                              <div className={`w-10 h-10 rounded-full flex items-center justify-center shadow-sm border-2 transition-colors duration-300 bg-altruistWhite ${isCompleted ? 'bg-altruistBlue border-altruistBlue text-white' : isActive ? 'border-altruistBlue text-altruistBlue shadow-[0_0_15px_rgba(21,101,192,0.3)]' : 'border-altruistGray-200 text-altruistGray-400'}`}>
                                {isCompleted ? <CheckCircle2 className="w-5 h-5" /> : isActive ? <Loader2 className="w-5 h-5 animate-spin" /> : <Icon className="w-5 h-5" />}
                              </div>
                              <div className={`flex-1 pt-2 transition-all duration-300 ${isActive ? 'scale-105 origin-left' : ''}`}>
                                <h5 className={`text-[14px] font-bold tracking-wide uppercase ${isActive ? 'text-altruistBlue' : isCompleted ? 'text-altruistDark' : 'text-altruistGray-400'}`}>
                                  {step.label}
                                </h5>
                                {isActive && (
                                  <p className="text-[12px] text-altruistGray-500 font-medium mt-1 animate-pulse">
                                    {index >= 1 && index <= 5 ? 'Analyzing concurrently...' : 'Agents are actively processing...'}
                                  </p>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center p-8 bg-altruistGray-50 rounded-sm border border-altruistGray-200">
                    <LayoutDashboard className="w-8 h-8 text-altruistBlue mb-4 opacity-50" />
                    <p className="text-[14px] font-medium text-altruistGray-800 mb-6 text-center">
                      Generate a comprehensive 30-day Executive Dossier using the multi-agent AI protocol.
                    </p>
                    <button onClick={() => generateReport(companyData.ticker)} className="bg-altruistBlue text-white px-6 py-2.5 rounded-sm text-[13px] font-bold uppercase tracking-wide hover:bg-blue-800 transition-colors flex items-center gap-2 shadow-sm">
                      <Activity className="w-4 h-4" /> Generate Executive Dossier
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
