import { useEffect, useState, useCallback } from 'react';
import type { Device } from '../../types';
import { getDevices } from '../../services/api';
import DeviceCard from './DeviceCard';
import { useNavigate } from 'react-router-dom';

export default function DeviceListPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('ALL');
  const navigate = useNavigate();

  const fetchDevices = useCallback(async () => {
    try {
      const data = await getDevices();
      setDevices(data);
    } catch {
      // silently retry on next poll
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 5000);
    return () => clearInterval(interval);
  }, [fetchDevices]);

  const filtered = filter === 'ALL' ? devices : devices.filter((d) => d.status === filter);

  const counts = {
    ALL: devices.length,
    CONNECTED: devices.filter((d) => d.status === 'CONNECTED').length,
    TESTING: devices.filter((d) => d.status === 'TESTING').length,
    OFFLINE: devices.filter((d) => d.status === 'OFFLINE').length,
    ERROR: devices.filter((d) => d.status === 'ERROR').length,
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#f1f5f9', margin: 0 }}>Devices</h1>
        <span style={{ color: '#94a3b8', fontSize: 14 }}>{devices.length} device(s) registered</span>
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {Object.entries(counts).map(([key, count]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            style={{
              padding: '6px 16px',
              borderRadius: 20,
              border: filter === key ? '1px solid #3b82f6' : '1px solid #334155',
              background: filter === key ? '#1e3a5f' : 'transparent',
              color: filter === key ? '#93c5fd' : '#94a3b8',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            {key} ({count})
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', color: '#94a3b8', padding: 40 }}>Loading devices...</div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: 'center', color: '#64748b', padding: 40 }}>No devices found.</div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
          gap: 16,
        }}>
          {filtered.map((device) => (
            <DeviceCard
              key={device.id}
              device={device}
              onUpdate={fetchDevices}
              onStreamClick={(id) => navigate(`/stream/${id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
