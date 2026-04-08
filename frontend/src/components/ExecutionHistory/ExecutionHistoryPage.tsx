import { useEffect, useState, useCallback } from 'react';
import type { Execution } from '../../types';
import { getExecutions } from '../../services/api';
import ExecutionDetail from './ExecutionDetail';

const STATUS_STYLE: Record<string, { color: string; bg: string }> = {
  COMPLETED: { color: '#22c55e', bg: '#052e16' },
  FAILED: { color: '#ef4444', bg: '#450a0a' },
  RUNNING: { color: '#3b82f6', bg: '#172554' },
  QUEUED: { color: '#f59e0b', bg: '#451a03' },
  ABORTED: { color: '#a855f7', bg: '#3b0764' },
};

export default function ExecutionHistoryPage() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(0);
  const limit = 20;

  const fetchExecutions = useCallback(async () => {
    try {
      const params: Record<string, unknown> = { limit, offset: page * limit };
      if (statusFilter) params.status = statusFilter;
      const data = await getExecutions(params as Parameters<typeof getExecutions>[0]);
      setExecutions(data.executions);
      setTotal(data.total);
    } catch {
      // retry
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    fetchExecutions();
  }, [fetchExecutions]);

  if (selected) {
    return <ExecutionDetail executionId={selected} onBack={() => setSelected(null)} />;
  }

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#f1f5f9', marginBottom: 20 }}>
        Execution History
      </h1>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {['', 'COMPLETED', 'FAILED', 'RUNNING', 'QUEUED', 'ABORTED'].map((s) => (
          <button
            key={s}
            onClick={() => { setStatusFilter(s); setPage(0); }}
            style={{
              padding: '5px 14px',
              borderRadius: 20,
              border: statusFilter === s ? '1px solid #3b82f6' : '1px solid #334155',
              background: statusFilter === s ? '#1e3a5f' : 'transparent',
              color: statusFilter === s ? '#93c5fd' : '#94a3b8',
              cursor: 'pointer',
              fontSize: 12,
            }}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ color: '#94a3b8', textAlign: 'center', padding: 40 }}>Loading...</div>
      ) : executions.length === 0 ? (
        <div style={{ color: '#64748b', textAlign: 'center', padding: 40 }}>No executions found.</div>
      ) : (
        <>
          <div style={{
            background: '#1e293b',
            borderRadius: 12,
            overflow: 'hidden',
            border: '1px solid #334155',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  {['Status', 'Execution ID', 'Device', 'Requested By', 'Started', 'Duration'].map((h) => (
                    <th key={h} style={{
                      textAlign: 'left',
                      padding: '12px 16px',
                      color: '#94a3b8',
                      fontSize: 12,
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      letterSpacing: 0.5,
                    }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {executions.map((exec) => {
                  const st = STATUS_STYLE[exec.status] ?? STATUS_STYLE.QUEUED;
                  return (
                    <tr
                      key={exec.id}
                      onClick={() => setSelected(exec.id)}
                      style={{
                        borderBottom: '1px solid #1e293b',
                        cursor: 'pointer',
                        background: '#0f172a',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = '#1e293b')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = '#0f172a')}
                    >
                      <td style={{ padding: '10px 16px' }}>
                        <span style={{
                          background: st.bg,
                          color: st.color,
                          padding: '2px 10px',
                          borderRadius: 12,
                          fontSize: 12,
                          fontWeight: 600,
                        }}>
                          {exec.status}
                        </span>
                      </td>
                      <td style={{ padding: '10px 16px', color: '#e2e8f0', fontSize: 13, fontFamily: 'monospace' }}>
                        {exec.id.slice(0, 12)}...
                      </td>
                      <td style={{ padding: '10px 16px', color: '#94a3b8', fontSize: 13 }}>
                        {exec.device_name ?? exec.device_id.slice(0, 10)}
                      </td>
                      <td style={{ padding: '10px 16px', color: '#94a3b8', fontSize: 13 }}>
                        {exec.requested_by}
                      </td>
                      <td style={{ padding: '10px 16px', color: '#94a3b8', fontSize: 13 }}>
                        {exec.started_at ? new Date(exec.started_at).toLocaleString() : '-'}
                      </td>
                      <td style={{ padding: '10px 16px', color: '#94a3b8', fontSize: 13 }}>
                        {exec.total_duration_sec != null ? `${exec.total_duration_sec.toFixed(1)}s` : '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16 }}>
            <span style={{ color: '#64748b', fontSize: 13 }}>
              Showing {page * limit + 1}-{Math.min((page + 1) * limit, total)} of {total}
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                style={{
                  padding: '6px 14px',
                  background: page === 0 ? '#334155' : '#475569',
                  color: page === 0 ? '#64748b' : '#f1f5f9',
                  border: 'none',
                  borderRadius: 6,
                  cursor: page === 0 ? 'not-allowed' : 'pointer',
                  fontSize: 13,
                }}
              >
                Prev
              </button>
              <button
                disabled={(page + 1) * limit >= total}
                onClick={() => setPage((p) => p + 1)}
                style={{
                  padding: '6px 14px',
                  background: (page + 1) * limit >= total ? '#334155' : '#475569',
                  color: (page + 1) * limit >= total ? '#64748b' : '#f1f5f9',
                  border: 'none',
                  borderRadius: 6,
                  cursor: (page + 1) * limit >= total ? 'not-allowed' : 'pointer',
                  fontSize: 13,
                }}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
