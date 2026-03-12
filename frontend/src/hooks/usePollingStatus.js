import { useEffect, useState } from 'react';

export default function usePollingStatus({
  enabled,
  fetchStatus,
  intervalMs = 1000,
  initialStatus = '',
}) {
  const [status, setStatus] = useState('');

  useEffect(() => {
    let intervalId;
    let cancelled = false;

    const poll = async () => {
      try {
        const nextStatus = await fetchStatus();
        if (!cancelled) {
          setStatus(nextStatus || '');
        }
      } catch {
        // Ignore polling errors. The main request path handles user-visible failures.
      }
    };

    if (enabled) {
      setStatus(initialStatus);
      poll();
      intervalId = setInterval(poll, intervalMs);
    } else {
      setStatus('');
    }

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [enabled, fetchStatus, initialStatus, intervalMs]);

  return status;
}
