import { useMemo } from 'react';
import useApi from '../hooks/useApi';
import {
  fetchRocCurve,
  fetchBeeswarmData,
  fetchPilotMetrics,
  fetchStudents,
  fetchModelInfo,
} from '../services/api';
import RocCurve from '../components/dashboard/RocCurve';
import BeeswarmPlot from '../components/dashboard/BeeswarmPlot';
import ConversionRate from '../components/dashboard/ConversionRate';

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

export default function AnalyticsPage() {
  const roc      = useApi(fetchRocCurve);
  const beeswarm = useApi(fetchBeeswarmData);
  const pilot    = useApi(fetchPilotMetrics);
  const students = useApi(fetchStudents);
  const modelInfo = useApi(fetchModelInfo);

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
    // try to build from student shap values
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
      <BeeswarmPlot
        data={beeswarmData}
        loading={isLoading && !beeswarmData.length}
        error={!apiDown ? (beeswarm.error && students.error ? beeswarm.error : null) : null}
        onRetry={beeswarm.refetch}
      />

    </div>
  );
}
