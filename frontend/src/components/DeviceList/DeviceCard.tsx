import { useState } from 'react';
import type { Device } from '../../types';
import { updateDeviceName } from '../../services/api';

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  CONNECTED: { label: 'Connected', color: '#22c55e', bg: '#052e16' },
  TESTING: { label: 'Testing', color: '#3b82f6', bg: '#172554' },
  QUEUED: { label: 'Queued', color: '#f59e0b', bg: '#451a03' },
  OFFLINE: { label: 'Offline', color: '#6b7280', bg: '#1f2937' },
  ERROR: { label: 'Error', color: '#ef4444', bg: '#450a0a' },
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

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: 12,
      padding: 20,
      border: `1px solid ${status.color}33`,
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
    }}>
      {/* Header: name + status badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        {editing ? (
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={handleSave}
            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            disabled={saving}
            autoFocus
            style={{
              background: '#0f172a',
              border: '1px solid #475569',
              borderRadius: 6,
              color: '#f1f5f9',
              padding: '4px 8px',
              fontSize: 16,
              fontWeight: 600,
              width: '60%',
            }}
          />
        ) : (
          <span
            onClick={() => setEditing(true)}
            style={{ fontWeight: 600, fontSize: 16, color: '#f1f5f9', cursor: 'pointer' }}
            title="Click to edit name"
          >
            {device.name}
          </span>
        )}
        <span style={{
          background: status.bg,
          color: status.color,
          padding: '3px 10px',
          borderRadius: 20,
          fontSize: 12,
          fontWeight: 600,
          border: `1px solid ${status.color}55`,
        }}>
          {status.label}
        </span>
      </div>

      {/* Device info */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 13, color: '#94a3b8' }}>
        <span>Model: {device.model}</span>
        <span>Android {device.android_version}</span>
        <span>Resolution: {device.resolution}</span>
        <span>Queue: {device.queue_length}</span>
      </div>

      <div style={{ fontSize: 12, color: '#64748b' }}>
        Serial: {device.id}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
        <button
          onClick={() => onStreamClick(device.id)}
          disabled={device.status === 'OFFLINE'}
          style={{
            flex: 1,
            padding: '8px 0',
            background: device.status === 'OFFLINE' ? '#334155' : '#2563eb',
            color: device.status === 'OFFLINE' ? '#64748b' : '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: device.status === 'OFFLINE' ? 'not-allowed' : 'pointer',
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          View Stream
        </button>
      </div>
    </div>
  );
}
