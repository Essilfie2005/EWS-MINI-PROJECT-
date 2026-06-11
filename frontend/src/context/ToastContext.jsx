import { createContext, useCallback, useContext, useState } from 'react';
import { CheckCircle, XCircle, Info, X } from 'lucide-react';

const ToastContext = createContext(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

let toastId = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((rawMessage, type = 'info', duration = 4000) => {
    // Always normalize to string
    let message = rawMessage;
    if (typeof message !== 'string') {
      if (Array.isArray(message)) {
        message = message.map(m => (typeof m === 'object' ? m.msg || JSON.stringify(m) : String(m))).join('; ');
      } else if (typeof message === 'object' && message !== null) {
        message = message.msg || message.detail || message.message || JSON.stringify(message);
      } else {
        message = String(message);
      }
    }
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message, type }]);
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const icons = {
    success: <CheckCircle size={18} />,
    error: <XCircle size={18} />,
    info: <Info size={18} />,
  };

  return (
    <ToastContext.Provider value={addToast}>
      {children}
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`}>
            {icons[t.type] || icons.info}
            <span style={{ flex: 1 }}>{typeof t.message === 'string' ? t.message : (t.message?.msg || t.message?.detail || t.message?.message || JSON.stringify(t.message))}</span>
            <button
              onClick={() => removeToast(t.id)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                padding: 0,
                display: 'flex',
                cursor: 'pointer',
              }}
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
