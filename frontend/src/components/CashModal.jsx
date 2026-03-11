import React, { useState } from 'react';
import { X, Wallet, Loader2 } from 'lucide-react';

export default function CashModal({ currentCash, onClose, onSave }) {
  const [amount, setAmount] = useState(currentCash?.toString() || '0');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSave(parseFloat(amount) || 0);
    } catch {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-altruistWhite border border-altruistGray-200 shadow-2xl rounded-sm w-full max-w-sm mx-4 animate-fade-in-up">
        <div className="border-b border-altruistGray-200 px-6 py-4 flex justify-between items-center bg-altruistGray-50">
          <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide flex items-center gap-2">
            <Wallet className="w-4 h-4" />
            Cash Balance
          </h3>
          <button onClick={onClose} className="text-altruistGray-400 hover:text-altruistDark transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-2">
              Set Cash Balance ($)
            </label>
            <input
              type="number"
              step="any"
              min="0"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full bg-altruistGray-50 border border-altruistGray-200 rounded-sm px-4 py-3 text-[18px] font-mono font-bold text-altruistDark focus:outline-none focus:border-altruistBlue focus:bg-altruistWhite transition-colors"
              autoFocus
            />
            <p className="text-[11px] text-altruistGray-400 mt-2">
              This is your available cash for buying stocks. Buying deducts, selling adds.
            </p>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-altruistBlue text-white py-3 rounded-sm text-[13px] font-bold uppercase tracking-wide hover:bg-blue-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save'}
          </button>
        </form>
      </div>
    </div>
  );
}
