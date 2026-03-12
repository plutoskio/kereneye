import React, { Suspense, lazy, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './index.css';

const PortfolioDashboard = lazy(() => import('./pages/PortfolioDashboard'));
const StockDetail = lazy(() => import('./pages/StockDetail'));
const TransactionHistory = lazy(() => import('./pages/TransactionHistory'));

function RouteFallback() {
  return (
    <div className="flex min-h-[320px] items-center justify-center">
      <div className="panel-structured w-full max-w-2xl p-8">
        <div className="skeleton h-8 w-48 rounded-sm" />
        <div className="mt-4 space-y-3">
          <div className="skeleton h-4 w-full rounded-sm" />
          <div className="skeleton h-4 w-5/6 rounded-sm" />
          <div className="skeleton h-4 w-2/3 rounded-sm" />
        </div>
      </div>
    </div>
  );
}

function App() {
  const navigate = useNavigate();
  const [searchTicker, setSearchTicker] = useState('');

  const handleSearchSubmit = (event) => {
    event.preventDefault();

    const normalizedTicker = searchTicker.trim().toUpperCase();
    if (!normalizedTicker) return;

    navigate(`/stock/${normalizedTicker}`);
    setSearchTicker('');
  };

  return (
    <div className="min-h-screen bg-altruistGray-50 text-altruistGray-900 font-sans flex flex-col">
      {/* GLOBAL HEADER */}
      <header className="border-b border-altruistGray-200 bg-altruistWhite px-8 py-3 sticky top-0 z-50 flex flex-col gap-3 shadow-sm md:h-16 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-6">
          <h1
            onClick={() => navigate('/')}
            className="text-xl font-bold tracking-tight text-altruistDark flex items-center gap-3 cursor-pointer hover:opacity-70 transition-opacity"
          >
            KerenEye
            <span className="text-altruistGray-300 font-normal">|</span>
            <span className="text-altruistGray-500 font-medium">Portfolio Intelligence</span>
          </h1>
        </div>

        <div className="flex w-full flex-col gap-3 md:w-auto md:flex-row md:items-center md:justify-end">
          <form onSubmit={handleSearchSubmit} className="flex w-full items-center gap-2 md:w-[320px]">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-altruistGray-400" />
              <input
                type="text"
                value={searchTicker}
                onChange={(event) => setSearchTicker(event.target.value)}
                placeholder="Search ticker"
                aria-label="Search stock ticker"
                className="w-full rounded-sm border border-altruistGray-200 bg-altruistWhite py-2 pl-9 pr-3 text-sm font-medium uppercase tracking-wide text-altruistDark outline-none transition-colors placeholder:text-altruistGray-400 focus:border-altruistBlue"
              />
            </div>
            <button
              type="submit"
              disabled={!searchTicker.trim()}
              className="rounded-sm bg-altruistBlue px-4 py-2 text-[11px] font-bold uppercase tracking-widest text-white transition-colors hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-altruistGray-300"
            >
              Search
            </button>
          </form>

          <nav className="flex items-center gap-6">
            <button
              onClick={() => navigate('/')}
              className="text-[12px] font-bold text-altruistGray-500 uppercase tracking-widest hover:text-altruistDark transition-colors"
            >
              Portfolio
            </button>
            <button
              onClick={() => navigate('/transactions')}
              className="text-[12px] font-bold text-altruistGray-500 uppercase tracking-widest hover:text-altruistDark transition-colors"
            >
              Transactions
            </button>
          </nav>
        </div>
      </header>

      {/* ROUTES */}
      <main className="flex-1 w-full max-w-[1600px] mx-auto p-8">
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<PortfolioDashboard />} />
            <Route path="/stock/:ticker" element={<StockDetail />} />
            <Route path="/transactions" element={<TransactionHistory />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}

export default App;
