import { useMemo } from 'react';
import useApi from '../hooks/useApi';
import {
  fetchRocCurve,
  fetchBeeswarmData,
  fetchPilotMetrics,
  fetchStudents,
  fetchModelInfo,
  fetchConfusionMatrix,
  fetchCalibrationCurve,
  fetchFairnessData,
  fetchCtganQuality,
} from '../services/api';
import RocCurve from '../components/dashboard/RocCurve';
import BeeswarmPlot from '../components/dashboard/BeeswarmPlot';
import ConversionRate from '../components/dashboard/ConversionRate';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  BarChart,
  Bar,
  Legend,
} from 'recharts';

// ── Demo data (proposal E1 visuals #2, #3, #6) ───────────────────────────

/** ROC curve: XGBoost vs Logistic Regression vs Rule-based (proposal E1 #2) */
function buildDemoRoc() {
  const pts = (auc) =>
    Array.from({ length: 21 }, (_, i) => {
      const fpr = parseFloat((i / 20).toFixed(2));
      const tpr = parseFloat(Math.min(1, Math.pow(fpr, Math.max(0.01, (1 - auc) / auc))).toFixed(4));
      return { fpr, tpr };
    });
  return {
    xgboost:   { auc: 0.834, points: pts(0.834) },
    logistic:  { auc: 0.741, points: pts(0.741) },
    rule_based:{ auc: 0.612, points: pts(0.612) },
  };
}

/** SHAP beeswarm: each dot = one student, x = SHAP value (proposal E1 #3) */
function buildDemoBeeswarm() {
  const features = [
    'Attendance Rate',
    'Quiz Average',
    'Assignment Submission',
    'Mobile Engagement',
    'Financial Aid',
  ];
  const dots = [];
  features.forEach((feat, fi) => {
    for (let i = 0; i < 30; i++) {
      const base = fi === 0 ? 0.35 : fi === 1 ? 0.22 : fi === 2 ? 0.10 : fi === 3 ? 0.06 : 0.03;
      dots.push({
        feature: feat,
        shap_value: (Math.random() - 0.4) * base * 2,
        feature_value: Math.random(),
      });
    }
  });
  return dots;
}

/** Pilot success metrics bar chart (proposal E1 #6) */
const DEMO_PILOT = {
  auc_roc: 0.834,          // → rendered as 83.4% vs target 80%
  conversion_rate: 67.0,   // % vs target 60%
  usability_score: 74.0,   // /100 vs target 70
};

const DEMO_ROC      = buildDemoRoc();
const DEMO_BEESWARM = buildDemoBeeswarm();

// ── Confusion Matrix Cell ─────────────────────────────────────────────────
function ConfusionCell({ label, count, bg, border, textColor }) {
  return (
    <div style={{
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: 10,
      padding: '20px 16px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 6,
    }}>
      <div style={{ fontSize: 28, fontWeight: 700, color: textColor, lineHeight: 1 }}>
        {count ?? '—'}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', textAlign: 'center', lineHeight: 1.3 }}>
        {label}
      </div>
    </div>
  );
}

// ── Calibration Curve Tooltip ─────────────────────────────────────────────
const CalibTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(19,27,46,0.95)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 13,
    }}>
      <div style={{ color: '#94a3b8', marginBottom: 4 }}>Mean Predicted: {label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value?.toFixed(3)}
        </div>
      ))}
    </div>
  );
};

// ── Fairness Tooltip ──────────────────────────────────────────────────────
const FairnessTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(19,27,46,0.95)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 13,
    }}>
      <div style={{ color: '#94a3b8', marginBottom: 4 }}>IMD Band {label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value?.toFixed(1)}%
        </div>
      ))}
    </div>
  );
};

// ── "Coming Soon" placeholder ─────────────────────────────────────────────
function ComingSoon({ title }) {
  return (
    <div className="glass-card" style={{ marginBottom: 24 }}>
      <h3 className="section-title" style={{ marginBottom: 12 }}>{title}</h3>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: 120,
        borderRadius: 8,
        background: 'rgba(99,102,241,0.04)',
        border: '1px dashed rgba(99,102,241,0.2)',
        color: 'var(--text-dim)',
        fontSize: 14,
        gap: 8,
      }}>
        🚧 Coming soon — endpoint not yet available
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const roc      = useApi(fetchRocCurve);
  const beeswarm = useApi(fetchBeeswarmData);
  const pilot    = useApi(fetchPilotMetrics);
  const students = useApi(fetchStudents);
  const modelInfo = useApi(fetchModelInfo);
  const confMatrix = useApi(fetchConfusionMatrix);
  const calibration = useApi(fetchCalibrationCurve);
  const fairness = useApi(fetchFairnessData);
  const ctgan = useApi(fetchCtganQuality);

  const apiDown = !roc.loading && roc.error;

  // ── ROC curve ─────────────────────────────────────────────────────────
  const rocData = useMemo(() => {
    if (roc.data) return roc.data;
    const m = modelInfo.data?.metrics;
    if (m?.auc_roc) {
      const pts = (auc) => Array.from({ length: 21 }, (_, i) => {
        const fpr = parseFloat((i / 20).toFixed(2));
        return { fpr, tpr: parseFloat(Math.min(1, Math.pow(fpr, Math.max(0.01,(1-auc)/auc))).toFixed(4)) };
      });
      return { xgboost: { auc: m.auc_roc, points: pts(m.auc_roc) } };
    }
    return apiDown ? DEMO_ROC : null;
  }, [roc.data, modelInfo.data, apiDown]);

  // ── SHAP beeswarm ─────────────────────────────────────────────────────
  const beeswarmData = useMemo(() => {
    if (beeswarm.data?.length) return beeswarm.data;
    const list = Array.isArray(students.data) ? students.data : students.data?.students || [];
    const dots = [];
    list.forEach((s) => {
      (s.shap_values || []).forEach((sv) => {
        dots.push({
          feature: sv.feature,
          shap_value: sv.contribution ?? sv.value ?? 0,
          feature_value: sv.raw_value != null ? Math.min(1, Math.max(0, sv.raw_value / 100)) : 0.5,
        });
      });
    });
    if (dots.length) return dots;
    return apiDown ? DEMO_BEESWARM : [];
  }, [beeswarm.data, students.data, apiDown]);

  // ── Pilot metrics ─────────────────────────────────────────────────────
  const pilotData = useMemo(() => {
    if (pilot.data) return pilot.data;
    const m = modelInfo.data?.metrics;
    if (m) return { auc_roc: m.auc_roc ?? null, conversion_rate: null, usability_score: null };
    return apiDown ? DEMO_PILOT : null;
  }, [pilot.data, modelInfo.data, apiDown]);

  // ── Confusion Matrix ──────────────────────────────────────────────────
  const cmData = confMatrix.data;
  const cmNotAvailable = !confMatrix.loading && confMatrix.error;

  // ── Calibration Curve ─────────────────────────────────────────────────
  const calibData = useMemo(() => {
    if (!calibration.data) return null;
    const raw = Array.isArray(calibration.data) ? calibration.data : calibration.data?.points;
    if (!raw) return null;
    // Also append the perfect calibration line as a second series
    return raw.map((pt) => ({
      mean_predicted: pt.mean_predicted ?? pt.x,
      fraction_positives: pt.fraction_positives ?? pt.y,
      perfect: pt.mean_predicted ?? pt.x,
    }));
  }, [calibration.data]);
  const calibNotAvailable = !calibration.loading && calibration.error;

  // ── Fairness Data ─────────────────────────────────────────────────────
  const fairData = useMemo(() => {
    if (!fairness.data) return null;
    return Array.isArray(fairness.data) ? fairness.data : fairness.data?.bands;
  }, [fairness.data]);
  const fairNotAvailable = !fairness.loading && fairness.error;

  // ── CTGAN Quality ─────────────────────────────────────────────────────
  const ctganData = ctgan.data;
  const ctganNotAvailable = !ctgan.loading && ctgan.error;

  const isLoading = roc.loading || beeswarm.loading || pilot.loading;

  return (
    <div className="fade-in">

      {apiDown && (
        <div style={{
          background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.25)',
          borderRadius: 10, padding: '10px 16px', marginBottom: 20,
          fontSize: 13, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          ⚠ Backend offline — showing demo analytics data
        </div>
      )}

      {/* Visual #6 — Pilot success metrics bar chart */}
      {(pilotData || isLoading) && (
        <div style={{ marginBottom: 24 }}>
          <ConversionRate data={pilotData} loading={isLoading && !pilotData} />
        </div>
      )}

      {/* Visual #2 — ROC curve: XGBoost vs Logistic vs Rule-based */}
      <div style={{ marginBottom: 24 }}>
        <RocCurve
          data={rocData}
          loading={isLoading && !rocData}
          error={!apiDown ? (roc.error && modelInfo.error ? roc.error : null) : null}
          onRetry={roc.refetch}
        />
      </div>

      {/* Visual #3 — SHAP beeswarm summary plot */}
      <div style={{ marginBottom: 24 }}>
        <BeeswarmPlot
          data={beeswarmData}
          loading={isLoading && !beeswarmData.length}
          error={!apiDown ? (beeswarm.error && students.error ? beeswarm.error : null) : null}
          onRetry={beeswarm.refetch}
        />
      </div>

      {/* ── A) Confusion Matrix ─────────────────────────────────────────── */}
      {cmNotAvailable ? (
        <ComingSoon title="Confusion Matrix" />
      ) : (
        <div className="glass-card" style={{ marginBottom: 24 }}>
          <h3 className="section-title" style={{ marginBottom: 4 }}>Confusion Matrix</h3>
          <p className="section-subtitle" style={{ marginBottom: 20 }}>
            Model classification performance at current threshold
          </p>
          {confMatrix.loading ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {[0,1,2,3].map(i => (
                <div key={i} style={{ height: 90, borderRadius: 10, background: 'rgba(255,255,255,0.03)', animation: 'pulse 1.5s infinite' }} />
              ))}
            </div>
          ) : cmData ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <ConfusionCell
                label="True Positive"
                count={cmData.tp ?? cmData.TP}
                bg="rgba(16,185,129,0.08)"
                border="rgba(16,185,129,0.25)"
                textColor="#10b981"
              />
              <ConfusionCell
                label="False Positive"
                count={cmData.fp ?? cmData.FP}
                bg="rgba(245,158,11,0.08)"
                border="rgba(245,158,11,0.25)"
                textColor="#f59e0b"
              />
              <ConfusionCell
                label="False Negative"
                count={cmData.fn ?? cmData.FN}
                bg="rgba(244,63,94,0.08)"
                border="rgba(244,63,94,0.25)"
                textColor="#f43f5e"
              />
              <ConfusionCell
                label="True Negative"
                count={cmData.tn ?? cmData.TN}
                bg="rgba(100,116,139,0.08)"
                border="rgba(100,116,139,0.25)"
                textColor="#94a3b8"
              />
            </div>
          ) : (
            <div style={{ color: 'var(--text-dim)', fontSize: 14, padding: '24px 0', textAlign: 'center' }}>
              No confusion matrix data available
            </div>
          )}
        </div>
      )}

      {/* ── B) Calibration Curve ─────────────────────────────────────────── */}
      {calibNotAvailable ? (
        <ComingSoon title="Calibration Curve" />
      ) : (
        <div className="glass-card" style={{ marginBottom: 24 }}>
          <h3 className="section-title" style={{ marginBottom: 4 }}>Calibration Curve</h3>
          <p className="section-subtitle" style={{ marginBottom: 20 }}>
            How well predicted probabilities match actual outcomes
          </p>
          {calibration.loading ? (
            <div style={{ height: 260, borderRadius: 8, background: 'rgba(255,255,255,0.03)', animation: 'pulse 1.5s infinite' }} />
          ) : calibData ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={calibData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="mean_predicted"
                  domain={[0, 1]}
                  type="number"
                  tickFormatter={(v) => v.toFixed(1)}
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                  tickLine={false}
                  label={{ value: 'Mean Predicted Probability', position: 'insideBottom', offset: -4, fill: '#64748b', fontSize: 12 }}
                />
                <YAxis
                  domain={[0, 1]}
                  tickFormatter={(v) => v.toFixed(1)}
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  axisLine={false}
                  tickLine={false}
                  label={{ value: 'Fraction of Positives', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 12 }}
                />
                <Tooltip content={<CalibTooltip />} />
                <Line
                  dataKey="fraction_positives"
                  name="Model"
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={{ fill: '#6366f1', r: 4 }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  dataKey="perfect"
                  name="Perfect"
                  stroke="rgba(255,255,255,0.25)"
                  strokeWidth={1.5}
                  strokeDasharray="6 4"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: 'var(--text-dim)', fontSize: 14, padding: '24px 0', textAlign: 'center' }}>
              No calibration data available
            </div>
          )}
        </div>
      )}

      {/* ── C) Fairness Analysis ──────────────────────────────────────────── */}
      {fairNotAvailable ? (
        <ComingSoon title="Fairness Analysis" />
      ) : (
        <div className="glass-card" style={{ marginBottom: 24 }}>
          <h3 className="section-title" style={{ marginBottom: 4 }}>Fairness Analysis</h3>
          <p className="section-subtitle" style={{ marginBottom: 20 }}>
            Dropout rate vs model accuracy by financial aid band (IMD 1–10)
          </p>
          {fairness.loading ? (
            <div style={{ height: 260, borderRadius: 8, background: 'rgba(255,255,255,0.03)', animation: 'pulse 1.5s infinite' }} />
          ) : fairData?.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={fairData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis
                  dataKey="band"
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                  tickLine={false}
                  label={{ value: 'Financial Aid Band (IMD)', position: 'insideBottom', offset: -4, fill: '#64748b', fontSize: 12 }}
                />
                <YAxis
                  unit="%"
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<FairnessTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8', paddingTop: 8 }} />
                <Bar dataKey="dropout_rate" name="Dropout Rate (%)" fill="#f43f5e" fillOpacity={0.75} radius={[4,4,0,0]} />
                <Bar dataKey="model_accuracy" name="Model Accuracy (%)" fill="#6366f1" fillOpacity={0.75} radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: 'var(--text-dim)', fontSize: 14, padding: '24px 0', textAlign: 'center' }}>
              No fairness data available
            </div>
          )}
        </div>
      )}

      {/* ── D) CTGAN Quality Report ───────────────────────────────────────── */}
      {ctganNotAvailable ? (
        <ComingSoon title="CTGAN Synthetic Data Quality" />
      ) : (
        <div className="glass-card" style={{ marginBottom: 24 }}>
          <h3 className="section-title" style={{ marginBottom: 4 }}>CTGAN Synthetic Data Quality</h3>
          <p className="section-subtitle" style={{ marginBottom: 20 }}>
            SDV quality metrics — how closely synthetic data matches real distributions
          </p>
          {ctgan.loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {[0,1].map(i => (
                <div key={i} style={{ height: 64, borderRadius: 8, background: 'rgba(255,255,255,0.03)', animation: 'pulse 1.5s infinite' }} />
              ))}
            </div>
          ) : ctganData ? (() => {
            const metrics = [
              {
                key: 'ks_complement',
                label: 'KS Complement',
                desc: 'Distribution similarity (higher = better)',
                threshold: 0.8,
                value: ctganData.ks_complement ?? ctganData.KSComplement,
              },
              {
                key: 'correlation_similarity',
                label: 'Correlation Similarity',
                desc: 'Feature correlation fidelity (higher = better)',
                threshold: 0.75,
                value: ctganData.correlation_similarity ?? ctganData.CorrelationSimilarity,
              },
            ];
            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {metrics.map((m) => {
                  const pct = m.value != null ? Math.round(m.value * 100) : null;
                  const pass = pct != null && m.value >= m.threshold;
                  return (
                    <div key={m.key} style={{ padding: '14px 18px', background: 'rgba(255,255,255,0.02)', borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <div>
                          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{m.label}</div>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{m.desc}</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <span style={{ fontSize: 22, fontWeight: 700, color: pass ? '#10b981' : '#f43f5e' }}>
                            {pct != null ? `${pct}%` : '—'}
                          </span>
                          <span style={{
                            fontSize: 11,
                            fontWeight: 600,
                            padding: '3px 8px',
                            borderRadius: 20,
                            background: pass ? 'rgba(16,185,129,0.15)' : 'rgba(244,63,94,0.15)',
                            color: pass ? '#10b981' : '#f43f5e',
                            border: `1px solid ${pass ? 'rgba(16,185,129,0.3)' : 'rgba(244,63,94,0.3)'}`,
                          }}>
                            {pass ? '✓ PASS' : '✗ FAIL'}
                          </span>
                        </div>
                      </div>
                      <div style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
                        <div style={{
                          height: '100%',
                          width: `${pct ?? 0}%`,
                          background: pass ? 'linear-gradient(90deg,#10b981,#34d399)' : 'linear-gradient(90deg,#f43f5e,#fb7185)',
                          borderRadius: 3,
                          transition: 'width 0.8s ease',
                        }} />
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>
                        Threshold: {Math.round(m.threshold * 100)}%
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })() : (
            <div style={{ color: 'var(--text-dim)', fontSize: 14, padding: '24px 0', textAlign: 'center' }}>
              No CTGAN quality data available
            </div>
          )}
        </div>
      )}
    </div>
  );
}
