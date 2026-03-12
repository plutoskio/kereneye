import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight, ArrowDownRight, Clock } from 'lucide-react';
import { getTransactions } from '../api/client';

export default function TransactionHistory() {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        setTransactions(await getTransactions());
      } catch (err) {
        console.error('Failed to fetch transactions:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchTransactions();
  }, []);

  const formatDate = (iso) => {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) +
      ' ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="animate-fade-in-up">
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-2 text-[12px] font-bold text-altruistGray-500 uppercase tracking-widest hover:text-altruistDark transition-colors mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Portfolio
      </button>

      <div className="panel-structured overflow-hidden">
        <div className="border-b border-altruistGray-200 px-6 py-4 bg-altruistGray-50 flex items-center gap-2">
          <Clock className="w-4 h-4 text-altruistBlue" />
          <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide">
            Transaction History
          </h3>
          <span className="text-[11px] font-medium text-altruistGray-400 ml-2">
            ({transactions.length} transactions)
          </span>
        </div>

        {loading ? (
          <div className="p-8 space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="skeleton h-12 w-full rounded-sm" />
            ))}
          </div>
        ) : transactions.length === 0 ? (
          <div className="p-12 text-center">
            <Clock className="w-8 h-8 text-altruistGray-300 mx-auto mb-4" />
            <p className="text-[14px] font-medium text-altruistGray-500">No transactions yet</p>
            <p className="text-[12px] text-altruistGray-400 mt-1">Add holdings to your portfolio to start tracking.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-altruistGray-200 bg-altruistGray-50/50">
                  <th className="text-left px-6 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">Date</th>
                  <th className="text-left px-4 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">Type</th>
                  <th className="text-left px-4 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">Ticker</th>
                  <th className="text-right px-4 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">Shares</th>
                  <th className="text-right px-4 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">Price</th>
                  <th className="text-right px-4 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">Total</th>
                  <th className="text-right px-6 py-3 font-bold text-altruistGray-500 uppercase tracking-wider text-[11px]">P&L</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t, i) => (
                  <tr key={i} className="border-b border-altruistGray-100 hover:bg-altruistGray-50 transition-colors">
                    <td className="px-6 py-4 text-altruistGray-600 font-medium">{formatDate(t.timestamp)}</td>
                    <td className="px-4 py-4">
                      <span className={`inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-sm ${
                        t.type === 'buy'
                          ? 'bg-green-50 text-green-700 border border-green-200'
                          : 'bg-red-50 text-red-700 border border-red-200'
                      }`}>
                        {t.type === 'buy' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                        {t.type}
                      </span>
                    </td>
                    <td className="px-4 py-4 font-mono font-bold text-altruistBlue">{t.ticker}</td>
                    <td className="px-4 py-4 text-right font-mono tabular-nums">{t.shares}</td>
                    <td className="px-4 py-4 text-right font-mono tabular-nums">${t.price?.toFixed(2)}</td>
                    <td className="px-4 py-4 text-right font-mono tabular-nums font-bold">${(t.shares * t.price)?.toFixed(2)}</td>
                    <td className="px-6 py-4 text-right font-mono tabular-nums font-bold">
                      {t.type === 'sell' && t.realized_pnl !== undefined ? (
                        <span className={t.realized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {t.realized_pnl >= 0 ? '+' : ''}${t.realized_pnl?.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-altruistGray-300">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
