import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import type { Device } from '../../types';
import { getDevices } from '../../services/api';
import StreamView from './StreamView';

export default function StreamPage() {
  const { deviceId } = useParams<{ deviceId?: string }>();
  const navigate = useNavigate();
  const [devices, setDevices] = useState<Device[]>([]);
  const [fullscreenDevice, setFullscreenDevice] = useState<string | null>(deviceId ?? null);

  useEffect(() => {
    getDevices().then(setDevices).catch(() => {});
    const interval = setInterval(() => {
      getDevices().then(setDevices).catch(() => {});
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const onlineDevices = devices.filter((d) => d.status !== 'OFFLINE');

  // Fullscreen single device view
  if (fullscreenDevice) {
    const device = devices.find((d) => d.id === fullscreenDevice);
    return (
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <button
            onClick={() => {
              setFullscreenDevice(null);
              if (deviceId) navigate('/stream');
            }}
            style={{
              background: '#334155',
              border: 'none',
              color: '#f1f5f9',
              padding: '8px 16px',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            Back to Grid
          </button>
          <h2 style={{ margin: 0, color: '#f1f5f9', fontSize: 20 }}>
            {device?.name ?? fullscreenDevice}
          </h2>
        </div>
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <StreamView
            deviceId={fullscreenDevice}
            deviceName={device?.name}
          />
        </div>
      </div>
    );
  }

  // Thumbnail grid
  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#f1f5f9', marginBottom: 20 }}>
        Live Streams
      </h1>

      {onlineDevices.length === 0 ? (
        <div style={{ color: '#64748b', textAlign: 'center', padding: 40 }}>
          No online devices available for streaming.
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
          gap: 16,
        }}>
          {onlineDevices.map((device) => (
            <StreamView
              key={device.id}
              deviceId={device.id}
              deviceName={device.name}
              thumbnail
              onClick={() => setFullscreenDevice(device.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
