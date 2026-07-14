import { useState, useEffect } from 'react';
import { Play, X, FlaskConical } from 'lucide-react';
import api from '../services/api';

const STORAGE_KEY = 'ews_demo_mode';

export default function DemoModeToggle() {
  const [demoActive, setDemoActive] = useState(
    () => localStorage.getItem(STORAGE_KEY) === 'true'
  );
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(demoActive));
  }, [demoActive]);

  const activateDemo = async () => {
    setLoading(true);
    setMessage('');
    try {
      await api.post('/predictions/demo-mode');
      setDemoActive(true);
      setShowModal(false);
    } catch (err) {
      if (err.response?.status === 404) {
        // Endpoint not implemented yet — still set demo UI flag
        setDemoActive(true);
        setShowModal(false);
      } else {
        setMessage('Could not activate demo mode. Backend may be unavailable.');
      }
    } finally {
      setLoading(false);
    }
  };

  const exitDemo = async () => {
    setLoading(true);
    try {
      await api.delete('/predictions/demo-mode');
    } catch {
      // Ignore — just clear local flag
    } finally {
      setDemoActive(false);
      setLoading(false);
    }
  };

  return (
    <>
      {/* Demo Mode Banner */}
      {demoActive && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, zIndex: 9999,
          background: 'linear-gradient(90deg, #f59e0b, #f43f5e)',
          color: 'white', textAlign: 'center', padding: '6px 16px',
          fontSize: 13, fontWeight: 700, display: 'flex',
          alignItems: 'center', justifyContent: 'center', gap: 12,
          boxShadow: '0 2px 12px rgba(245,158,11,0.4)',
        }}>
          <FlaskConical size={14} />
          DEMO MODE ACTIVE — Synthetic exhibition data loaded
          <button
            onClick={exitDemo}
            style={{
              background: 'rgba(255,255,255,0.2)', border: '1px solid rgba(255,255,255,0.4)',
              color: 'white', borderRadius: 6, padding: '2px 10px', cursor: 'pointer',
              fontSize: 11, fontWeight: 600,
            }}
          >
            {loading ? '...' : 'Exit Demo'}
          </button>
        </div>
      )}

      {/* Floating trigger button */}
      {!demoActive && (
        <button
          onClick={() => setShowModal(true)}
          title="Activate Demo Mode for exhibitions"
          style={{
            position: 'fixed', bottom: 28, right: 28, zIndex: 1000,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            color: 'white', border: 'none', borderRadius: 12,
            padding: '10px 16px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
            display: 'flex', alignItems: 'center', gap: 8,
            boxShadow: '0 4px 24px rgba(99,102,241,0.5)',
            transition: 'transform 0.2s, box-shadow 0.2s',
          }}
          onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.05)'; e.currentTarget.style.boxShadow = '0 6px 32px rgba(99,102,241,0.7)'; }}
          onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.boxShadow = '0 4px 24px rgba(99,102,241,0.5)'; }}
        >
          <Play size={14} />
          Demo Mode
        </button>
      )}

      {/* Confirmation Modal */}
      {showModal && (
        <div
          style={{
            position: 'fixed', inset: 0, zIndex: 10000,
            background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
          onClick={e => { if (e.target === e.currentTarget) setShowModal(false); }}
        >
          <div style={{
            background: 'linear-gradient(135deg, #1a2340, #131b2e)',
            border: '1px solid rgba(99,102,241,0.3)', borderRadius: 16,
            padding: 32, maxWidth: 420, width: '90%',
            boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h2 style={{ color: '#f1f5f9', fontSize: 18, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                <FlaskConical size={20} color="#f59e0b" /> Demo Mode
              </h2>
              <button onClick={() => setShowModal(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>
            <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6, marginBottom: 20 }}>
              Demo Mode loads 30 pre-set high-contrast synthetic students optimised for exhibition demonstrations.
              This will <strong style={{ color: '#f1f5f9' }}>not affect your real data</strong> — students are tagged as synthetic.
            </p>
            {message && (
              <p style={{ color: '#f43f5e', fontSize: 13, marginBottom: 16, background: 'rgba(244,63,94,0.1)', padding: '8px 12px', borderRadius: 8 }}>
                {message}
              </p>
            )}
            <div style={{ display: 'flex', gap: 12 }}>
              <button
                onClick={activateDemo}
                disabled={loading}
                style={{
                  flex: 1, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                  color: 'white', border: 'none', borderRadius: 8, padding: '10px 0',
                  cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: 14,
                  opacity: loading ? 0.7 : 1,
                }}
              >
                {loading ? 'Activating...' : 'Activate Demo Mode'}
              </button>
              <button
                onClick={() => setShowModal(false)}
                style={{
                  flex: 1, background: 'rgba(255,255,255,0.06)', color: '#94a3b8',
                  border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '10px 0',
                  cursor: 'pointer', fontWeight: 600, fontSize: 14,
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
