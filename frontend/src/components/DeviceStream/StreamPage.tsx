import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Monitor } from 'lucide-react';
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 24 }}>
          <button
            onClick={() => {
              setFullscreenDevice(null);
              if (deviceId) navigate('/stream');
            }}
            className="btn btn-ghost"
            style={{ gap: 8 }}
          >
            <ArrowLeft size={14} />
            목록으로
          </button>
          <div>
            <div className="page-title" style={{ fontSize: 18 }}>
              {device?.name ?? fullscreenDevice}
            </div>
            {device && (
              <div style={{ fontSize: 12, color: 'var(--text)', opacity: 0.6, marginTop: 2 }}>
                {device.model} · Android {device.android_version}
              </div>
            )}
          </div>
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
      <div className="page-header">
        <div className="page-title-group">
          <div className="page-title">화면 스트리밍</div>
          <div className="page-sub">연결된 단말의 실시간 화면을 확인합니다</div>
        </div>
        <div style={{ fontSize: 13, color: 'var(--text)', opacity: 0.6 }}>
          {onlineDevices.length}개 단말 온라인
        </div>
      </div>

      {onlineDevices.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><Monitor size={40} /></div>
          <div className="empty-state-title">스트리밍 가능한 단말 없음</div>
          <div className="empty-state-sub">온라인 상태의 단말을 ADB로 연결하세요</div>
        </div>
      ) : (
        <div className="stream-grid">
          {onlineDevices.map((device) => (
            <div key={device.id} className="stream-thumbnail" onClick={() => setFullscreenDevice(device.id)}>
              <StreamView
                deviceId={device.id}
                deviceName={device.name}
                thumbnail
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
