import { AlertTriangle, WifiOff, RefreshCw } from 'lucide-react';

function normalizeMessage(msg) {
  if (!msg) return 'Unable to connect to the server. Please ensure the backend API is running.';
  if (typeof msg === 'string') return msg;
  if (Array.isArray(msg)) {
    return msg.map((m) => (typeof m === 'object' ? m.msg || JSON.stringify(m) : String(m))).join('; ');
  }
  if (typeof msg === 'object') return msg.detail || msg.message || msg.msg || JSON.stringify(msg);
  return String(msg);
}

export default function ErrorState({ message, onRetry }) {
  return (
    <div className="empty-state">
      <WifiOff />
      <p className="title">Connection Error</p>
      <p className="description">
        {normalizeMessage(message)}
      </p>
      {onRetry && (
        <button
          className="btn btn-secondary btn-sm"
          style={{ marginTop: 16 }}
          onClick={onRetry}
        >
          <RefreshCw size={14} />
          Retry
        </button>
      )}
    </div>
  );
}

export function ErrorBanner({ message }) {
  return (
    <div className="error-banner">
      <AlertTriangle size={18} />
      <span>{normalizeMessage(message)}</span>
    </div>
  );
}
