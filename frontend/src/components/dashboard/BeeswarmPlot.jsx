import { useEffect, useRef, useState } from 'react';
import { SkeletonChart } from '../shared/Skeleton';
import ErrorState from '../shared/ErrorState';

const FEATURE_COLORS = [
  '#06b6d4', '#8b5cf6', '#f59e0b', '#f43f5e', '#10b981',
];

/**
 * Simulated beeswarm: each dot is one student, x = SHAP value, y = jittered per feature row.
 * Colour = feature value magnitude (blue=low, red=high).
 */
function drawBeeswarm(canvas, data) {
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.offsetWidth;
  const H = canvas.offsetHeight;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const features = [...new Set(data.map((d) => d.feature))];
  const rowH = H / (features.length + 1);
  const PAD_L = 155;
  const PAD_R = 24;
  const plotW = W - PAD_L - PAD_R;

  // x-axis: SHAP value range
  const allVals = data.map((d) => d.shap_value);
  const xMin = Math.min(...allVals, -0.01);
  const xMax = Math.max(...allVals, 0.01);
  const xRange = Math.max(Math.abs(xMin), Math.abs(xMax));

  const toX = (v) => PAD_L + plotW / 2 + (v / xRange) * (plotW / 2);

  // Draw gridlines + axis
  ctx.strokeStyle = 'rgba(255,255,255,0.06)';
  ctx.lineWidth = 1;
  [-0.5, -0.25, 0, 0.25, 0.5].forEach((t) => {
    const x = toX(t * xRange);
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, H);
    ctx.stroke();
  });

  // zero line
  ctx.strokeStyle = 'rgba(255,255,255,0.15)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(toX(0), 0);
  ctx.lineTo(toX(0), H);
  ctx.stroke();

  // x-axis labels
  ctx.fillStyle = '#64748b';
  ctx.font = '11px Inter, system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('← Low Risk', PAD_L + plotW * 0.15, H - 6);
  ctx.fillText('High Risk →', PAD_L + plotW * 0.85, H - 6);

  // Per feature row
  features.forEach((feat, fi) => {
    const y = rowH * (fi + 1);
    const pts = data.filter((d) => d.feature === feat);

    // Feature label
    ctx.fillStyle = '#94a3b8';
    ctx.font = '12px Inter, system-ui, sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(feat, PAD_L - 10, y + 4);

    // Subtle row stripe
    if (fi % 2 === 0) {
      ctx.fillStyle = 'rgba(255,255,255,0.015)';
      ctx.fillRect(PAD_L, y - rowH / 2, plotW, rowH);
    }

    // Separate dots with simple collision-avoidance (bin by x-pixel)
    const bins = {};
    pts.forEach((pt) => {
      const px = Math.round(toX(pt.shap_value));
      if (!bins[px]) bins[px] = 0;
      const tier = bins[px]++;
      const dy = tier === 0 ? 0 : (tier % 2 === 0 ? 1 : -1) * Math.ceil(tier / 2) * 5;

      // Color: blue(low) → red(high) based on feature_value 0-1
      const t = Math.max(0, Math.min(1, pt.feature_value ?? 0.5));
      const r = Math.round(6 + t * (244 - 6));
      const g = Math.round(182 - t * (182 - 63));
      const b = Math.round(212 - t * (212 - 94));
      ctx.fillStyle = `rgba(${r},${g},${b},0.85)`;
      ctx.beginPath();
      ctx.arc(px, y + dy, 3.5, 0, Math.PI * 2);
      ctx.fill();
    });
  });
}

export default function BeeswarmPlot({ data, loading, error, onRetry }) {
  const canvasRef = useRef(null);
  const [dims, setDims] = useState({ w: 0, h: 0 });

  useEffect(() => {
    if (!canvasRef.current || !data?.length) return;
    const el = canvasRef.current;
    const ro = new ResizeObserver(() => {
      if (!canvasRef.current) return;
      setDims({ w: canvasRef.current.offsetWidth, h: canvasRef.current.offsetHeight });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [data]);

  useEffect(() => {
    if (!canvasRef.current || !data?.length) return;
    drawBeeswarm(canvasRef.current, data);
  }, [data, dims]);

  if (loading)
    return (
      <div className="glass-card">
        <div className="section-header">
          <div>
            <h3 className="section-title">SHAP Beeswarm — Cohort View</h3>
            <p className="section-subtitle">Feature impact across all students</p>
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

  if (!data?.length) return null;

  return (
    <div className="glass-card slide-up">
      <div className="section-header">
        <div>
          <h3 className="section-title">SHAP Beeswarm — Cohort View</h3>
          <p className="section-subtitle">
            Each dot = one student · x-axis = SHAP impact · colour: blue = low feature value, red = high
          </p>
        </div>
        {/* colour scale legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)' }}>
          <span>Low</span>
          <div style={{
            width: 80, height: 8, borderRadius: 4,
            background: 'linear-gradient(90deg, #06b6d4, #f43f5e)',
          }} />
          <span>High</span>
        </div>
      </div>
      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: 340, display: 'block' }}
      />
    </div>
  );
}
