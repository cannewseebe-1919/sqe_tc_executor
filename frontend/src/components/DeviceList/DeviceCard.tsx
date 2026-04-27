import { useState } from 'react';
import { Smartphone, Monitor, Pencil, Check, X } from 'lucide-react';
import type { Device } from '../../types';
import { updateDeviceName } from '../../services/api';

const STATUS_CONFIG: Record<string, {
  label: string; color: string; bg: string; accent: string; pulse?: boolean;
}> = {
  CONNECTED: { label: 'Connected',  color: '#22c55e', bg: 'rgba(34,197,94,0.1)',   accent: '#22c55e' },
  TESTING:   { label: 'Testing',    color: '#38bdf8', bg: 'rgba(56,189,248,0.1)',  accent: '#38bdf8', pulse: true },
  QUEUED:    { label: 'Queued',     color: '#f59e0b', bg: 'rgba(245,158,11,0.1)',  accent: '#f59e0b' },
  OFFLINE:   { label: 'Offline',    color: '#64748b', bg: 'rgba(100,116,139,0.1)', accent: '#334155' },
  ERROR:     { label: 'Error',      color: '#ef4444', bg: 'rgba(239,68,68,0.1)',   accent: '#ef4444' },
};

interface Props {
  device: Device;
  onUpdate: () => void;
  onStreamClick: (deviceId: string) => void;
}

export default function DeviceCard({ device, onUpdate, onStreamClick }: Props) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(device.name);
  const [saving, setSaving] = useState(false);
  const status = STATUS_CONFIG[device.status] ?? STATUS_CONFIG.OFFLINE;

  const handleSave = async () => {
    if (!name.trim() || name === device.name) {
      setName(device.name);
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await updateDeviceName(device.id, name.trim());
      onUpdate();
    } catch {
      setName(device.name);
    } finally {
      setSaving(false);
      setEditing(false);
    }
  };

  const handleCancel = () => {
    setName(device.name);
    setEditing(false);
  };

  const isOffline = device.status === 'OFFLINE';

  return (
    <div
      className="device-card"
      style={{ '--card-accent': status.accent } as React.CSSProperties}
    >
      {/* Header */}
      <div className="device-card-header">
        <div className="device-name-wrap" style={{ flex: 1, minWidth: 0 }}>
          <div className="device-icon" style={{ color: status.color }}>
            <Smartphone size={16} />
          </div>

          {editing ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, minWidth: 0 }}>
              <input
                className="device-name-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSave();
                  if (e.key === 'Escape') handleCancel();
                }}
                disabled={saving}
                autoFocus
                style={{ flex: 1 }}
              />
              <button className="btn btn-ghost" style={{ padding: '4px 8px' }} onClick={handleSave} disabled={saving}>
                <Check size={13} />
              </button>
              <button className="btn btn-ghost" style={{ padding: '4px 8px' }} onClick={handleCancel}>
                <X size={13} />
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
              <span className="device-name" onClick={() => setEditing(true)} title="클릭하여 이름 수정">
                {device.name}
              </span>
              <button
                onClick={() => setEditing(true)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: 'var(--text)', opacity: 0.4 }}
              >
                <Pencil size={11} />
              </button>
            </div>
          )}
        </div>

        {/* Status badge */}
        <span
          className="status-badge"
          style={{ color: status.color, background: status.bg, borderColor: `${status.color}30` }}
        >
          <span className={`status-dot${status.pulse ? ' pulse' : ''}`} style={{ background: status.color }} />
          {status.label}
        </span>
      </div>

      {/* Info */}
      <div className="device-info">
        <div className="device-info-item">
          <span className="device-info-label">모델</span>
          <span style={{ color: 'var(--text-bright)', fontWeight: 500 }}>{device.model}</span>
        </div>
        <div className="device-info-item">
          <span className="device-info-label">Android</span>
          <span style={{ color: 'var(--text-bright)' }}>{device.android_version}</span>
        </div>
        <div className="device-info-item">
          <span className="device-info-label">해상도</span>
          <span>{device.resolution}</span>
        </div>
        <div className="device-info-item">
          <span className="device-info-label">대기열</span>
          <span style={{ color: device.queue_length > 0 ? 'var(--warning)' : 'var(--text)' }}>
            {device.queue_length}개
          </span>
        </div>
      </div>

      <div className="device-serial">{device.id}</div>

      {/* Actions */}
      <div className="device-actions">
        <button
          className="btn btn-primary"
          style={{ flex: 1 }}
          onClick={() => onStreamClick(device.id)}
          disabled={isOffline}
        >
          <Monitor size={13} />
          화면 보기
        </button>
      </div>
    </div>
  );
}
