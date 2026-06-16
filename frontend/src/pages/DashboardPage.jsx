import useApi from '../hooks/useApi';
import { useNavigate } from 'react-router-dom';
import {
  fetchDashboardOverview,
  fetchRiskDistribution,
  fetchFeatureImportance,
  fetchHeatmapData,
  fetchAlerts,
} from '../services/api';
import MetricsCards from '../components/dashboard/MetricsCards';
import RiskDistribution from '../components/dashboard/RiskDistribution';
import CohortOverview from '../components/dashboard/CohortOverview';
import RiskHeatMap from '../components/dashboard/RiskHeatMap';
import RecentAlerts from '../components/dashboard/RecentAlerts';
import { Upload, ArrowRight } from 'lucide-react';

// ── 30 synthetic demo students (proposal Section E2 demo requirement) ──────
function generateDemoStudents() {
  const bands = ['low', 'low', 'low', 'medium', 'medium', 'medium', 'high', 'high', 'critical'];
  return Array.from({ length: 30 }, (_, i) => {
    const band = bands[i % bands.length];
    const score =
      band === 'critical' ? 0.82 + Math.random() * 0.15 :
      band === 'high'     ? 0.61 + Math.random() * 0.18 :
      band === 'medium'   ? 0.41 + Math.random() * 0.18 :
                            0.10 + Math.random() * 0.28;
    return {
      student_id: `A-${String(i + 1).padStart(3, '0')}`,
      id: i + 1,
      risk_score: parseFloat(score.toFixed(3)),
      risk_band: band,
      attendance_rate: band === 'critical' ? 38 + Math.random() * 10 :
                       band === 'high'     ? 48 + Math.random() * 12 :
                       band === 'medium'   ? 62 + Math.random() * 15 :
                                            75 + Math.random() * 20,
      quiz_average:    band === 'critical' ? 28 + Math.random() * 10 :
                       band === 'high'     ? 38 + Math.random() * 12 :
                       band === 'medium'   ? 52 + Math.random() * 15 :
                                            68 + Math.random() * 20,
    };
  });
}

const DEMO_STUDENTS = generateDemoStudents();

const DEMO_OVERVIEW = {
  total_students: 30,
  flagged_students: DEMO_STUDENTS.filter(s => s.risk_band === 'high' || s.risk_band === 'critical').length,
  dropout_rate: 23.3,
  average_risk_score: parseFloat(
    (DEMO_STUDENTS.reduce((s, d) => s + d.risk_score, 0) / DEMO_STUDENTS.length).toFixed(3)
  ),
};

const DEMO_DISTRIBUTION = [
  { band: 'low',      count: DEMO_STUDENTS.filter(s => s.risk_band === 'low').length },
  { band: 'medium',   count: DEMO_STUDENTS.filter(s => s.risk_band === 'medium').length },
  { band: 'high',     count: DEMO_STUDENTS.filter(s => s.risk_band === 'high').length },
  { band: 'critical', count: DEMO_STUDENTS.filter(s => s.risk_band === 'critical').length },
];

const DEMO_IMPORTANCE = [
  { period: 'Attendance Rate',        importance: 0.4821 },
  { period: 'Quiz Average',           importance: 0.3104 },
  { period: 'Assignment Submission',  importance: 0.1233 },
  { period: 'Mobile Engagement',      importance: 0.0612 },
  { period: 'Financial Aid',          importance: 0.0230 },
];

const DEMO_ALERTS = [
  { id: 1, student_id: 'A-003', message: 'Student A-003 flagged HIGH RISK. Attendance 42%, Quiz Avg 31%. Please contact within 5 days.', sent_at: new Date(Date.now() - 3600000).toISOString(), status: 'delivered', risk_band: 'critical' },
  { id: 2, student_id: 'A-007', message: 'Student A-007 flagged HIGH RISK. Attendance 51%, Quiz Avg 38%. Please contact within 5 days.', sent_at: new Date(Date.now() - 7200000).toISOString(), status: 'delivered', risk_band: 'high' },
  { id: 3, student_id: 'A-016', message: 'Student A-016 flagged HIGH RISK. Attendance 47%, Quiz Avg 33%. Please contact within 5 days.', sent_at: new Date(Date.now() - 86400000).toISOString(), status: 'pending', risk_band: 'high' },
];

function EmptyDashboard() {
  const navigate = useNavigate();
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', minHeight: '60vh', gap: 24, textAlign: 'center',
    }}>
      <div style={{
        width: 72, height: 72, borderRadius: 20, background: 'var(--accent-bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Upload size={32} style={{ color: 'var(--accent)' }} />
      </div>
      <div>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
          No cohort data yet
        </h2>
        <p style={{ fontSize: 14, color: 'var(--text-muted)', maxWidth: 420, lineHeight: 1.7 }}>
          Upload your Week 6 foundation-year student data to run the batch dropout risk assessment.
        </p>
      </div>
      <button className="btn btn-primary" onClick={() => navigate('/settings')}>
        <Upload size={16} /> Upload Cohort Data <ArrowRight size={14} />
      </button>
      <div style={{
        background: 'var(--glass-bg)', border: '1px solid var(--glass-border)',
        borderRadius: 12, padding: '16px 24px', fontSize: 13,
        color: 'var(--text-secondary)', maxWidth: 480, lineHeight: 1.8,
      }}>
        <strong style={{ color: 'var(--text-primary)' }}>Expected columns:</strong><br />
        student_id · index_number · mid_sem_result (out of 30)<br />
        <span style={{ color: 'var(--text-muted)' }}>Optional: attendance_rate · end_sem_result (out of 70)</span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const overview    = useApi(fetchDashboardOverview);
  const distribution = useApi(fetchRiskDistribution);
  const importance  = useApi(fetchFeatureImportance);
  const heatmap     = useApi(fetchHeatmapData);
  const alerts      = useApi(fetchAlerts);

  const isLoading = overview.loading;
  const apiDown   = !isLoading && overview.error;
  const noData    = !isLoading && !overview.error && overview.data?.total_students === 0;

  // ── fall back to demo data when backend is unreachable ──────────────────
  const metricsData = overview.data
    ? {
        total_students:    overview.data.total_students,
        at_risk_count:     overview.data.flagged_students,
        at_risk_pct:
          overview.data.total_students > 0
            ? (overview.data.flagged_students / overview.data.total_students) * 100
            : 0,
        dropout_rate:      overview.data.dropout_rate,
        average_risk_score: overview.data.average_risk_score,
      }
    : apiDown
    ? {
        total_students:    DEMO_OVERVIEW.total_students,
        at_risk_count:     DEMO_OVERVIEW.flagged_students,
        at_risk_pct:       (DEMO_OVERVIEW.flagged_students / DEMO_OVERVIEW.total_students) * 100,
        dropout_rate:      DEMO_OVERVIEW.dropout_rate,
        average_risk_score: DEMO_OVERVIEW.average_risk_score,
      }
    : null;

  const distributionData = distribution.data?.risk_distribution
    ? Object.entries(distribution.data.risk_distribution).map(([band, info]) => ({
        band: band.toLowerCase(), count: info.count,
      }))
    : distribution.data || (apiDown ? DEMO_DISTRIBUTION : null);

  const importanceData = importance.data?.feature_importance
    ? Object.entries(importance.data.feature_importance).map(([feature, score]) => ({
        period: feature.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        importance: score,
      }))
    : importance.data || (apiDown ? DEMO_IMPORTANCE : null);

  const heatmapData = heatmap.data?.items || heatmap.data || (apiDown ? DEMO_STUDENTS : null);
  const alertsData  = alerts.data || (apiDown ? DEMO_ALERTS : null);

  // Show empty upload prompt only when backend is live but has no data yet
  if (noData) return <EmptyDashboard />;

  return (
    <div className="fade-in">
      {apiDown && (
        <div style={{
          background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.25)',
          borderRadius: 10, padding: '10px 16px', marginBottom: 20,
          fontSize: 13, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          ⚠ Backend offline — showing demo data with 30 synthetic students
        </div>
      )}

      {/* 1. Metrics cards */}
      <MetricsCards data={metricsData} loading={isLoading} />

      {/* 2. Risk distribution + Feature importance */}
      <div className="dashboard-grid">
        <RiskDistribution
          data={distributionData}
          loading={isLoading && !apiDown}
          error={!apiDown ? distribution.error : null}
          onRetry={distribution.refetch}
        />
        <CohortOverview
          data={importanceData}
          loading={isLoading && !apiDown}
          error={!apiDown ? importance.error : null}
          onRetry={importance.refetch}
        />
      </div>

      {/* 3. Risk heatmap (30 colour-coded student cells) + Recent alerts */}
      <div className="dashboard-grid" style={{ marginBottom: 24 }}>
        <RiskHeatMap
          data={heatmapData}
          loading={isLoading && !apiDown}
          error={!apiDown ? heatmap.error : null}
          onRetry={heatmap.refetch}
        />
        <RecentAlerts
          data={alertsData}
          loading={isLoading && !apiDown}
          onAlertSent={alerts.refetch}
        />
      </div>
    </div>
  );
}
