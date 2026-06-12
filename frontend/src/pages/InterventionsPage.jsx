import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Plus,
  X,
  HandHelping,
  TrendingUp,
  Calendar,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { fetchInterventions, createIntervention } from '../services/api';
import { SkeletonTable, SkeletonCard } from '../components/shared/Skeleton';
import ErrorState from '../components/shared/ErrorState';
import { useToast } from '../context/ToastContext';

const PAGE_SIZE = 15;

export default function InterventionsPage() {
  const addToast = useToast();

  // Data
  const [interventions, setInterventions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);

  // Modal
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    student_id: '',
    date: new Date().toISOString().slice(0, 10),
    nature: '',
    outcome: '',
    notes: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const loadInterventions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchInterventions();
      setInterventions(Array.isArray(res.data) ? res.data : res.data?.interventions || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load interventions');
    } finally {
      setLoading(false);
    }
  }, []);

  const computedStats = useMemo(() => {
    if (!interventions || interventions.length === 0) return null;
    const now = new Date();
    const thisMonth = interventions.filter(i => {
      if (!i.created_at) return false;
      const d = new Date(i.created_at);
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
    }).length;
    
    const positive = interventions.filter(i => i.outcome === 'positive').length;
    const conversion_rate = (positive / interventions.length) * 100;
    
    return {
      total_interventions: interventions.length,
      conversion_rate,
      this_month: thisMonth
    };
  }, [interventions]);

  useEffect(() => {
    loadInterventions();
  }, [loadInterventions]);

  const totalPages = Math.max(1, Math.ceil(interventions.length / PAGE_SIZE));
  const paginated = interventions.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.student_id || !form.nature || !form.outcome) {
      addToast('Please fill all required fields', 'error');
      return;
    }
    setSubmitting(true);
    try {
      await createIntervention(form);
      addToast('Intervention logged successfully', 'success');
      setShowModal(false);
      setForm({ student_id: '', date: new Date().toISOString().slice(0, 10), nature: '', outcome: '', notes: '' });
      loadInterventions();
    } catch (err) {
      addToast(err.response?.data?.detail || 'Failed to log intervention', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fade-in">
      {/* Stats Row */}
      <div className="metrics-grid" style={{ marginBottom: 24 }}>
        {loading ? (
          <>
            <SkeletonCard height={90} />
            <SkeletonCard height={90} />
            <SkeletonCard height={90} />
          </>
        ) : computedStats ? (
          <>
            <div className="metric-card accent slide-up stagger-1">
              <div className="metric-info">
                <span className="metric-label">Total Interventions</span>
                <span className="metric-value">{computedStats.total_interventions}</span>
              </div>
              <div className="metric-icon accent"><HandHelping size={22} /></div>
            </div>
            <div className="metric-card success slide-up stagger-2">
              <div className="metric-info">
                <span className="metric-label">Conversion Rate</span>
                <span className="metric-value">
                  {computedStats.conversion_rate != null ? `${computedStats.conversion_rate.toFixed(1)}%` : '—'}
                </span>
              </div>
              <div className="metric-icon success"><TrendingUp size={22} /></div>
            </div>
            <div className="metric-card warning slide-up stagger-3">
              <div className="metric-info">
                <span className="metric-label">This Month</span>
                <span className="metric-value">{computedStats.this_month}</span>
              </div>
              <div className="metric-icon warning"><Calendar size={22} /></div>
            </div>
          </>
        ) : null}
      </div>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h3 className="section-title">Intervention Log</h3>
        <button className="btn btn-primary btn-sm" onClick={() => setShowModal(true)}>
          <Plus size={14} /> Log Intervention
        </button>
      </div>

      {/* Table */}
      <div className="glass-card-static">
        {loading ? (
          <SkeletonTable rows={8} cols={6} />
        ) : error ? (
          <ErrorState message={error} onRetry={loadInterventions} />
        ) : (
          <>
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Student ID</th>
                    <th>Date</th>
                    <th>Nature</th>
                    <th>Outcome</th>
                    <th>Notes</th>
                    <th>Logged By</th>
                  </tr>
                </thead>
                <tbody>
                  {paginated.map((item, i) => (
                    <tr key={item.id || i}>
                      <td>{item.student_id}</td>
                      <td>
                        {item.created_at
                          ? new Date(item.created_at).toLocaleDateString('en-GB', {
                              day: 'numeric',
                              month: 'short',
                              year: 'numeric',
                            })
                          : '—'}
                      </td>
                      <td style={{ textTransform: 'capitalize' }}>
                        {(item.intervention_type || '').replace(/_/g, ' ')}
                      </td>
                      <td>
                        <span
                          className={`risk-badge ${
                            item.outcome === 'positive'
                              ? 'low'
                              : item.outcome === 'negative'
                              ? 'high'
                              : 'medium'
                          }`}
                        >
                          {item.outcome || '—'}
                        </span>
                      </td>
                      <td style={{ maxWidth: 260 }}>
                        <span className="truncate" style={{ display: 'block' }}>
                          {item.description || '—'}
                        </span>
                      </td>
                      <td>{item.logged_by || '—'}</td>
                    </tr>
                  ))}
                  {paginated.length === 0 && (
                    <tr>
                      <td colSpan={6} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                        No interventions logged yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="pagination">
              <span className="pagination-info">
                Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, interventions.length)} of{' '}
                {interventions.length}
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

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Log New Intervention</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Student ID *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. STU-001"
                  value={form.student_id}
                  onChange={(e) => setForm({ ...form, student_id: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Date *</label>
                <input
                  type="date"
                  className="form-input"
                  value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Nature of Intervention *</label>
                <select
                  className="form-select"
                  value={form.nature}
                  onChange={(e) => setForm({ ...form, nature: e.target.value })}
                  required
                >
                  <option value="">Select type...</option>
                  <option value="phone_call">Phone Call</option>
                  <option value="sms">SMS</option>
                  <option value="in_person">In-Person Meeting</option>
                  <option value="email">Email</option>
                  <option value="counselling">Counselling Session</option>
                  <option value="peer_mentoring">Peer Mentoring</option>
                  <option value="academic_support">Academic Support</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Outcome *</label>
                <select
                  className="form-select"
                  value={form.outcome}
                  onChange={(e) => setForm({ ...form, outcome: e.target.value })}
                  required
                >
                  <option value="">Select outcome...</option>
                  <option value="positive">Positive — Student Engaged</option>
                  <option value="neutral">Neutral — No Change</option>
                  <option value="negative">Negative — No Response</option>
                  <option value="pending">Pending Follow-up</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Notes</label>
                <textarea
                  className="form-input form-textarea"
                  placeholder="Additional details..."
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Saving...' : 'Save Intervention'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
