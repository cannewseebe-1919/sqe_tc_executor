import { useState, useRef, useEffect, useCallback } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';

interface Props {
  deviceId: string;
  deviceName?: string;
  thumbnail?: boolean;
  onClick?: () => void;
}

export default function StreamView({ deviceId, deviceName, thumbnail = false, onClick }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [fps, setFps] = useState(0);
  const frameCount = useRef(0);

  const wsUrl = (() => {
    const base = import.meta.env.VITE_WS_BASE_URL ||
      `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;
    return `${base}/api/devices/${deviceId}/stream`;
  })();

  const handleMessage = useCallback((data: unknown) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Expect base64-encoded image frame (JPEG or PNG)
    if (typeof data === 'object' && data !== null && 'frame' in data) {
      const frameData = (data as { frame: string }).frame;
      // Auto-detect PNG (base64 of PNG starts with 'iVBOR') or default to JPEG
      const mime = frameData.startsWith('iVBOR') ? 'image/png' : 'image/jpeg';
      const img = new Image();
      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        frameCount.current++;
      };
      img.src = `data:${mime};base64,${frameData}`;
    }
  }, []);

  const { connected } = useWebSocket({
    url: wsUrl,
    onMessage: handleMessage,
  });

  // FPS counter
  useEffect(() => {
    const interval = setInterval(() => {
      setFps(frameCount.current);
      frameCount.current = 0;
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const containerStyle: React.CSSProperties = thumbnail
    ? { width: 240, height: 420, cursor: 'pointer', position: 'relative' }
    : { width: '100%', maxWidth: 480, position: 'relative' };

  return (
    <div style={containerStyle} onClick={onClick}>
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: thumbnail ? '100%' : 'auto',
          objectFit: 'contain',
          background: '#0f172a',
          borderRadius: 8,
          border: connected ? '2px solid #22c55e33' : '2px solid #ef444433',
        }}
      />

      {/* Overlay info */}
      <div style={{
        position: 'absolute',
        bottom: 8,
        left: 8,
        right: 8,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        {deviceName && (
          <span style={{
            background: '#000000aa',
            color: '#f1f5f9',
            padding: '2px 8px',
            borderRadius: 4,
            fontSize: 12,
          }}>
            {deviceName}
          </span>
        )}
        <span style={{
          background: connected ? '#052e16cc' : '#450a0acc',
          color: connected ? '#22c55e' : '#ef4444',
          padding: '2px 8px',
          borderRadius: 4,
          fontSize: 11,
        }}>
          {connected ? `${fps} FPS` : 'Disconnected'}
        </span>
      </div>
    </div>
  );
}
