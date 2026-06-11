import { useNavigate } from 'react-router-dom';
import { SkeletonChart } from '../shared/Skeleton';
import ErrorState from '../shared/ErrorState';

function getRiskClass(score) {
  if (score >= 0.8) return 'critical';
  if (score >= 0.6) return 'high';
  if (score >= 0.4) return 'medium';
  return 'low';
}

export default function RiskHeatMap({ data, loading, error, onRetry }) {
  const navigate = useNavigate();

  if (loading)
    return (
      <div className="glass-card">
        <div className="section-header">
          <div>
            <h3 className="section-title">Student Risk Heatmap</h3>
            <p className="section-subtitle">Each cell represents a student — click to view details</p>
          </div>
        </div>
        <SkeletonChart height={200} />
      </div>
    );

  if (error)
    return (
      <div className="glass-card">
        <ErrorState message={error} onRetry={onRetry} />
      </div>
    );

  if (!data || !data.length) return null;

  return (
    <div className="glass-card slide-up">
      <div className="section-header">
        <div>
          <h3 className="section-title">Student Risk Heatmap</h3>
          <p className="section-subtitle">
            Each cell represents a student — click to view details
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12, fontSize: 12, color: 'var(--text-muted)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: '#10b981' }} /> Low
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: '#f59e0b' }} /> Medium
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: '#f43f5e' }} /> High
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: '#dc2626' }} /> Critical
          </span>
        </div>
      </div>
      <div className="heatmap-grid">
        {data.map((student) => {
          const riskClass = student.risk_band || getRiskClass(student.risk_score);
          return (
            <div
              key={student.student_id}
              className={`heatmap-cell ${riskClass}`}
              title={`${student.student_id}: ${(student.risk_score * 100).toFixed(0)}%`}
              onClick={() => navigate(`/students/${student.student_id}`)}
            />
          );
        })}
      </div>
    </div>
  );
}
