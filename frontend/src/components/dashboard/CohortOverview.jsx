import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { SkeletonChart } from '../shared/Skeleton';
import ErrorState from '../shared/ErrorState';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: 'rgba(19, 27, 46, 0.95)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 8,
        padding: '12px 16px',
        fontSize: 13,
      }}
    >
      <div style={{ fontWeight: 600, color: '#f1f5f9', marginBottom: 8 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color }} />
          <span style={{ color: 'var(--text-secondary)' }}>{p.name}:</span>
          <span style={{ color: '#f1f5f9', fontWeight: 600 }}>{p.value}</span>
        </div>
      ))}
    </div>
  );
};

export default function CohortOverview({ data, loading, error, onRetry }) {
  if (loading)
    return (
      <div className="glass-card">
        <div className="section-header">
          <div>
            <h3 className="section-title">Risk Trend Over Time</h3>
            <p className="section-subtitle">Cohort risk levels across assessment periods</p>
          </div>
        </div>
        <SkeletonChart height={300} />
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
          <h3 className="section-title">Risk Trend Over Time</h3>
          <p className="section-subtitle">Cohort risk levels across assessment periods</p>
        </div>
      </div>
      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="gradLow" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradMedium" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradHigh" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradCritical" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#dc2626" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#dc2626" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis
              dataKey="period"
              tick={{ fontSize: 12, fill: '#64748b' }}
              axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#64748b' }}
              axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
              iconType="circle"
              iconSize={8}
            />
            <Area
              type="monotone"
              dataKey="low"
              name="Low"
              stroke="#10b981"
              fill="url(#gradLow)"
              strokeWidth={2}
              animationDuration={1000}
            />
            <Area
              type="monotone"
              dataKey="medium"
              name="Medium"
              stroke="#f59e0b"
              fill="url(#gradMedium)"
              strokeWidth={2}
              animationDuration={1000}
              animationBegin={200}
            />
            <Area
              type="monotone"
              dataKey="high"
              name="High"
              stroke="#f43f5e"
              fill="url(#gradHigh)"
              strokeWidth={2}
              animationDuration={1000}
              animationBegin={400}
            />
            <Area
              type="monotone"
              dataKey="critical"
              name="Critical"
              stroke="#dc2626"
              fill="url(#gradCritical)"
              strokeWidth={2}
              animationDuration={1000}
              animationBegin={600}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
