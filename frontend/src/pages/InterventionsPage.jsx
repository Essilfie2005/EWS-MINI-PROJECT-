import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  HandHelping,
  TrendingUp,
  Calendar,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { fetchInterventions } from '../services/api';
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

    // Count interventions with a positive/successful outcome
    const positive = interventions.filter(i =>
      i.outcome === 'SUCCESSFUL' || i.outcome === 'positive'
    ).length;
    // Only compute rate against interventions that have an outcome recorded
    const withOutcome = interventions.filter(i => i.outcome && i.outcome !== '').length;
    const conversion_rate = withOutcome > 0 ? (positive / withOutcome) * 100 : null;

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
        <span style={{ fontSize: 13, color: 'var(--text-dim)' }}>Log interventions from a student's detail page</span>
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


    </div>
  );
}
