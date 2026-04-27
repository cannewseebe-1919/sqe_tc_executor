import { useEffect, useState, useCallback } from 'react';
import { ClipboardList, ChevronLeft, ChevronRight } from 'lucide-react';
import type { Execution } from '../../types';
import { getExecutions } from '../../services/api';
import ExecutionDetail from './ExecutionDetail';

const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  COMPLETED: { color: '#22c55e', bg: 'rgba(34,197,94,0.1)',   label: '완료' },
  FAILED:    { color: '#ef4444', bg: 'rgba(239,68,68,0.1)',   label: '실패' },
  RUNNING:   { color: '#38bdf8', bg: 'rgba(56,189,248,0.1)',  label: '실행 중' },
  QUEUED:    { color: '#f59e0b', bg: 'rgba(245,158,11,0.1)',  label: '대기' },
  ABORTED:   { color: '#a855f7', bg: 'rgba(168,85,247,0.1)', label: '중단' },
};

const FILTERS = [
  { key: '',          label: '전체' },
  { key: 'RUNNING',  label: '실행 중' },
  { key: 'COMPLETED',label: '완료' },
  { key: 'FAILED',   label: '실패' },
  { key: 'QUEUED',   label: '대기' },
  { key: 'ABORTED',  label: '중단' },
];

function formatDuration(sec: number | null | undefined) {
  if (sec == null) return '-';
  if (sec < 60) return `${sec.toFixed(1)}s`;
  return `${Math.floor(sec / 60)}m ${(sec % 60).toFixed(0)}s`;
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('ko-KR', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

export default function ExecutionHistoryPage() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
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

  useEffect(() => { fetchExecutions(); }, [fetchExecutions]);

  if (selected) {
    return <ExecutionDetail executionId={selected} onBack={() => setSelected(null)} />;
  }

  const totalPages = Math.ceil(total / limit);

  return (
    <div>
      <div className="page-header">
        <div className="page-title-group">
          <div className="page-title">실행 이력</div>
          <div className="page-sub">테스트 케이스 실행 결과를 확인합니다</div>
        </div>
        <div style={{ fontSize: 13, color: 'var(--text)', opacity: 0.5 }}>
          총 {total.toLocaleString()}건
        </div>
      </div>

      {/* Filter tabs */}
      <div className="filter-tabs">
        {FILTERS.map(({ key, label }) => (
          <button
            key={key}
            className={`filter-tab${statusFilter === key ? ' active' : ''}`}
            onClick={() => { setStatusFilter(key); setPage(0); }}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading-state">실행 이력을 불러오는 중...</div>
      ) : executions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><ClipboardList size={40} /></div>
          <div className="empty-state-title">실행 이력 없음</div>
          <div className="empty-state-sub">
            {statusFilter ? `'${statusFilter}' 상태의 실행 이력이 없습니다` : '아직 실행된 테스트가 없습니다'}
          </div>
        </div>
      ) : (
        <>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  {['상태', '실행 ID', '단말', '요청자', '시작 시각', '소요 시간'].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {executions.map((exec) => {
                  const st = STATUS_CONFIG[exec.status] ?? STATUS_CONFIG.QUEUED;
                  return (
                    <tr key={exec.id} onClick={() => setSelected(exec.id)}>
                      <td>
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 5,
                          background: st.bg,
                          color: st.color,
                          padding: '3px 10px',
                          borderRadius: 20,
                          fontSize: 11,
                          fontWeight: 600,
                          border: `1px solid ${st.color}30`,
                        }}>
                          <span style={{
                            width: 5, height: 5, borderRadius: '50%',
                            background: st.color, flexShrink: 0,
                          }} />
                          {st.label}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'ui-monospace, monospace', fontSize: 12, color: 'var(--text)' }}>
                        {exec.id.slice(0, 13)}…
                      </td>
                      <td>{exec.device_name ?? exec.device_id.slice(0, 12)}</td>
                      <td style={{ color: 'var(--text)' }}>{exec.requested_by}</td>
                      <td style={{ color: 'var(--text)', fontSize: 12 }}>{formatDate(exec.started_at)}</td>
                      <td style={{ color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>
                        {formatDuration(exec.total_duration_sec)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="pagination">
            <span className="pagination-info">
              {page * limit + 1}–{Math.min((page + 1) * limit, total)} / {total.toLocaleString()}건
            </span>
            <div className="pagination-buttons">
              <button
                className="btn btn-ghost"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                style={{ padding: '7px 12px' }}
              >
                <ChevronLeft size={14} />
                이전
              </button>
              <span style={{
                display: 'flex', alignItems: 'center',
                padding: '0 12px', fontSize: 13, color: 'var(--text)',
              }}>
                {page + 1} / {totalPages || 1}
              </span>
              <button
                className="btn btn-ghost"
                disabled={(page + 1) * limit >= total}
                onClick={() => setPage((p) => p + 1)}
                style={{ padding: '7px 12px' }}
              >
                다음
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
