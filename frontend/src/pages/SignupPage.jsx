import { useState } from 'react';
import { ShieldAlert, Eye, EyeOff, Loader2, CheckCircle } from 'lucide-react';
import { registerUser } from '../services/api';

export default function SignupPage() {
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    confirm_password: '',
    role: 'counsellor',
  });
  const [showPass, setShowPass] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (form.password !== form.confirm_password) {
      setError('Passwords do not match.');
      return;
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setLoading(true);
    try {
      const res = await registerUser({
        username: form.username.trim(),
        email: form.email.trim() || undefined,
        password: form.password,
        confirm_password: form.confirm_password,
        role: form.role,
      });
      setSuccess(res.data.message || 'Account created! You can now log in.');
      setForm({ username: '', email: '', password: '', confirm_password: '', role: 'counsellor' });
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map(d => d.msg || JSON.stringify(d)).join(' · '));
      } else {
        setError(typeof detail === 'string' ? detail : 'Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = { width: '100%', paddingRight: 44 };

  return (
    <div className="login-page">
      <div className="login-card slide-up">
        {/* Logo */}
        <div className="login-logo">
          <div className="logo-icon">
            <ShieldAlert size={24} />
          </div>
          <div>
            <div className="logo-title">EWS Dashboard</div>
            <div className="logo-subtitle">Dropout Early Warning System</div>
          </div>
        </div>

        <h2 className="login-heading">Create an account</h2>

        {error && <div className="login-error">{error}</div>}
        {success && (
          <div className="login-success">
            <CheckCircle size={14} style={{ marginRight: 6, flexShrink: 0 }} />
            {success}
            <a href="/login" style={{ marginLeft: 8, color: 'inherit', fontWeight: 700 }}>
              Sign in →
            </a>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Username */}
          <div className="form-group">
            <label className="form-label">Username *</label>
            <input
              type="text"
              className="form-input"
              placeholder="Choose a username"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              autoComplete="username"
              required
              minLength={3}
            />
          </div>

          {/* Email (optional) */}
          <div className="form-group">
            <label className="form-label">Email <span style={{ color: 'var(--text-dim)', fontWeight: 400 }}>(optional)</span></label>
            <input
              type="email"
              className="form-input"
              placeholder="your@email.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              autoComplete="email"
            />
          </div>

          {/* Role */}
          <div className="form-group">
            <label className="form-label">Role *</label>
            <select
              className="form-select"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              required
            >
              <option value="counsellor">Counsellor</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          {/* Password */}
          <div className="form-group">
            <label className="form-label">Password *</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPass ? 'text' : 'password'}
                className="form-input"
                placeholder="At least 6 characters"
                value={form.password}
                style={inputStyle}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                autoComplete="new-password"
                required
                minLength={6}
              />
              <button type="button" onClick={() => setShowPass(p => !p)} style={eyeBtnStyle}>
                {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Confirm Password */}
          <div className="form-group">
            <label className="form-label">Confirm Password *</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showConfirm ? 'text' : 'password'}
                className="form-input"
                placeholder="Repeat your password"
                value={form.confirm_password}
                style={inputStyle}
                onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
                autoComplete="new-password"
                required
              />
              <button type="button" onClick={() => setShowConfirm(p => !p)} style={eyeBtnStyle}>
                {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 8, height: 44 }}
            disabled={loading}
          >
            {loading ? <><Loader2 size={16} className="spin" /> Creating account...</> : 'Create Account'}
          </button>
        </form>

        <p className="login-hint" style={{ marginTop: 16 }}>
          Already have an account?{' '}
          <a href="/login" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}>
            Sign in
          </a>
        </p>
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
        .login-logo .logo-title { font-size: 16px; font-weight: 700; color: var(--text-primary); }
        .login-logo .logo-subtitle { font-size: 12px; color: var(--text-muted); }
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
        .login-success {
          display: flex;
          align-items: center;
          background: rgba(34, 197, 94, 0.1);
          border: 1px solid rgba(34, 197, 94, 0.25);
          color: #4ade80;
          border-radius: var(--radius-sm);
          padding: 10px 14px;
          font-size: 13px;
          margin-bottom: 16px;
        }
        .login-hint {
          text-align: center;
          font-size: 12px;
          color: var(--text-dim);
          margin-top: 12px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .spin { animation: spin 0.8s linear infinite; }
      `}</style>
    </div>
  );
}

const eyeBtnStyle = {
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
};
