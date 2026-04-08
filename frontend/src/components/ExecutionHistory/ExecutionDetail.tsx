import { useEffect, useState } from 'react';
import type { Execution } from '../../types';
import { getExecution } from '../../services/api';
import StepTimeline from './StepTimeline';
import ScreenshotGallery from './ScreenshotGallery';

interface Props {
  executionId: string;
  onBack: () => void;
}

export default function ExecutionDetail({ executionId, onBack }: Props) {
  const [exec, setExec] = useState<Execution | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'timeline' | 'screenshots' | 'logs'>('timeline');

  useEffect(() => {
    let cancelled = false;
    const fetch = async () => {
      try {
        const data = await getExecution(executionId);
        if (!cancelled) setExec(data);
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetch();
    // Poll if still running
    const interval = setInterval(() => {
      if (exec?.status === 'RUNNING' || exec?.status === 'QUEUED') fetch();
    }, 3000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [executionId, exec?.status]);

  if (loading || !exec) {
    return <div style={{ color: '#94a3b8', textAlign: 'center', padding: 40 }}>Loading execution details...</div>;
  }

  const statusColors: Record<string, string> = {
    COMPLETED: '#22c55e', FAILED: '#ef4444', RUNNING: '#3b82f6',
    QUEUED: '#f59e0b', ABORTED: '#a855f7',
  };

  return (
    <div>
      <button
        onClick={onBack}
        style={{
          background: '#334155', border: 'none', color: '#f1f5f9',
          padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13, marginBottom: 20,
        }}
      >
        Back to History
      </button>

      {/* Summary card */}
      <div style={{
        background: '#1e293b', borderRadius: 12, padding: 20,
        border: '1px solid #334155', marginBottom: 20,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ margin: 0, color: '#f1f5f9', fontSize: 20 }}>
            Execution {exec.id.slice(0, 12)}
          </h2>
          <span style={{
            color: statusColors[exec.status] ?? '#94a3b8',
            fontSize: 16, fontWeight: 700,
          }}>
            {exec.status}
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
          <InfoItem label="Device" value={exec.device_info?.model ?? exec.device_id} />
          <InfoItem label="Requested By" value={exec.requested_by} />
          <InfoItem label="Started" value={exec.started_at ? new Date(exec.started_at).toLocaleString() : '-'} />
          <InfoItem label="Duration" value={exec.total_duration_sec != null ? `${exec.total_duration_sec.toFixed(1)}s` : '-'} />
          {exec.summary && (
            <>
              <InfoItem label="Steps" value={`${exec.summary.passed}/${exec.summary.total_steps} passed`} />
              <InfoItem label="Failed" value={String(exec.summary.failed)} />
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
        {(['timeline', 'screenshots', 'logs'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '8px 20px',
              background: tab === t ? '#1e293b' : 'transparent',
              color: tab === t ? '#f1f5f9' : '#64748b',
              border: 'none',
              borderBottom: tab === t ? '2px solid #3b82f6' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: 500,
              textTransform: 'capitalize',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'timeline' && <StepTimeline steps={exec.steps ?? []} />}
      {tab === 'screenshots' && <ScreenshotGallery steps={exec.steps ?? []} />}
      {tab === 'logs' && (
        <div style={{
          background: '#0f172a', borderRadius: 8, padding: 16,
          fontFamily: 'monospace', fontSize: 13, color: '#94a3b8',
          maxHeight: 500, overflowY: 'auto', whiteSpace: 'pre-wrap',
          border: '1px solid #1e293b',
        }}>
          {exec.steps?.map((s) => (
            <div key={`${s.execution_id}-${s.step_order}`} style={{ marginBottom: 12 }}>
              <div style={{ color: s.status === 'PASSED' ? '#22c55e' : s.status === 'FAILED' ? '#ef4444' : '#64748b' }}>
                [{s.step_order}] {s.step_name} - {s.status} ({s.duration_sec.toFixed(2)}s)
              </div>
              {s.log && <div style={{ color: '#64748b', marginLeft: 16 }}>{s.log}</div>}
              {s.error_type && <div style={{ color: '#ef4444', marginLeft: 16 }}>Error: {s.error_type}</div>}
            </div>
          )) ?? <div>No logs available.</div>}
          {exec.crash_logs && exec.crash_logs.length > 0 && (
            <div style={{ marginTop: 20, borderTop: '1px solid #334155', paddingTop: 12 }}>
              <div style={{ color: '#ef4444', fontWeight: 600, marginBottom: 8 }}>Crash Logs:</div>
              {exec.crash_logs.map((log, i) => (
                <div key={i} style={{ color: '#fca5a5', marginBottom: 8 }}>{log}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ color: '#64748b', fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ color: '#e2e8f0', fontSize: 14, marginTop: 2 }}>{value}</div>
    </div>
  );
}
