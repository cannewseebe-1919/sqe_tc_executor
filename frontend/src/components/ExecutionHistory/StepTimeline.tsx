import type { ExecutionStep } from '../../types';

interface Props {
  steps: ExecutionStep[];
}

export default function StepTimeline({ steps }: Props) {
  if (steps.length === 0) {
    return <div style={{ color: '#64748b', textAlign: 'center', padding: 20 }}>No steps recorded.</div>;
  }

  const sorted = [...steps].sort((a, b) => a.step_order - b.step_order);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {sorted.map((step, i) => {
        const color = step.status === 'PASSED' ? '#22c55e'
          : step.status === 'FAILED' ? '#ef4444' : '#64748b';
        const isLast = i === sorted.length - 1;

        return (
          <div key={`${step.execution_id}-${step.step_order}`} style={{ display: 'flex', gap: 16 }}>
            {/* Timeline line + dot */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 20 }}>
              <div style={{
                width: 12, height: 12, borderRadius: '50%',
                background: color, border: `2px solid ${color}`,
                flexShrink: 0, marginTop: 4,
              }} />
              {!isLast && (
                <div style={{ width: 2, flex: 1, background: '#334155', minHeight: 30 }} />
              )}
            </div>

            {/* Step card */}
            <div style={{
              flex: 1,
              background: '#1e293b',
              borderRadius: 8,
              padding: 14,
              marginBottom: 8,
              border: `1px solid ${color}22`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#f1f5f9', fontWeight: 500, fontSize: 14 }}>
                  {step.step_order}. {step.step_name}
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: '#94a3b8', fontSize: 12 }}>
                    {step.duration_sec.toFixed(2)}s
                  </span>
                  <span style={{
                    color, fontSize: 12, fontWeight: 600,
                    background: `${color}18`, padding: '2px 8px', borderRadius: 10,
                  }}>
                    {step.status}
                  </span>
                </div>
              </div>
              {step.log && (
                <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 6, fontFamily: 'monospace' }}>
                  {step.log}
                </div>
              )}
              {step.error_type && (
                <div style={{ color: '#fca5a5', fontSize: 12, marginTop: 4, fontWeight: 500 }}>
                  Error: {step.error_type}
                </div>
              )}
              {step.screenshot_url && (
                <div style={{ marginTop: 8 }}>
                  <img
                    src={step.screenshot_url}
                    alt={step.step_name}
                    style={{ maxWidth: 200, borderRadius: 6, border: '1px solid #334155' }}
                    loading="lazy"
                  />
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
