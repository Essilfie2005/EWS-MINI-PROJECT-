import { Users, UserX, HeartHandshake, BrainCircuit, TrendingUp, TrendingDown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { SkeletonMetrics } from '../shared/Skeleton';

export default function MetricsCards({ data, loading }) {
  const navigate = useNavigate();

  if (loading) return <SkeletonMetrics />;
  if (!data) return null;

  const cards = [
    {
      label: 'Total Students',
      value: data.total_students?.toLocaleString() ?? '—',
      trend: data.total_students_trend,
      icon: Users,
      color: 'accent',
      path: '/students',
    },
    {
      label: 'At-Risk Students',
      value: data.at_risk_count?.toLocaleString() ?? '—',
      subtitle: data.at_risk_pct != null ? `${data.at_risk_pct.toFixed(1)}% of total` : '',
      trend: data.at_risk_trend,
      icon: UserX,
      color: 'danger',
      path: '/students',
    },
    {
      label: 'Dropout Rate',
      value: data.dropout_rate != null ? `${data.dropout_rate.toFixed(1)}%` : '—',
      trend: data.dropout_rate_trend,
      icon: HeartHandshake,
      color: 'warning',
      path: '/interventions',
    },
    {
      label: 'Average Risk Score',
      value: data.average_risk_score != null ? data.average_risk_score.toFixed(3) : '—',
      trend: data.average_risk_score_trend,
      icon: BrainCircuit,
      color: 'success',
      path: '/settings',
    },
  ];

  return (
    <div className="metrics-grid">
      {cards.map((card, i) => {
        const Icon = card.icon;
        const trendUp = card.trend > 0;
        const hasTrend = card.trend != null && card.trend !== 0;

        return (
          <div 
            key={i} 
            className={`metric-card ${card.color} slide-up stagger-${i + 1}`}
            onClick={() => navigate(card.path)}
            style={{ cursor: 'pointer', transition: 'transform 0.2s, box-shadow 0.2s' }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 8px 16px rgba(0,0,0,0.2)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'none';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <div className="metric-info">
              <span className="metric-label">{card.label}</span>
              <span className="metric-value">{card.value}</span>
              {card.subtitle && (
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{card.subtitle}</span>
              )}
              {hasTrend && (
                <span className={`metric-trend ${trendUp ? 'up' : 'down'}`}>
                  {trendUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                  {Math.abs(card.trend).toFixed(1)}%
                </span>
              )}
            </div>
            <div className={`metric-icon ${card.color}`}>
              <Icon size={22} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
