import { useEffect, useState, useCallback } from 'react';
import type { DeviceQueue } from '../../types';
import { getQueues } from '../../services/api';

const STATUS_COLORS: Record<string, string> = {
  RUNNING: '#3b82f6',
  QUEUED: '#f59e0b',
  COMPLETED: '#22c55e',
  FAILED: '#ef4444',
};

export default function QueueStatusPage() {
  const [queues, setQueues] = useState<DeviceQueue[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchQueues = useCallback(async () => {
    try {
      const data = await getQueues();
      setQueues(data);
    } catch {
      // retry on next poll
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueues();
    const interval = setInterval(fetchQueues, 3000);
    return () => clearInterval(interval);
  }, [fetchQueues]);

  if (loading) {
    return <div style={{ color: '#94a3b8', textAlign: 'center', padding: 40 }}>Loading queues...</div>;
  }

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#f1f5f9', marginBottom: 20 }}>
        Queue Status
      </h1>

      {queues.length === 0 ? (
        <div style={{ color: '#64748b', textAlign: 'center', padding: 40 }}>No active queues.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {queues.map((q) => (
            <div key={q.device_id} style={{
              background: '#1e293b',
              borderRadius: 12,
              padding: 20,
              border: '1px solid #334155',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <h3 style={{ margin: 0, color: '#f1f5f9', fontSize: 16 }}>{q.device_name}</h3>
                <span style={{ color: '#94a3b8', fontSize: 13 }}>
                  {q.queue.length} item(s) in queue
                </span>
              </div>

              {/* Currently running */}
              {q.current_execution && (
                <div style={{
                  background: '#172554',
                  borderRadius: 8,
                  padding: 14,
                  marginBottom: 12,
                  border: '1px solid #1e40af',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <span style={{ color: '#93c5fd', fontWeight: 600, fontSize: 14 }}>
                        Running
                      </span>
                      <span style={{ color: '#94a3b8', fontSize: 13, marginLeft: 12 }}>
                        {q.current_execution.current_step ?? ''}
                      </span>
                    </div>
                    {q.current_execution.progress && (
                      <span style={{
                        background: '#1e3a5f',
                        color: '#93c5fd',
                        padding: '2px 10px',
                        borderRadius: 12,
                        fontSize: 12,
                      }}>
                        Step {q.current_execution.progress}
                      </span>
                    )}
                  </div>
                  <div style={{ color: '#64748b', fontSize: 12, marginTop: 6 }}>
                    Requested by {q.current_execution.requested_by}
                  </div>
                </div>
              )}

              {/* Queue items */}
              {q.queue.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {q.queue.map((item, i) => (
                    <div key={item.execution_id} style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      background: '#0f172a',
                      borderRadius: 6,
                      padding: '10px 14px',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{
                          background: '#334155',
                          color: '#94a3b8',
                          width: 28,
                          height: 28,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          borderRadius: '50%',
                          fontSize: 12,
                          fontWeight: 600,
                        }}>
                          {i + 1}
                        </span>
                        <div>
                          <div style={{ color: '#e2e8f0', fontSize: 13 }}>
                            TC: {item.test_case_id.slice(0, 8)}...
                          </div>
                          <div style={{ color: '#64748b', fontSize: 11 }}>
                            by {item.requested_by}
                          </div>
                        </div>
                      </div>
                      <span style={{
                        color: STATUS_COLORS.QUEUED,
                        fontSize: 12,
                        fontWeight: 500,
                      }}>
                        Waiting
                      </span>
                    </div>
                  ))}
                </div>
              ) : !q.current_execution ? (
                <div style={{ color: '#475569', fontSize: 13, textAlign: 'center', padding: 12 }}>
                  Idle - no pending tests
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
