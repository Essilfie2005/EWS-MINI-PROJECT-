import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from 'recharts';
import { Target } from 'lucide-react';
import { SkeletonChart } from '../shared/Skeleton';

const METRICS = [
  { key: 'auc_roc',          label: 'Model AUC-ROC',            target: 0.8,  scale: 100, unit: '%' },
  { key: 'conversion_rate',  label: 'Intervention Conversion',  target: 60,   scale: 1,   unit: '%' },
  { key: 'usability_score',  label: 'Counsellor Usability',     target: 70,   scale: 1,   unit: '/100' },
];

function getBarColor(actual, target) {
  if (actual >= target) return '#10b981';
  if (actual >= target * 0.75) return '#f59e0b';
  return '#f43f5e';
}

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
      <div style={{ fontWeight: 600, color: '#f1f5f9', marginBottom: 6 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color, display: 'flex', gap: 8 }}>
          <span style={{ color: '#94a3b8' }}>{p.name}:</span>
          <strong style={{ color: p.color }}>{Number(p.value).toFixed(1)}</strong>
        </div>
      ))}
    </div>
  );
};

export default function ConversionRate({ data, loading }) {
  if (loading)
    return (
      <div className="glass-card">
        <div className="section-header">
          <div>
            <h3 className="section-title">Pilot Success Metrics</h3>
            <p className="section-subtitle">Actual vs target thresholds</p>
          </div>
        </div>
        <SkeletonChart height={220} />
      </div>
    );

  if (!data) return null;

  const chartData = METRICS.map((m) => {
    const raw = data[m.key] ?? null;
    if (raw === null) return null;
    const actual = m.scale !== 1 ? raw * m.scale : raw;
    return {
      name: m.label,
      Actual: parseFloat(actual.toFixed(1)),
      Target: parseFloat((m.target).toFixed(1)),
      unit: m.unit,
      color: getBarColor(actual, m.target),
    };
  }).filter(Boolean);

  if (!chartData.length) return null;

  return (
    <div className="glass-card slide-up">
      <div className="section-header">
        <div>
          <h3 className="section-title">Pilot Success Metrics</h3>
          <p className="section-subtitle">Actual vs target thresholds</p>
        </div>
        <Target size={18} style={{ color: 'var(--text-muted)' }} />
      </div>

      <div style={{ width: '100%', height: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 10, right: 16, left: -10, bottom: 8 }}
            barCategoryGap="30%"
            barGap={4}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: '#64748b' }}
              axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#64748b' }}
              axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              tickLine={false}
              domain={[0, 100]}
              tickFormatter={(v) => `${v}`}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Legend
              wrapperStyle={{ fontSize: 12, color: '#94a3b8', paddingTop: 8 }}
              formatter={(v) => <span style={{ color: '#94a3b8' }}>{v}</span>}
            />
            {/* Target bars (grey reference) */}
            <Bar dataKey="Target" fill="rgba(100,116,139,0.3)" radius={[4, 4, 0, 0]} name="Target" />
            {/* Actual bars (colour-coded) */}
            <Bar dataKey="Actual" radius={[4, 4, 0, 0]} name="Actual" animationDuration={800}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.color} fillOpacity={0.9} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Status badges */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 8 }}>
        {chartData.map((d) => (
          <div key={d.name} style={{
            fontSize: 11, fontWeight: 600, padding: '2px 10px',
            borderRadius: 99,
            background: d.Actual >= d.Target ? 'rgba(16,185,129,0.12)' : 'rgba(244,63,94,0.12)',
            color: d.Actual >= d.Target ? '#10b981' : '#f43f5e',
          }}>
            {d.Actual >= d.Target ? '✓' : '✗'} {d.name}
          </div>
        ))}
      </div>
    </div>
  );
}
