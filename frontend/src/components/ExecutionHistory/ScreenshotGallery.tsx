import { useState } from 'react';
import type { ExecutionStep } from '../../types';

interface Props {
  steps: ExecutionStep[];
}

export default function ScreenshotGallery({ steps }: Props) {
  const [enlarged, setEnlarged] = useState<string | null>(null);

  const withScreenshots = steps.filter((s) => s.screenshot_url);

  if (withScreenshots.length === 0) {
    return <div style={{ color: '#64748b', textAlign: 'center', padding: 20 }}>No screenshots available.</div>;
  }

  return (
    <>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: 12,
      }}>
        {withScreenshots.map((step) => (
          <div
            key={`${step.execution_id}-${step.step_order}`}
            onClick={() => setEnlarged(step.screenshot_url)}
            style={{
              background: '#1e293b',
              borderRadius: 8,
              overflow: 'hidden',
              cursor: 'pointer',
              border: '1px solid #334155',
            }}
          >
            <img
              src={step.screenshot_url!}
              alt={step.step_name}
              style={{ width: '100%', display: 'block' }}
              loading="lazy"
            />
            <div style={{ padding: '8px 10px' }}>
              <div style={{ color: '#e2e8f0', fontSize: 12, fontWeight: 500 }}>
                {step.step_order}. {step.step_name}
              </div>
              <div style={{
                color: step.status === 'PASSED' ? '#22c55e' : step.status === 'FAILED' ? '#ef4444' : '#64748b',
                fontSize: 11, marginTop: 2,
              }}>
                {step.status}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Lightbox */}
      {enlarged && (
        <div
          onClick={() => setEnlarged(null)}
          style={{
            position: 'fixed', inset: 0,
            background: '#000000dd',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, cursor: 'pointer',
          }}
        >
          <img
            src={enlarged}
            alt="Screenshot"
            style={{ maxWidth: '90vw', maxHeight: '90vh', borderRadius: 8 }}
          />
        </div>
      )}
    </>
  );
}
