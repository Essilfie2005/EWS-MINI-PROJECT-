import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';
import { SkeletonChart } from '../shared/Skeleton';
import ErrorState from '../shared/ErrorState';

const RISK_COLORS = {
  low: '#10b981',
  medium: '#f59e0b',
  high: '#f43f5e',
  critical: '#dc2626',
};

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0];
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
      <div style={{ color: d.payload.fill, fontWeight: 600 }}>{d.name}</div>
      <div style={{ color: '#f1f5f9', marginTop: 2 }}>
        {d.value} students ({d.payload.pct}%)
      </div>
    </div>
  );
};

const renderLegend = (props) => {
  const { payload } = props;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, justifyContent: 'center', marginTop: 8 }}>
      {payload.map((entry, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: entry.color,
            }}
          />
          <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{entry.value}</span>
        </div>
      ))}
    </div>
  );
};

export default function RiskDistribution({ data, loading, error, onRetry }) {
  if (loading)
    return (
      <div className="glass-card">
        <div className="section-header">
          <div>
            <h3 className="section-title">Risk Distribution</h3>
            <p className="section-subtitle">Current risk band breakdown</p>
          </div>
        </div>
        <SkeletonChart height={280} />
      </div>
    );

  if (error)
    return (
      <div className="glass-card">
        <ErrorState message={error} onRetry={onRetry} />
      </div>
    );

  // Normalise: backend may return [{risk_band, count, avg_score}] or {low:N, medium:N, high:N}
  let items = [];
  if (Array.isArray(data)) {
    items = data.map((d) => ({
      band: (d.risk_band || d.band || 'unknown').toLowerCase(),
      count: d.count || d.value || 0,
    }));
  } else if (typeof data === 'object' && data !== null) {
    // Object format like {low: 100, medium: 50, high: 30}
    items = Object.entries(data).map(([band, count]) => ({
      band: band.toLowerCase(),
      count: typeof count === 'number' ? count : 0,
    }));
  }

  items = items.filter((d) => d.count > 0);
  if (!items.length) return null;

  const total = items.reduce((s, d) => s + d.count, 0);
  const chartData = items.map((d) => ({
    name: d.band.charAt(0).toUpperCase() + d.band.slice(1),
    value: d.count,
    pct: total > 0 ? ((d.count / total) * 100).toFixed(1) : 0,
    fill: RISK_COLORS[d.band] || '#64748b',
  }));

  return (
    <div className="glass-card slide-up">
      <div className="section-header">
        <div>
          <h3 className="section-title">Risk Distribution</h3>
          <p className="section-subtitle">Current risk band breakdown</p>
        </div>
      </div>
      <div className="chart-container-sm">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="45%"
              innerRadius={65}
              outerRadius={95}
              paddingAngle={3}
              dataKey="value"
              animationBegin={200}
              animationDuration={800}
              animationEasing="ease-out"
            >
              {chartData.map((entry, index) => (
                <Cell key={index} fill={entry.fill} stroke="none" />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend content={renderLegend} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
