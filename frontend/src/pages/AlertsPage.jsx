import { useState, useEffect, useCallback } from 'react';
import {
  Send,
  Users,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
} from 'lucide-react';
import { sendSMSAlert, fetchAlertHistory } from '../services/api';
import { SkeletonTable } from '../components/shared/Skeleton';
import ErrorState from '../components/shared/ErrorState';
import { useToast } from '../context/ToastContext';

const PAGE_SIZE = 15;

const statusIcon = {
  delivered: <CheckCircle2 size={14} style={{ color: 'var(--risk-safe)' }} />,
  failed: <XCircle size={14} style={{ color: 'var(--risk-high)' }} />,
  pending: <Clock size={14} style={{ color: 'var(--risk-medium)' }} />,
  sent: <CheckCircle2 size={14} style={{ color: 'var(--accent)' }} />,
};

export default function AlertsPage() {
  const addToast = useToast();

  // Send form
  const [studentId, setStudentId] = useState('');
  const [customMessage, setCustomMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [batchSending, setBatchSending] = useState(false);

  // History
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAlertHistory();
      setHistory(Array.isArray(res.data) ? res.data : res.data?.alerts || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load alert history');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const totalPages = Math.max(1, Math.ceil(history.length / PAGE_SIZE));
  const paginated = history.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!studentId.trim()) {
      addToast('Please enter a Student ID', 'error');
      return;
    }
    setSending(true);
    try {
      await sendSMSAlert({ student_id: studentId.trim(), message: customMessage || undefined });
      addToast(`SMS alert sent to ${studentId}`, 'success');
      setStudentId('');
      setCustomMessage('');
      loadHistory();
    } catch (err) {
      addToast(err.response?.data?.detail || 'Failed to send SMS', 'error');
    } finally {
      setSending(false);
    }
  };

  const handleBatchSend = async () => {
    setBatchSending(true);
    try {
      await sendSMSAlert({ batch: true });
      addToast('Batch SMS alerts triggered for all pending students', 'success');
      loadHistory();
    } catch (err) {
      addToast(err.response?.data?.detail || 'Batch send failed', 'error');
    } finally {
      setBatchSending(false);
    }
  };

  return (
    <div className="fade-in">
      {/* Send Panel */}
      <div className="dashboard-grid" style={{ marginBottom: 24 }}>
        {/* Individual Send */}
        <div className="glass-card slide-up">
          <h3 className="section-title" style={{ marginBottom: 16 }}>Send SMS Alert</h3>
          <form onSubmit={handleSend}>
            <div className="form-group">
              <label className="form-label">Student ID</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. STU-001"
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Custom Message (optional)</label>
              <textarea
                className="form-input form-textarea"
                placeholder="Leave empty to use the default alert template..."
                value={customMessage}
                onChange={(e) => setCustomMessage(e.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={sending} style={{ width: '100%' }}>
              {sending ? (
                <>
                  <Loader2 size={14} className="spin" /> Sending...
                </>
              ) : (
                <>
                  <Send size={14} /> Send Alert
                </>
              )}
            </button>
          </form>
        </div>

        {/* Batch Send */}
        <div className="glass-card slide-up stagger-2">
          <h3 className="section-title" style={{ marginBottom: 16 }}>Batch Send</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 20, lineHeight: 1.6 }}>
            Send SMS alerts to all students currently flagged as high or critical risk who have
            not yet received an alert for the current assessment period.
          </p>
          <button
            className="btn btn-danger"
            onClick={handleBatchSend}
            disabled={batchSending}
            style={{ width: '100%' }}
          >
            {batchSending ? (
              <>
                <Loader2 size={14} className="spin" /> Processing...
              </>
            ) : (
              <>
                <Users size={14} /> Send to All Pending
              </>
            )}
          </button>
          <p style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 12 }}>
            This will send alerts only to students who haven't been notified yet.
          </p>
        </div>
      </div>

      {/* History */}
      <div style={{ marginBottom: 16 }}>
        <h3 className="section-title">SMS History</h3>
      </div>

      <div className="glass-card-static">
        {loading ? (
          <SkeletonTable rows={8} cols={5} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadHistory} />
        ) : (
          <>
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Student ID</th>
                    <th>Message</th>
                    <th>Status</th>
                    <th>Sent At</th>
                    <th>Delivered At</th>
                  </tr>
                </thead>
                <tbody>
                  {paginated.map((alert, i) => (
                    <tr key={alert.id || i}>
                      <td>{alert.student_id}</td>
                      <td style={{ maxWidth: 300 }}>
                        <span className="truncate" style={{ display: 'block' }}>
                          {alert.message || 'Default alert template'}
                        </span>
                      </td>
                      <td>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                          {statusIcon[alert.status] || statusIcon.pending}
                          <span
                            style={{
                              textTransform: 'capitalize',
                              color:
                                alert.status === 'delivered'
                                  ? 'var(--risk-safe)'
                                  : alert.status === 'failed'
                                  ? 'var(--risk-high)'
                                  : 'var(--text-secondary)',
                            }}
                          >
                            {alert.status || 'pending'}
                          </span>
                        </span>
                      </td>
                      <td>
                        {alert.sent_at
                          ? new Date(alert.sent_at).toLocaleString('en-GB', {
                              day: 'numeric',
                              month: 'short',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '—'}
                      </td>
                      <td>
                        {alert.delivered_at
                          ? new Date(alert.delivered_at).toLocaleString('en-GB', {
                              day: 'numeric',
                              month: 'short',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '—'}
                      </td>
                    </tr>
                  ))}
                  {paginated.length === 0 && (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                        No SMS alerts sent yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="pagination">
              <span className="pagination-info">
                {history.length > 0
                  ? `Showing ${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, history.length)} of ${history.length}`
                  : '0 records'}
              </span>
              <div className="pagination-controls">
                <button className="pagination-btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  <ChevronLeft size={14} />
                </button>
                {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => (
                  <button
                    key={i + 1}
                    className={`pagination-btn ${page === i + 1 ? 'active' : ''}`}
                    onClick={() => setPage(i + 1)}
                  >
                    {i + 1}
                  </button>
                ))}
                <button className="pagination-btn" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
