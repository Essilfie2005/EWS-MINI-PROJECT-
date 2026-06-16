import { useState } from 'react';
import { ShieldAlert, Eye, EyeOff, Loader2 } from 'lucide-react';

// Demo credentials — replace with a real auth endpoint when available
const DEMO_USER = 'admin';
const DEMO_PASS = 'ews2024';

export default function LoginPage({ onLogin }) {
  const [form, setForm] = useState({ username: '', password: '' });
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Simulate async check (swap for real API call when auth is added)
    await new Promise((r) => setTimeout(r, 600));

    if (form.username === DEMO_USER && form.password === DEMO_PASS) {
      localStorage.setItem('ews_token', btoa(`${form.username}:${form.password}`));
      onLogin();
    } else {
      setError('Invalid username or password.');
    }
    setLoading(false);
  };

  return (
    <div className="login-page">
      <div className="login-card slide-up">
        <div className="login-logo">
          <div className="logo-icon">
            <ShieldAlert size={24} />
          </div>
          <div>
            <div className="logo-title">EWS Dashboard</div>
            <div className="logo-subtitle">Dropout Early Warning System</div>
          </div>
        </div>

        <h2 className="login-heading">Sign in to continue</h2>

        {error && (
          <div className="login-error">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <input
              type="text"
              className="form-input"
              placeholder="Enter username"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              autoComplete="username"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPass ? 'text' : 'password'}
                className="form-input"
                placeholder="Enter password"
                value={form.password}
                style={{ width: '100%', paddingRight: 44 }}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPass((p) => !p)}
                style={{
                  position: 'absolute',
                  right: 12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  display: 'flex',
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 8, height: 44 }}
            disabled={loading}
          >
            {loading ? <><Loader2 size={16} className="spin" /> Signing in...</> : 'Sign In'}
          </button>
        </form>

        <p className="login-hint">Demo: <code>admin</code> / <code>ews2024</code></p>
      </div>

      <style>{`
        .login-page {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          background: linear-gradient(135deg, var(--bg-deep) 0%, var(--bg-surface) 50%, #0f172a 100%);
        }
        .login-card {
          width: 100%;
          max-width: 420px;
          background: var(--glass-bg);
          backdrop-filter: blur(var(--glass-blur));
          border: 1px solid var(--glass-border);
          border-radius: var(--radius-xl);
          padding: 40px 36px;
          box-shadow: var(--shadow-xl);
        }
        .login-logo {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 32px;
        }
        .login-logo .logo-icon {
          width: 44px;
          height: 44px;
          border-radius: var(--radius-md);
          background: linear-gradient(135deg, var(--accent), #8b5cf6);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
          flex-shrink: 0;
        }
        .login-logo .logo-title {
          font-size: 16px;
          font-weight: 700;
          color: var(--text-primary);
        }
        .login-logo .logo-subtitle {
          font-size: 12px;
          color: var(--text-muted);
        }
        .login-heading {
          font-size: 22px;
          font-weight: 700;
          color: var(--text-primary);
          margin-bottom: 24px;
          letter-spacing: -0.02em;
        }
        .login-error {
          background: var(--risk-high-bg);
          border: 1px solid rgba(244, 63, 94, 0.25);
          color: var(--risk-high);
          border-radius: var(--radius-sm);
          padding: 10px 14px;
          font-size: 13px;
          margin-bottom: 16px;
        }
        .login-hint {
          text-align: center;
          font-size: 12px;
          color: var(--text-dim);
          margin-top: 20px;
        }
        .login-hint code {
          background: rgba(255,255,255,0.07);
          padding: 1px 6px;
          border-radius: 4px;
          color: var(--text-muted);
          font-family: monospace;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 0.8s linear infinite;
        }
      `}</style>
    </div>
  );
}
