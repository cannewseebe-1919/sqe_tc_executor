import { useEffect, useState, useCallback } from 'react';
import { Play, Clock, ListOrdered } from 'lucide-react';
import type { DeviceQueue } from '../../types';
import { getQueues } from '../../services/api';

export default function QueueStatusPage() {
  const [queues, setQueues] = useState<DeviceQueue[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchQueues = useCallback(async () => {
    try {
      const data = await getQueues();
      setQueues(data);
    } catch {
      // retry
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueues();
    const interval = setInterval(fetchQueues, 3000);
    return () => clearInterval(interval);
  }, [fetchQueues]);

  const totalQueued = queues.reduce((sum, q) => sum + q.queue.length, 0);
  const running = queues.filter((q) => q.current_execution).length;

  if (loading) {
    return <div className="loading-state">대기열 정보를 불러오는 중...</div>;
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-title-group">
          <div className="page-title">대기열</div>
          <div className="page-sub">단말별 테스트 실행 대기열 현황</div>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <div style={{
            background: 'var(--blue-dim)',
            border: '1px solid rgba(56,189,248,0.2)',
            borderRadius: 8,
            padding: '8px 14px',
            fontSize: 12,
            color: 'var(--blue)',
            fontWeight: 500,
          }}>
            실행 중 {running}
          </div>
          <div style={{
            background: 'var(--warning-dim)',
            border: '1px solid rgba(245,158,11,0.2)',
            borderRadius: 8,
            padding: '8px 14px',
            fontSize: 12,
            color: 'var(--warning)',
            fontWeight: 500,
          }}>
            대기 중 {totalQueued}
          </div>
        </div>
      </div>

      {queues.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><ListOrdered size={40} /></div>
          <div className="empty-state-title">대기열 없음</div>
          <div className="empty-state-sub">현재 실행 중이거나 대기 중인 테스트가 없습니다</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {queues.map((q) => (
            <div key={q.device_id} className="queue-card">
              <div className="queue-card-header">
                <div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--heading)' }}>
                    {q.device_name}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text)', opacity: 0.5, marginTop: 2, fontFamily: 'monospace' }}>
                    {q.device_id}
                  </div>
                </div>
                <span style={{
                  fontSize: 12,
                  color: 'var(--text)',
                  opacity: 0.6,
                  background: 'var(--elevated)',
                  padding: '4px 12px',
                  borderRadius: 20,
                }}>
                  대기 {q.queue.length}개
                </span>
              </div>

              {/* Currently running */}
              {q.current_execution && (
                <div className="queue-running">
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Play size={13} style={{ color: 'var(--blue)', flexShrink: 0 }} />
                      <span style={{ color: 'var(--blue)', fontWeight: 600, fontSize: 13 }}>실행 중</span>
                      {q.current_execution.current_step && (
                        <span style={{ color: 'var(--text)', fontSize: 12 }}>
                          {q.current_execution.current_step}
                        </span>
                      )}
                    </div>
                    {q.current_execution.progress && (
                      <span style={{
                        fontSize: 11,
                        color: 'var(--blue)',
                        background: 'rgba(56,189,248,0.15)',
                        padding: '2px 10px',
                        borderRadius: 12,
                      }}>
                        Step {q.current_execution.progress}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text)', opacity: 0.5, marginTop: 6 }}>
                    요청: {q.current_execution.requested_by}
                  </div>
                </div>
              )}

              {/* Queue items */}
              {q.queue.length > 0 ? (
                <div>
                  {q.queue.map((item, i) => (
                    <div key={item.execution_id} className="queue-item" style={{ marginTop: i === 0 ? 0 : 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <div className="queue-index">{i + 1}</div>
                        <div>
                          <div style={{ fontSize: 12, color: 'var(--text-bright)', fontFamily: 'monospace' }}>
                            {item.test_case_id.slice(0, 12)}...
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--text)', opacity: 0.5 }}>
                            {item.requested_by}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--warning)' }}>
                        <Clock size={12} />
                        <span style={{ fontSize: 11, fontWeight: 500 }}>대기 중</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : !q.current_execution ? (
                <div style={{
                  textAlign: 'center',
                  padding: '20px',
                  color: 'var(--text)',
                  opacity: 0.3,
                  fontSize: 13,
                }}>
                  대기 중인 테스트 없음
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
