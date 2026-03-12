import React, { useEffect, useState } from 'react';
import { X, Wallet, Loader2, Plus, Minus, History } from 'lucide-react';

export default function CashModal({ currentCash, onClose, onSave }) {
  const [action, setAction] = useState('deposit');
  const [amount, setAmount] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (action === 'snapshot') {
      setAmount(currentCash?.toString() || '0');
      return;
    }

    setAmount('');
  }, [action, currentCash]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSave(parseFloat(amount) || 0, date, action);
    } catch {
      setLoading(false);
    }
  };

  const actionOptions = [
    {
      id: 'deposit',
      label: 'Deposit',
      icon: Plus,
      description: 'Add new funds to the account on this date.',
    },
    {
      id: 'withdraw',
      label: 'Withdraw',
      icon: Minus,
      description: 'Remove funds from the account on this date.',
    },
    {
      id: 'snapshot',
      label: 'Snapshot',
      icon: History,
      description: 'Set the exact cash balance for that date. Use for corrections.',
    },
  ];

  const amountLabel = action === 'snapshot' ? 'Cash Balance ($)' : `${action === 'deposit' ? 'Deposit' : 'Withdrawal'} Amount ($)`;
  const helperText = action === 'snapshot'
    ? 'This records the exact cash balance on the selected date.'
    : `This records a ${action} in the cash ledger on the selected date.`;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-altruistWhite border border-altruistGray-200 shadow-2xl rounded-sm w-full max-w-sm mx-4 animate-fade-in-up">
        <div className="border-b border-altruistGray-200 px-6 py-4 flex justify-between items-center bg-altruistGray-50">
          <h3 className="text-[13px] font-bold text-altruistGray-800 uppercase tracking-wide flex items-center gap-2">
            <Wallet className="w-4 h-4" />
            Manage Cash
          </h3>
          <button onClick={onClose} className="text-altruistGray-400 hover:text-altruistDark transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-2">
              Action
            </label>
            <div className="grid grid-cols-3 gap-2">
              {actionOptions.map((option) => {
                const Icon = option.icon;
                const isActive = action === option.id;

                return (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => setAction(option.id)}
                    className={`rounded-sm border px-3 py-3 text-left transition-colors ${
                      isActive
                        ? 'border-altruistBlue bg-altruistBlue/10 text-altruistBlue'
                        : 'border-altruistGray-200 bg-altruistGray-50 text-altruistGray-600 hover:border-altruistGray-300 hover:bg-altruistWhite'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-widest">
                      <Icon className="h-3.5 w-3.5" />
                      {option.label}
                    </div>
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-[11px] text-altruistGray-400">
              {actionOptions.find((option) => option.id === action)?.description}
            </p>
          </div>
          <div>
            <label className="block text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-2">
              {amountLabel}
            </label>
            <input
              type="number"
              step="any"
              min="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full bg-altruistGray-50 border border-altruistGray-200 rounded-sm px-4 py-3 text-[18px] font-mono font-bold text-altruistDark focus:outline-none focus:border-altruistBlue focus:bg-altruistWhite transition-colors"
              autoFocus
              required
            />
            <p className="text-[11px] text-altruistGray-400 mt-2">
              Current cash: ${Number(currentCash || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}. {helperText}
            </p>
          </div>
          <div>
            <label className="block text-[11px] font-bold text-altruistGray-500 uppercase tracking-widest mb-2">
              Effective Date
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              max={new Date().toISOString().split('T')[0]}
              className="w-full bg-altruistGray-50 border border-altruistGray-200 rounded-sm px-4 py-3 text-[14px] font-mono text-altruistDark focus:outline-none focus:border-altruistBlue focus:bg-altruistWhite transition-colors"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading || !date || !amount}
            className="w-full bg-altruistBlue text-white py-3 rounded-sm text-[13px] font-bold uppercase tracking-wide hover:bg-blue-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : action === 'snapshot' ? 'Save Snapshot' : action === 'deposit' ? 'Add Cash' : 'Subtract Cash'}
          </button>
        </form>
      </div>
    </div>
  );
}
