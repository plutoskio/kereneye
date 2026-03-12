import React, { useState } from 'react';
import { X, TrendingDown, Loader2, AlertCircle, DollarSign } from 'lucide-react';

export default function SellModal({ holding, onClose, onSell }) {
  const [shares, setShares] = useState('');
  const [price, setPrice] = useState(holding.current_price?.toString() || '');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const sharesToSell = parseFloat(shares) || 0;
  const sellPrice = parseFloat(price) || 0;
  const proceeds = sharesToSell * sellPrice;
  const realizedPnl = (sellPrice - holding.avg_cost) * sharesToSell;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!shares || !price || !date || sharesToSell <= 0) return;
    if (sharesToSell > holding.shares) {
      setError(`You only have ${holding.shares} shares`);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await onSell(holding.ticker, sharesToSell, sellPrice, date);
    } catch (err) {
      setError(err.message || 'Failed to sell');
      setLoading(false);
    }
  };

  const sellAll = () => {
    setShares(holding.shares.toString());
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      <div className="relative bg-altruistWhite border border-altruistGray-200 shadow-2xl rounded-sm w-full max-w-md mx-4 animate-fade-in-up">
        {/* Header */}
        <div className="border-b border-altruistGray-200 px-6 py-4 flex justify-between items-center bg-red-50">
          <div>
            <h3 className="text-[13px] font-bold text-red-800 uppercase tracking-wide flex items-center gap-2">
              <TrendingDown className="w-4 h-4" />
              Sell {holding.ticker}
            </h3>
            <p className="text-[11px] text-red-600 mt-0.5">{holding.name}</p>
          </div>
          <button onClick={onClose} className="text-altruistGray-400 hover:text-altruistDark transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Position info */}
        <div className="px-6 py-3 bg-altruistGray-50 border-b border-altruistGray-200 grid grid-cols-3 gap-4">
          <div>
            <p className="text-[10px] font-bold text-altruistGray-500 uppercase tracking-widest">Shares Held</p>
            <p className="text-[14px] font-mono font-bold text-altruistDark">{holding.shares}</p>
          </div>
          <div>
            <p className="text-[10px] font-bold text-altruistGray-500 uppercase tracking-widest">Avg Cost</p>
            <p className="text-[14px] font-mono font-bold text-altruistDark">${holding.avg_cost.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-[10px] font-bold text-altruistGray-500 uppercase tracking-widest">Current</p>
            <p className="text-[14px] font-mono font-bold text-altruistDark">${holding.current_price.toFixed(2)}</p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-sm px-4 py-3 text-[13px] text-red-700 font-medium">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-2">
                Shares to Sell
              </label>
              <div className="relative">
                <input
                  type="number"
                  step="any"
                  min="0.01"
                  max={holding.shares}
                  placeholder={holding.shares.toString()}
                  value={shares}
                  onChange={(e) => setShares(e.target.value)}
                  className="w-full bg-altruistGray-50 border border-altruistGray-200 rounded-sm px-4 py-3 text-[14px] font-mono text-altruistDark placeholder-altruistGray-400 focus:outline-none focus:border-red-400 focus:bg-altruistWhite transition-colors"
                  required
                  autoFocus
                />
                <button
                  type="button"
                  onClick={sellAll}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-bold text-red-600 uppercase tracking-widest hover:text-red-800"
                >
                  All
                </button>
              </div>
            </div>
            <div>
              <label className="block text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-2">
                Sell Price ($)
              </label>
              <input
                type="number"
                step="any"
                min="0.01"
                placeholder={holding.current_price.toFixed(2)}
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="w-full bg-altruistGray-50 border border-altruistGray-200 rounded-sm px-4 py-3 text-[14px] font-mono text-altruistDark placeholder-altruistGray-400 focus:outline-none focus:border-red-400 focus:bg-altruistWhite transition-colors"
                required
              />
            </div>
            <div>
              <label className="block text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-2">
                Date
              </label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                max={new Date().toISOString().split('T')[0]}
                className="w-full bg-altruistGray-50 border border-altruistGray-200 rounded-sm px-4 py-3 text-[14px] font-mono text-altruistDark focus:outline-none focus:border-red-400 focus:bg-altruistWhite transition-colors"
                required
              />
            </div>
          </div>

          {/* Preview */}
          {sharesToSell > 0 && sellPrice > 0 && (
            <div className="space-y-3">
              <div className="bg-altruistGray-50 border border-altruistGray-200 rounded-sm p-4 flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-1">Proceeds</p>
                  <p className="text-[20px] font-mono font-medium text-altruistDark tabular-nums">
                    ${proceeds.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-1">Realized P&L</p>
                  <p className={`text-[20px] font-mono font-bold tabular-nums ${realizedPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {realizedPnl >= 0 ? '+' : ''}${realizedPnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </p>
                </div>
              </div>

              {sharesToSell < holding.shares && (
                <p className="text-[12px] text-altruistGray-500 text-center">
                  Remaining: {(holding.shares - sharesToSell).toFixed(4)} shares
                </p>
              )}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !shares || !price || !date || sharesToSell <= 0}
            className="w-full bg-red-600 text-white py-3 rounded-sm text-[13px] font-bold uppercase tracking-wide hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing Sale...
              </>
            ) : (
              <>
                <DollarSign className="w-4 h-4" />
                Sell {sharesToSell > 0 ? `${sharesToSell} Shares` : 'Shares'}
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
