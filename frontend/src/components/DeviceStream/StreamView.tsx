import { useState, useRef, useEffect, useCallback } from 'react';
import { Wifi, WifiOff, Loader } from 'lucide-react';
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
  const [lastError, setLastError] = useState<string | null>(null);
  const [frameReceived, setFrameReceived] = useState(false);

  const wsUrl = (() => {
    const base = import.meta.env.VITE_WS_BASE_URL ||
      `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;
    return `${base}/api/devices/${deviceId}/stream`;
  })();

  const handleMessage = useCallback((data: unknown) => {
    if (typeof data === 'object' && data !== null && 'error' in data) {
      setLastError((data as { error: string }).error);
      return;
    }
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (typeof data === 'object' && data !== null && 'frame' in data) {
      const frameData = (data as { frame: string }).frame;
      const mime = frameData.startsWith('iVBOR') ? 'image/png' : 'image/jpeg';
      const img = new Image();
      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        frameCount.current++;
        setFrameReceived(true);
        setLastError(null);
      };
      img.src = `data:${mime};base64,${frameData}`;
    }
  }, []);

  const { connected } = useWebSocket({ url: wsUrl, onMessage: handleMessage });

  useEffect(() => {
    const interval = setInterval(() => {
      setFps(frameCount.current);
      frameCount.current = 0;
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        aspectRatio: thumbnail ? '9/19.5' : undefined,
        cursor: thumbnail ? 'pointer' : undefined,
        borderRadius: 12,
        overflow: 'hidden',
        background: '#04091a',
        maxWidth: thumbnail ? undefined : 460,
      }}
      onClick={onClick}
    >
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          display: 'block',
        }}
      />

      {/* Error overlay */}
      {lastError && (
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(4,9,26,0.85)',
          gap: 10,
          padding: 16,
        }}>
          <WifiOff size={24} style={{ color: '#ef4444', opacity: 0.8 }} />
          <div style={{
            color: '#fca5a5',
            fontSize: 11,
            textAlign: 'center',
            lineHeight: 1.4,
            maxWidth: 200,
          }}>
            {lastError}
          </div>
        </div>
      )}

      {/* Loading overlay */}
      {connected && !frameReceived && !lastError && (
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 10,
          background: 'rgba(4,9,26,0.7)',
        }}>
          <Loader size={22} style={{ color: '#3b82f6', animation: 'spin 1s linear infinite' }} />
          <span style={{ fontSize: 12, color: '#64748b' }}>화면 로딩 중...</span>
        </div>
      )}

      {/* Bottom bar */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        padding: '8px 10px',
        background: 'linear-gradient(to top, rgba(4,9,26,0.9) 0%, transparent 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        {deviceName && (
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            color: '#e2e8f0',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: '65%',
            textShadow: '0 1px 3px rgba(0,0,0,0.8)',
          }}>
            {deviceName}
          </span>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginLeft: 'auto' }}>
          {connected ? (
            <Wifi size={10} style={{ color: '#22c55e' }} />
          ) : (
            <WifiOff size={10} style={{ color: '#ef4444' }} />
          )}
          <span style={{
            fontSize: 10,
            fontWeight: 600,
            color: connected ? '#22c55e' : '#ef4444',
            letterSpacing: 0.3,
          }}>
            {connected ? `${fps} FPS` : 'OFF'}
          </span>
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
