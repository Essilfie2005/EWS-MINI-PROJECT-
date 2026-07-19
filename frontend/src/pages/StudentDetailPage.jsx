import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ClipboardPlus,
  AlertTriangle,
  Download,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
  LineChart,
  Line,
} from 'recharts';
import { fetchStudentDetail, createIntervention, updateIntervention, triggerSinglePrediction, fetchPredictionHistory, fetchStudentInterventions, fetchRiskTrajectory, downloadPdfBrief } from '../services/api';
import api from '../services/api';
import { SkeletonCard, SkeletonChart } from '../components/shared/Skeleton';
import ErrorState from '../components/shared/ErrorState';
import { useToast } from '../context/ToastContext';
import SmsAlertTrigger from '../components/dashboard/SmsAlertTrigger';

/* ── helpers ── */
function getRiskColor(band) {
  const b = (band || '').toLowerCase();
  if (b === 'critical') return '#dc2626';
  if (b === 'high') return '#f43f5e';
  if (b === 'medium') return '#f59e0b';
  return '#10b981';
}

function scoreToGauge(score) {
  const circumference = 2 * Math.PI * 75;
  const offset = circumference - score * circumference;
  return { circumference, offset };
}

/* ── SHAP Tooltip ── */
const ShapTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div
      style={{
        background: 'rgba(19, 27, 46, 0.95)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 8,
        padding: '10px 14px',
        fontSize: 13,
      }}
    >
      <div style={{ fontWeight: 600, color: '#f1f5f9' }}>{d.feature}</div>
      <div style={{ color: d.value >= 0 ? '#f43f5e' : '#10b981', marginTop: 2 }}>
        SHAP: {d.value >= 0 ? '+' : ''}{d.value.toFixed(4)}
      </div>
    </div>
  );
};

/* ── Intervention Modal ── */
function InterventionModal({ studentId, onClose, onSuccess }) {
  const addToast = useToast();
  const [form, setForm] = useState({
    student_id: studentId,
    date: new Date().toISOString().slice(0, 10),
    nature: '',
    outcome: '',
    notes: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await createIntervention({
        student_id: parseInt(studentId, 10),
        intervention_type: form.nature,
        description: form.notes
      });

      if (form.outcome) {
        await updateIntervention(res.data.id, {
          status: 'COMPLETED',
          outcome: form.outcome
        });
      }

      addToast('Intervention logged successfully', 'success');
      onSuccess();
      onClose();
    } catch (err) {
      addToast(err.response?.data?.detail || 'Failed to log intervention', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Log Intervention</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Date</label>
            <input
              type="date"
              className="form-input"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Nature of Intervention</label>
            <select
              className="form-select"
              value={form.nature}
              onChange={(e) => setForm({ ...form, nature: e.target.value })}
              required
            >
              <option value="">Select type...</option>
              <option value="SMS">SMS</option>
              <option value="EMAIL">Email</option>
              <option value="COUNSELLING">Counselling Session</option>
              <option value="TUTORING">Tutoring / Academic Support</option>
              <option value="OTHER">Other</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Outcome</label>
            <select
              className="form-select"
              value={form.outcome}
              onChange={(e) => setForm({ ...form, outcome: e.target.value })}
              required
            >
              <option value="">Unknown / Not yet assessed</option>
              <option value="SUCCESSFUL">✅ Successful — Student Recovered</option>
              <option value="UNSUCCESSFUL">❌ Unsuccessful — Student Did Not Respond</option>
              <option value="PENDING">⏳ Pending — Follow-up Required</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Notes</label>
            <textarea
              className="form-input form-textarea"
              placeholder="Details about the intervention..."
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving...' : 'Save Intervention'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Main Page ── */
export default function StudentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const addToast = useToast();

  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);

  const [generatingShap, setGeneratingShap] = useState(false);

  // Risk trajectory
  const [trajectory, setTrajectory] = useState(null);
  const [trajectoryLoading, setTrajectoryLoading] = useState(false);
  const [trajectoryUnavailable, setTrajectoryUnavailable] = useState(false);

  // V3 — 4-week forecast
  const [forecast, setForecast] = useState(null);

  // Outcome updating state
  const [updatingOutcome, setUpdatingOutcome] = useState(null); // intervention id being updated

  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const handleGenerateShap = async () => {
    setGeneratingShap(true);
    try {
      await triggerSinglePrediction({ student_id: parseInt(id, 10) });
      addToast('SHAP feature explanations generated', 'success');
      await loadStudent();
    } catch (err) {
      addToast(err.response?.data?.detail || 'Failed to generate explanations', 'error');
    } finally {
      setGeneratingShap(false);
    }
  };

  const loadStudent = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [studentRes, historyRes, interventionsRes] = await Promise.all([
        fetchStudentDetail(id),
        fetchPredictionHistory(id).catch(() => ({ data: { predictions: [] } })),
        fetchStudentInterventions(id).catch(() => ({ data: { interventions: [] } }))
      ]);

      const studentData = studentRes.data;
      
      // Get latest prediction SHAP values
      const predictions = historyRes.data?.predictions || [];
      const latestPredictionWithShap = predictions.find(p => p.shap_values && p.shap_values.length > 0);
      studentData.shap_values = latestPredictionWithShap ? latestPredictionWithShap.shap_values : null;
      
      // Attach interventions
      studentData.interventions = interventionsRes.data?.interventions || [];

      setStudent(studentData);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load student');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadStudent();
  }, [loadStudent]);

  // Load risk trajectory independently (soft failure)
  useEffect(() => {
    if (!id) return;
    setTrajectoryLoading(true);
    setTrajectoryUnavailable(false);
    fetchRiskTrajectory(id)
      .then((res) => {
        const pts = Array.isArray(res.data) ? res.data : res.data?.points;
        setTrajectory(pts || null);
      })
      .catch(() => {
        setTrajectoryUnavailable(true);
      })
      .finally(() => setTrajectoryLoading(false));
  }, [id]);

  // V3 — Load 4-week forecast
  useEffect(() => {
    if (!id) return;
    api.get(`/predictions/forecast/${id}`)
      .then(res => setForecast(res.data))
      .catch(() => {});
  }, [id]);

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      const res = await downloadPdfBrief(id);
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `risk_brief_${id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      addToast('PDF downloaded successfully', 'success');
    } catch (err) {
      addToast('PDF export not yet available', 'warning');
    } finally {
      setDownloadingPdf(false);
    }
  };



  if (loading) {
    return (
      <div className="fade-in">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/students')}>
            <ArrowLeft size={16} /> Back
          </button>
        </div>
        <div className="student-detail-grid">
          <div className="left-col">
            <SkeletonCard height={220} />
            <SkeletonCard height={220} />
          </div>
          <div className="right-col">
            <SkeletonChart height={300} />
            <SkeletonCard height={200} />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fade-in">
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/students')} style={{ marginBottom: 24 }}>
          <ArrowLeft size={16} /> Back
        </button>
        <div className="glass-card">
          <ErrorState message={error} onRetry={loadStudent} />
        </div>
      </div>
    );
  }

  if (!student) return null;

  const riskScore = student.risk_score ?? 0;
  const riskBand = student.risk_band || 'low';
  const riskColor = getRiskColor(riskBand);
  const { circumference, offset } = scoreToGauge(riskScore);

  // Feature data for progress bars
  const features = [
    { label: 'Attendance', key: 'attendance_rate', color: '#06b6d4' },
    { label: 'Quiz Average', key: 'quiz_average', color: '#8b5cf6' },
    { label: 'Assignment Rate', key: 'assignment_submission_rate', color: '#f59e0b' },
    { label: 'Engagement', key: 'mobile_engagement_freq', color: '#f43f5e' },
    { label: 'Financial Aid (IMD)', key: 'financial_aid_status', color: '#10b981', max: 10 },
  ];

  // SHAP values
  const shapData = (student.shap_values || [])
    .map((s) => ({
      feature: s.feature,
      value: s.contribution, // this is the actual SHAP impact score
      rawValue: s.value,
    }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  // Interventions timeline
  const interventions = student.interventions || [];

  return (
    <div className="fade-in">
      {/* Top bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/students')}>
          <ArrowLeft size={16} /> Back to Students
        </button>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-secondary btn-sm" onClick={() => setShowModal(true)}>
            <ClipboardPlus size={14} /> Log Intervention
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            title="Download Risk Brief PDF"
          >
            <Download size={14} /> {downloadingPdf ? 'Downloading...' : 'Download Risk Brief'}
          </button>
          {(student?.risk_band === 'high' || student?.risk_band === 'critical') && (
            <SmsAlertTrigger
              studentId={id}
              studentData={student}
              onSent={loadStudent}
            />
          )}
        </div>
      </div>

      <div className="student-detail-grid">
        {/* Left Column */}
        <div className="left-col">
          {/* Risk Gauge */}
          <div className="glass-card slide-up" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <h3 className="section-title" style={{ alignSelf: 'flex-start', marginBottom: 20 }}>Risk Score</h3>
            <div className="gauge-ring">
              <svg viewBox="0 0 180 180">
                <circle cx="90" cy="90" r="75" className="bg" />
                <circle
                  cx="90"
                  cy="90"
                  r="75"
                  className="progress"
                  style={{
                    stroke: riskColor,
                    strokeDasharray: circumference,
                    strokeDashoffset: offset,
                  }}
                />
              </svg>
              <div className="gauge-value">
                <div className="score" style={{ color: riskColor }}>
                  {(riskScore * 100).toFixed(0)}%
                </div>
                <div className="label">Dropout Risk</div>
              </div>
            </div>
            <div style={{ marginTop: 16 }}>
              <span className={`risk-badge ${riskBand.toLowerCase()}`}>
                {riskBand.charAt(0).toUpperCase() + riskBand.slice(1)} Risk
              </span>
            </div>
          </div>

          {/* Student Features */}
          <div className="glass-card slide-up stagger-2">
            <h3 className="section-title" style={{ marginBottom: 20 }}>
              Student Profile — {student.student_id}
            </h3>
            <div className="feature-bars">
              {features.map((f) => {
                const rawVal = student[f.key];
                if (rawVal == null) return null;
                const max = f.max || 100;
                const pct = Math.min((rawVal / max) * 100, 100);
                const displayVal = f.max ? rawVal.toFixed(2) : `${Number(rawVal).toFixed(1)}%`;
                return (
                  <div key={f.key} className="progress-bar-wrapper">
                    <div className="progress-bar-header">
                      <span className="label">{f.label}</span>
                      <span className="value">{displayVal}</span>
                    </div>
                    <div className="progress-bar-track">
                      <div
                        className="progress-bar-fill"
                        style={{ width: `${pct}%`, background: f.color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="right-col">
          {/* Risk Trajectory Chart */}
          {!trajectoryUnavailable && (
            <div className="glass-card slide-up" style={{ marginBottom: 0 }}>
              <div className="section-header" style={{ marginBottom: 16 }}>
                <div>
                  <h3 className="section-title">Risk Score Trajectory</h3>
                  <p className="section-subtitle">Weekly dropout risk progression</p>
                </div>
                {trajectory && trajectory.length >= 2 && (() => {
                  const trending = trajectory[trajectory.length - 1].risk > trajectory[0].risk;
                  return (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: trending ? '#f43f5e' : '#10b981' }}>
                      {trending ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                      {trending ? 'Trending Up' : 'Trending Down'}
                    </div>
                  );
                })()}
              </div>
              {trajectoryLoading ? (
                <div style={{ height: 200, borderRadius: 8, background: 'rgba(255,255,255,0.03)', animation: 'pulse 1.5s infinite' }} />
              ) : trajectory?.length ? (() => {
                const trending = trajectory.length >= 2 && trajectory[trajectory.length - 1].risk > trajectory[0].risk;
                const lineColor = trending ? '#f43f5e' : '#10b981';
                return (
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={trajectory} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis
                        dataKey="week"
                        tick={{ fontSize: 12, fill: '#64748b' }}
                        axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                        tickLine={false}
                      />
                      <YAxis
                        domain={[0, 1]}
                        tickFormatter={(v) => `${Math.round(v * 100)}%`}
                        tick={{ fontSize: 12, fill: '#64748b' }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        formatter={(v) => [`${(v * 100).toFixed(1)}%`, 'Risk Score']}
                        contentStyle={{
                          background: 'rgba(19,27,46,0.95)',
                          border: '1px solid rgba(255,255,255,0.1)',
                          borderRadius: 8,
                          fontSize: 13,
                        }}
                      />
                      <ReferenceLine y={0.5} stroke="rgba(245,158,11,0.6)" strokeDasharray="4 4" label={{ value: 'Risk Threshold', position: 'insideTopRight', fontSize: 11, fill: '#f59e0b' }} />
                      <Line
                        type="monotone"
                        dataKey="risk"
                        stroke={lineColor}
                        strokeWidth={2.5}
                        dot={{ fill: lineColor, r: 4, strokeWidth: 0 }}
                        activeDot={{ r: 6 }}
                        animationDuration={800}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                );
              })() : (
                <div style={{ color: 'var(--text-dim)', fontSize: 13, padding: '32px 0', textAlign: 'center' }}>
                  No trajectory data for this student
                </div>
              )}
            </div>
          )}

          {/* SHAP Waterfall Chart */}
          <div className="glass-card slide-up stagger-1">
            <div className="section-header">
              <div>
                <h3 className="section-title">SHAP Feature Contributions</h3>
                <p className="section-subtitle">
                  How each feature affects dropout risk prediction
                </p>
              </div>
            </div>
            {shapData.length > 0 ? (
              <div style={{ width: '100%', height: Math.max(shapData.length * 44, 200) }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={shapData}
                    layout="vertical"
                    margin={{ top: 5, right: 40, left: 10, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 12, fill: '#64748b' }}
                      axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                      tickLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="feature"
                      tick={{ fontSize: 12, fill: '#94a3b8' }}
                      axisLine={false}
                      tickLine={false}
                      width={130}
                    />
                    <Tooltip content={<ShapTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                    <ReferenceLine x={0} stroke="rgba(255,255,255,0.15)" />
                    <Bar dataKey="value" animationDuration={800} radius={[4, 4, 4, 4]}>
                      {shapData.map((entry, index) => (
                        <Cell
                          key={index}
                          fill={entry.value >= 0 ? '#f43f5e' : '#10b981'}
                          fillOpacity={0.85}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="empty-state" style={{ padding: '32px 16px' }}>
                <AlertTriangle style={{ width: 32, height: 32, color: 'var(--text-dim)', marginBottom: 8 }} />
                <p className="title" style={{ fontSize: 14 }}>No SHAP data available</p>
                <p className="description" style={{ marginBottom: 16 }}>Generate AI feature explanations for this student to see what factors are driving their risk score.</p>
                <button 
                  className="btn btn-primary btn-sm" 
                  onClick={handleGenerateShap}
                  disabled={generatingShap}
                >
                  {generatingShap ? 'Generating...' : 'Generate Explanations'}
                </button>
              </div>
            )}
          </div>

          {/* Intervention Timeline */}
          <div className="glass-card slide-up stagger-3">
            <h3 className="section-title" style={{ marginBottom: 16 }}>Intervention Timeline</h3>
            {interventions.length > 0 ? (
              <div className="timeline">
                {interventions.map((item, i) => {
                  const outcomeMap = {
                    SUCCESSFUL:   { label: 'Successful',   color: '#10b981', bg: 'rgba(16,185,129,0.12)' },
                    UNSUCCESSFUL: { label: 'Unsuccessful', color: '#f43f5e', bg: 'rgba(244,63,94,0.12)' },
                    PENDING:      { label: 'Pending',      color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
                    positive:     { label: 'Successful',   color: '#10b981', bg: 'rgba(16,185,129,0.12)' },
                    negative:     { label: 'Unsuccessful', color: '#f43f5e', bg: 'rgba(244,63,94,0.12)' },
                    neutral:      { label: 'Pending',      color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
                  };
                  const oc = outcomeMap[item.outcome] || null;
                  const isUpdating = updatingOutcome === (item.id || i);

                  const handleOutcomeUpdate = async (newOutcome) => {
                    if (!item.id) return;
                    setUpdatingOutcome(item.id);
                    try {
                      await updateIntervention(item.id, { status: 'COMPLETED', outcome: newOutcome });
                      addToast(`Outcome marked as ${newOutcome}`, 'success');
                      await loadStudent();
                    } catch {
                      addToast('Failed to update outcome', 'error');
                    } finally {
                      setUpdatingOutcome(null);
                    }
                  };

                  return (
                    <div className="timeline-item" key={item.id || i} style={{ paddingBottom: 20 }}>
                      <div className="timeline-date">
                        {item.created_at
                          ? new Date(item.created_at).toLocaleDateString('en-GB', {
                              day: 'numeric', month: 'short', year: 'numeric',
                            })
                          : item.date
                            ? new Date(item.date).toLocaleDateString('en-GB', {
                                day: 'numeric', month: 'short', year: 'numeric',
                              })
                            : '—'}
                      </div>
                      <div className="timeline-title">
                        {(item.intervention_type || item.nature || 'Intervention')
                          .replace(/_/g, ' ')
                          .replace(/\b\w/g, (c) => c.toUpperCase())}
                      </div>

                      {/* Description */}
                      {(item.description || item.notes) && (
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                          {item.description || item.notes}
                        </div>
                      )}

                      {/* Current outcome badge */}
                      <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                        {oc ? (
                          <span style={{
                            background: oc.bg, color: oc.color,
                            border: `1px solid ${oc.color}44`,
                            borderRadius: 8, padding: '3px 10px',
                            fontSize: 12, fontWeight: 700,
                          }}>
                            {oc.label}
                          </span>
                        ) : (
                          <span style={{
                            background: 'rgba(148,163,184,0.12)', color: '#94a3b8',
                            border: '1px solid rgba(148,163,184,0.2)',
                            borderRadius: 8, padding: '3px 10px',
                            fontSize: 12, fontWeight: 600,
                          }}>No outcome yet</span>
                        )}

                        {/* Inline update buttons — always visible */}
                        {isUpdating ? (
                          <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>Saving…</span>
                        ) : (
                          <div style={{ display: 'flex', gap: 6 }}>
                            {[
                              { val: 'SUCCESSFUL',   label: '✅ Successful',   color: '#10b981' },
                              { val: 'UNSUCCESSFUL', label: '❌ Unsuccessful', color: '#f43f5e' },
                              { val: 'PENDING',      label: '⏳ Pending',      color: '#f59e0b' },
                            ].map(({ val, label, color }) => (
                              <button
                                key={val}
                                onClick={() => handleOutcomeUpdate(val)}
                                disabled={item.outcome === val}
                                style={{
                                  background: item.outcome === val ? color + '22' : 'transparent',
                                  color: item.outcome === val ? color : 'var(--text-dim)',
                                  border: `1px solid ${item.outcome === val ? color + '55' : 'rgba(255,255,255,0.1)'}`,
                                  borderRadius: 6, padding: '3px 9px',
                                  fontSize: 11, fontWeight: 600,
                                  cursor: item.outcome === val ? 'default' : 'pointer',
                                  transition: 'all 0.2s',
                                }}
                                onMouseEnter={e => { if (item.outcome !== val) e.target.style.borderColor = color + '88'; }}
                                onMouseLeave={e => { if (item.outcome !== val) e.target.style.borderColor = 'rgba(255,255,255,0.1)'; }}
                              >
                                {label}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state" style={{ padding: '24px 16px' }}>
                <ClipboardPlus style={{ width: 32, height: 32, color: 'var(--text-dim)', marginBottom: 8 }} />
                <p className="title" style={{ fontSize: 14 }}>No interventions yet</p>
                <p className="description">Log an intervention using the button above.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <InterventionModal
          studentId={id}
          onClose={() => setShowModal(false)}
          onSuccess={loadStudent}
        />
      )}

      {/* V3 — 4-Week Risk Forecast */}
      {forecast && (
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--bg-card-border)',
          borderRadius: 16, padding: 24, marginTop: 24,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              📡 4-Week Risk Forecast (Prophet)
            </h3>
            {forecast.trend && (
              <span style={{
                background: forecast.trend.color + '22',
                color: forecast.trend.color,
                border: `1px solid ${forecast.trend.color}44`,
                borderRadius: 8, padding: '4px 12px',
                fontSize: 12, fontWeight: 700,
              }}>
                {forecast.trend.label.replace(/_/g, ' ')}
              </span>
            )}
          </div>
          {forecast.trend && (
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
              {forecast.trend.description}
            </p>
          )}
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={forecast.combined || []} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="week" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis domain={[0, 1]} tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={v => v.toFixed(1)} />
              <Tooltip
                contentStyle={{ background: '#1a2340', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
                formatter={(v, name, props) => [
                  v?.toFixed(4),
                  props.payload?.type === 'forecast' ? '🔮 Forecast' : '📊 Historical'
                ]}
              />
              <ReferenceLine y={forecast.youden_threshold || 0.4432} stroke="#f59e0b" strokeDasharray="4 4"
                label={{ value: 'Risk threshold', position: 'right', fill: '#f59e0b', fontSize: 10 }} />
              <Line
                type="monotone" dataKey="risk_score"
                stroke="#6366f1" strokeWidth={2.5}
                dot={(props) => {
                  const { cx, cy, payload } = props;
                  return (
                    <circle key={payload.week} cx={cx} cy={cy} r={4}
                      fill={payload.type === 'forecast' ? '#f59e0b' : '#6366f1'}
                      stroke="none" />
                  );
                }}
                strokeDasharray={(d) => d?.type === 'forecast' ? '6 3' : undefined}
              />
            </LineChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 11, color: 'var(--text-dim)' }}>
            <span>🟣 Historical ({forecast.history_weeks} weeks)</span>
            <span>🟡 Forecast ({forecast.forecast_weeks} weeks)</span>
            <span>Method: {forecast.method}</span>
            {forecast.synthetic_history && <span style={{ color: '#f59e0b' }}>⚠ Synthetic history (insufficient real data)</span>}
          </div>
        </div>
      )}
    </div>
  );
}
