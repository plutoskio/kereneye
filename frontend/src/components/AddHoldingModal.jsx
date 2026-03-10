import React, { useState } from 'react';
import { X, Search, Loader2, AlertCircle } from 'lucide-react';

export default function AddHoldingModal({ onClose, onAdd }) {
  const [ticker, setTicker] = useState('');
  const [shares, setShares] = useState('');
  const [avgCost, setAvgCost] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!ticker.trim() || !shares || !avgCost) return;

    setLoading(true);
    setError(null);

    try {
      await onAdd(ticker.trim().toUpperCase(), parseFloat(shares), parseFloat(avgCost));
    } catch (err) {
      setError(err.message || 'Failed to add holding');
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-altruistWhite border border-altruistGray-200 shadow-2xl rounded-sm w-full max-w-md mx-4 animate-fade-in-up">
        {/* Header */}
        <div className="border-b border-altruistGray-200 px-6 py-4 flex justify-between items-center bg-altruistGray-50">
          <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide">Add Holding</h3>
          <button onClick={onClose} className="text-altruistGray-400 hover:text-altruistDark transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-sm px-4 py-3 text-[13px] text-red-700 font-medium">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          {/* Ticker */}
          <div>
            <label className="block text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-2">
              Ticker Symbol
            </label>
            <div className="relative">
              <Search className="w-4 h-4 text-altruistGray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="e.g. AAPL"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="w-full bg-altruistGray-50 border border-altruistGray-200 rounded-sm pl-10 pr-4 py-3 text-[14px] font-mono font-bold uppercase text-altruistDark placeholder-altruistGray-400 focus:outline-none focus:border-altruistBlue focus:bg-altruistWhite transition-colors"
                required
                autoFocus
              />
            </div>
          </div>

          {/* Shares & Price row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-2">
                Shares
              </label>
              <input
                type="number"
                step="any"
                min="0.01"
                placeholder="10"
                value={shares}
                onChange={(e) => setShares(e.target.value)}
                className="w-full bg-altruistGray-50 border border-altruistGray-200 rounded-sm px-4 py-3 text-[14px] font-mono text-altruistDark placeholder-altruistGray-400 focus:outline-none focus:border-altruistBlue focus:bg-altruistWhite transition-colors"
                required
              />
            </div>
            <div>
              <label className="block text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-2">
                Avg Cost ($)
              </label>
              <input
                type="number"
                step="any"
                min="0.01"
                placeholder="150.00"
                value={avgCost}
                onChange={(e) => setAvgCost(e.target.value)}
                className="w-full bg-altruistGray-50 border border-altruistGray-200 rounded-sm px-4 py-3 text-[14px] font-mono text-altruistDark placeholder-altruistGray-400 focus:outline-none focus:border-altruistBlue focus:bg-altruistWhite transition-colors"
                required
              />
            </div>
          </div>

          {/* Preview */}
          {ticker && shares && avgCost && (
            <div className="bg-altruistGray-50 border border-altruistGray-200 rounded-sm p-4">
              <p className="text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-1">Total Investment</p>
              <p className="text-[20px] font-mono font-medium text-altruistDark tabular-nums">
                ${(parseFloat(shares) * parseFloat(avgCost)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
              <p className="text-[12px] text-altruistGray-500 mt-1">
                {shares} shares of {ticker} at ${parseFloat(avgCost).toFixed(2)} each
              </p>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading || !ticker || !shares || !avgCost}
            className="w-full bg-altruistBlue text-white py-3 rounded-sm text-[13px] font-bold uppercase tracking-wide hover:bg-blue-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Validating Ticker...
              </>
            ) : (
              'Add to Portfolio'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
