import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { SkeletonChart } from '../shared/Skeleton';
import ErrorState from '../shared/ErrorState';

const COLORS = ['#06b6d4', '#8b5cf6', '#f59e0b', '#f43f5e', '#10b981'];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
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
      <div style={{ fontWeight: 600, color: '#f1f5f9', marginBottom: 4 }}>{label}</div>
      <div style={{ color: '#94a3b8' }}>
        Importance: <span style={{ color: '#f1f5f9', fontWeight: 700 }}>{payload[0].value.toFixed(4)}</span>
      </div>
    </div>
  );
};

export default function CohortOverview({ data, loading, error, onRetry }) {
  if (loading)
    return (
      <div className="glass-card">
        <div className="section-header">
          <div>
            <h3 className="section-title">Feature Importance</h3>
            <p className="section-subtitle">XGBoost gain scores by feature</p>
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
          <h3 className="section-title">Feature Importance</h3>
          <p className="section-subtitle">XGBoost gain scores by feature</p>
        </div>
      </div>
      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis
              dataKey="period"
              tick={{ fontSize: 11, fill: '#64748b' }}
              axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              tickLine={false}
              angle={-25}
              textAnchor="end"
              interval={0}
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#64748b' }}
              axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Bar dataKey="importance" radius={[4, 4, 0, 0]} animationDuration={800}>
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
