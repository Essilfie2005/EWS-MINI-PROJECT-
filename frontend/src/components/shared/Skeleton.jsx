export function SkeletonCard({ height = 100, className = '' }) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ height, borderRadius: 'var(--radius-lg)' }}
    />
  );
}

export function SkeletonText({ width = '100%', height = 14, className = '' }) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width, height, borderRadius: 4 }}
    />
  );
}

export function SkeletonMetrics() {
  return (
    <div className="metrics-grid">
      {[1, 2, 3, 4].map((i) => (
        <SkeletonCard key={i} height={110} />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 8, cols = 6 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <div style={{ display: 'flex', gap: 16, padding: '12px 16px' }}>
        {Array.from({ length: cols }).map((_, c) => (
          <SkeletonText key={c} width={`${80 + Math.random() * 60}px`} height={12} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} style={{ display: 'flex', gap: 16, padding: '14px 16px' }}>
          {Array.from({ length: cols }).map((_, c) => (
            <SkeletonText key={c} width={`${60 + Math.random() * 80}px`} height={14} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart({ height = 280 }) {
  return <SkeletonCard height={height} />;
}
