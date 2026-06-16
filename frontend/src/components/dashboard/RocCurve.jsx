import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { SkeletonChart } from '../shared/Skeleton';
import ErrorState from '../shared/ErrorState';

const MODEL_COLORS = {
  xgboost: '#06b6d4',
  logistic: '#8b5cf6',
  rule_based: '#f59e0b',
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(19,27,46,0.97)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 13,
    }}>
      <div style={{ color: '#94a3b8', marginBottom: 6 }}>
        FPR: <strong style={{ color: '#f1f5f9' }}>{Number(label).toFixed(2)}</strong>
      </div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color, display: 'flex', gap: 8, alignItems: 'center' }}>
          <span>{p.name}:</span>
          <strong>TPR {Number(p.value).toFixed(2)}</strong>
        </div>
      ))}
    </div>
  );
};

export default function RocCurve({ data, loading, error, onRetry }) {
  if (loading)
    return (
      <div className="glass-card">
        <div className="section-header">
          <div>
            <h3 className="section-title">ROC Curves</h3>
            <p className="section-subtitle">XGBoost vs Logistic Regression vs Rule-based</p>
          </div>
        </div>
        <SkeletonChart height={320} />
      </div>
    );

  if (error)
    return (
      <div className="glass-card">
        <ErrorState message={error} onRetry={onRetry} />
      </div>
    );

  if (!data) return null;

  // data shape: { xgboost: { auc, points:[{fpr,tpr}] }, logistic: {...}, rule_based: {...} }
  // Merge into recharts format: [{fpr, xgboost_tpr, logistic_tpr, rule_tpr}]
  const modelKeys = Object.keys(data);
  if (!modelKeys.length) return null;

  const basePoints = data[modelKeys[0]]?.points || [];
  const chartData = basePoints.map((pt, i) => {
    const row = { fpr: pt.fpr };
    modelKeys.forEach((k) => {
      row[k] = data[k]?.points?.[i]?.tpr ?? 0;
    });
    return row;
  });

  const MODEL_LABELS = {
    xgboost: 'XGBoost',
    logistic: 'Logistic Regression',
    rule_based: 'Rule-based',
  };

  return (
    <div className="glass-card slide-up">
      <div className="section-header">
        <div>
          <h3 className="section-title">ROC Curves</h3>
          <p className="section-subtitle">True Positive Rate vs False Positive Rate</p>
        </div>
        <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
          {modelKeys.map((k) => (
            <span key={k} style={{ color: MODEL_COLORS[k] || '#94a3b8' }}>
              AUC: <strong>{data[k]?.auc?.toFixed(3) ?? '—'}</strong>
            </span>
          ))}
        </div>
      </div>
      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis
              dataKey="fpr"
              type="number"
              domain={[0, 1]}
              tickFormatter={(v) => v.toFixed(1)}
              tick={{ fontSize: 11, fill: '#64748b' }}
              axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              tickLine={false}
              label={{ value: 'False Positive Rate', position: 'insideBottom', offset: -6, fill: '#64748b', fontSize: 12 }}
            />
            <YAxis
              domain={[0, 1]}
              tickFormatter={(v) => v.toFixed(1)}
              tick={{ fontSize: 11, fill: '#64748b' }}
              axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              tickLine={false}
              label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft', offset: 20, fill: '#64748b', fontSize: 12 }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              formatter={(v) => <span style={{ fontSize: 12, color: '#94a3b8' }}>{MODEL_LABELS[v] || v}</span>}
            />
            {/* Random baseline */}
            <ReferenceLine
              segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
              stroke="rgba(255,255,255,0.15)"
              strokeDasharray="5 5"
              label={{ value: 'Random', fill: '#475569', fontSize: 11, position: 'insideTopRight' }}
            />
            {modelKeys.map((k) => (
              <Line
                key={k}
                type="monotone"
                dataKey={k}
                name={k}
                stroke={MODEL_COLORS[k] || '#94a3b8'}
                strokeWidth={2}
                dot={false}
                animationDuration={800}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
