import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Search, ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import PortfolioDashboard from './pages/PortfolioDashboard';
import StockDetail from './pages/StockDetail';
import TransactionHistory from './pages/TransactionHistory';
import './index.css';

function App() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-altruistGray-50 text-altruistGray-900 font-sans flex flex-col">
      {/* GLOBAL HEADER */}
      <header className="border-b border-altruistGray-200 bg-altruistWhite px-8 h-16 sticky top-0 z-50 flex items-center justify-between shadow-sm">
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
      </header>

      {/* ROUTES */}
      <main className="flex-1 w-full max-w-[1600px] mx-auto p-8">
        <Routes>
          <Route path="/" element={<PortfolioDashboard />} />
          <Route path="/stock/:ticker" element={<StockDetail />} />
          <Route path="/transactions" element={<TransactionHistory />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
