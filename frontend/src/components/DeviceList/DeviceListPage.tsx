import { useEffect, useState, useCallback } from 'react';
import { Smartphone, Wifi, Loader2, WifiOff, AlertCircle, RefreshCw } from 'lucide-react';
import type { Device } from '../../types';
import { getDevices } from '../../services/api';
import DeviceCard from './DeviceCard';
import { useNavigate } from 'react-router-dom';

const FILTER_KEYS = ['ALL', 'CONNECTED', 'TESTING', 'OFFLINE', 'ERROR'] as const;

export default function DeviceListPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<string>('ALL');
  const navigate = useNavigate();

  const fetchDevices = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    try {
      const data = await getDevices();
      setDevices(data);
    } catch {
      // silently retry on next poll
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(() => fetchDevices(), 5000);
    return () => clearInterval(interval);
  }, [fetchDevices]);

  const counts = {
    ALL:       devices.length,
    CONNECTED: devices.filter((d) => d.status === 'CONNECTED').length,
    TESTING:   devices.filter((d) => d.status === 'TESTING').length,
    OFFLINE:   devices.filter((d) => d.status === 'OFFLINE').length,
    ERROR:     devices.filter((d) => d.status === 'ERROR').length,
  };

  const filtered = filter === 'ALL' ? devices : devices.filter((d) => d.status === filter);

  const statItems = [
    { key: 'ALL',       label: '전체',  color: 'var(--accent)',   icon: <Smartphone size={14} /> },
    { key: 'CONNECTED', label: '연결됨', color: 'var(--success)',  icon: <Wifi size={14} /> },
    { key: 'TESTING',   label: '테스트 중', color: 'var(--blue)',  icon: <Loader2 size={14} /> },
    { key: 'OFFLINE',   label: '오프라인', color: 'var(--text)',   icon: <WifiOff size={14} /> },
    { key: 'ERROR',     label: '오류',  color: 'var(--error)',    icon: <AlertCircle size={14} /> },
  ];

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div className="page-title-group">
          <div className="page-title">단말 관리</div>
          <div className="page-sub">연결된 Android 단말을 확인하고 관리합니다</div>
        </div>
        <button
          className="btn btn-ghost"
          onClick={() => fetchDevices(true)}
          disabled={refreshing}
          style={{ gap: 6 }}
        >
          <RefreshCw size={13} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
          새로고침
        </button>
      </div>

      {/* Stats row */}
      <div className="stats-row">
        {statItems.map(({ key, label, color, icon }) => (
          <div
            key={key}
            className="stat-card"
            onClick={() => setFilter(key)}
            style={{
              cursor: 'pointer',
              borderColor: filter === key ? color : undefined,
              background: filter === key ? `${color}0a` : undefined,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6, color }}>
              {icon}
              <span className="stat-label" style={{ opacity: 1, color }}>{label}</span>
            </div>
            <div className="stat-value" style={{ color: filter === key ? color : undefined }}>
              {counts[key as keyof typeof counts]}
            </div>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="filter-tabs">
        {FILTER_KEYS.map((key) => (
          <button
            key={key}
            className={`filter-tab${filter === key ? ' active' : ''}`}
            onClick={() => setFilter(key)}
          >
            {key === 'ALL' ? '전체' : key} ({counts[key]})
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="loading-state">단말 목록을 불러오는 중...</div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><Smartphone size={40} /></div>
          <div className="empty-state-title">단말 없음</div>
          <div className="empty-state-sub">
            {filter === 'ALL' ? 'ADB로 연결된 단말이 없습니다.' : `${filter} 상태의 단말이 없습니다.`}
          </div>
        </div>
      ) : (
        <div className="device-grid">
          {filtered.map((device) => (
            <DeviceCard
              key={device.id}
              device={device}
              onUpdate={() => fetchDevices()}
              onStreamClick={(id) => navigate(`/stream/${id}`)}
              onExecuted={() => navigate('/history')}
            />
          ))}
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
