import useApi from '../hooks/useApi';
import {
  fetchDashboardOverview,
  fetchRiskDistribution,
  fetchRecentAlerts,
  fetchFeatureImportance,
} from '../services/api';
import MetricsCards from '../components/dashboard/MetricsCards';
import RiskDistribution from '../components/dashboard/RiskDistribution';
import CohortOverview from '../components/dashboard/CohortOverview';
import RiskHeatMap from '../components/dashboard/RiskHeatMap';
import RecentAlerts from '../components/dashboard/RecentAlerts';

export default function DashboardPage() {
  const overview = useApi(fetchDashboardOverview);
  const distribution = useApi(fetchRiskDistribution);
  const alerts = useApi(fetchRecentAlerts);
  const importance = useApi(fetchFeatureImportance);

  // Map backend response to MetricsCards shape
  const metricsData = overview.data
    ? {
        total_students: overview.data.total_students,
        at_risk_count: overview.data.flagged_students,
        at_risk_pct:
          overview.data.total_students > 0
            ? (overview.data.flagged_students / overview.data.total_students) * 100
            : 0,
        intervention_rate: overview.data.dropout_rate,
        model_auc: overview.data.average_risk_score,
      }
    : null;

  return (
    <div className="fade-in">
      <MetricsCards data={metricsData} loading={overview.loading} />

      <div className="dashboard-grid">
        <RiskDistribution
          data={distribution.data}
          loading={distribution.loading}
          error={distribution.error}
          onRetry={distribution.refetch}
        />
        <CohortOverview
          data={importance.data}
          loading={importance.loading}
          error={importance.error}
          onRetry={importance.refetch}
        />
      </div>

      <RiskHeatMap
        data={overview.data}
        loading={overview.loading}
        error={overview.error}
        onRetry={overview.refetch}
      />

      <div style={{ marginTop: 24 }}>
        <RecentAlerts data={alerts.data} loading={alerts.loading} />
      </div>
    </div>
  );
}
