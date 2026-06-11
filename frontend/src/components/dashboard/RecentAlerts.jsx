import { Clock } from 'lucide-react';
import { SkeletonChart } from '../shared/Skeleton';

export default function RecentAlerts({ data, loading }) {
  if (loading)
    return (
      <div className="glass-card">
        <div className="section-header">
          <h3 className="section-title">Recent Alerts</h3>
        </div>
        <SkeletonChart height={200} />
      </div>
    );

  const alertList = Array.isArray(data) ? data : data?.alerts || [];

  if (!alertList.length)
    return (
      <div className="glass-card">
        <div className="section-header">
          <h3 className="section-title">Recent Alerts</h3>
        </div>
        <div className="empty-state" style={{ padding: '32px 16px' }}>
          <Clock style={{ width: 32, height: 32, color: 'var(--text-dim)', marginBottom: 8 }} />
          <p className="title" style={{ fontSize: 14 }}>No recent alerts</p>
          <p className="description">SMS alerts will appear here after being sent.</p>
        </div>
      </div>
    );

  return (
    <div className="glass-card slide-up">
      <div className="section-header">
        <h3 className="section-title">Recent Alerts</h3>
      </div>
      <div style={{ maxHeight: 320, overflowY: 'auto' }}>
        {alertList.map((alert, i) => (
          <div className="alert-item" key={alert.id || i}>
            <div className={`alert-dot ${alert.risk_band || 'high'}`} />
            <div className="alert-content">
              <div className="alert-text">{alert.message || `Alert sent to ${alert.student_id}`}</div>
              <div className="alert-time">
                {alert.sent_at
                  ? new Date(alert.sent_at).toLocaleString()
                  : 'Just now'}
                {alert.status && (
                  <span
                    style={{
                      marginLeft: 8,
                      color:
                        alert.status === 'delivered'
                          ? 'var(--risk-safe)'
                          : alert.status === 'failed'
                          ? 'var(--risk-high)'
                          : 'var(--text-muted)',
                    }}
                  >
                    • {alert.status}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
