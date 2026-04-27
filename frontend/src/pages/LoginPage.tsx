import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { getSamlLoginUrl, devLogin } from '../services/api';

const IS_DEV_MODE = import.meta.env.VITE_DEV_MODE === 'true';

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (IS_DEV_MODE) handleDevLogin();
  }, []);

  const handleDevLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await devLogin();
      localStorage.setItem('access_token', token);
      navigate('/');
    } catch {
      setError('Dev login 실패. 백엔드 .env에 DEV_MODE=true 설정 여부를 확인하세요.');
      setLoading(false);
    }
  };

  const handleSsoLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const url = await getSamlLoginUrl();
      window.location.href = url;
    } catch {
      setError('SSO 로그인을 시작할 수 없습니다. 다시 시도해주세요.');
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background glow */}
      <div style={{
        position: 'absolute',
        top: '30%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: 600,
        height: 400,
        background: 'radial-gradient(ellipse, rgba(59,130,246,0.08) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div style={{
        background: 'var(--card)',
        borderRadius: 20,
        padding: '48px 44px',
        width: 420,
        textAlign: 'center',
        border: '1px solid var(--border)',
        position: 'relative',
        boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
      }}>
        {/* Logo */}
        <div style={{
          width: 52,
          height: 52,
          background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
          borderRadius: 14,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 18,
          fontWeight: 800,
          color: 'white',
          margin: '0 auto 20px',
          boxShadow: '0 8px 24px rgba(59,130,246,0.35)',
        }}>
          TE
        </div>

        <h1 style={{ color: 'var(--heading)', fontSize: 22, fontWeight: 700, margin: '0 0 6px', letterSpacing: -0.3 }}>
          Test Executor
        </h1>
        <p style={{ color: 'var(--text)', fontSize: 13, margin: '0 0 32px', opacity: 0.6 }}>
          Device Management &amp; Test Execution Platform
        </p>

        {IS_DEV_MODE && (
          <div style={{
            background: 'rgba(245,158,11,0.08)',
            border: '1px solid rgba(245,158,11,0.25)',
            borderRadius: 8,
            padding: '7px 12px',
            marginBottom: 20,
            color: '#f59e0b',
            fontSize: 12,
            fontWeight: 500,
          }}>
            개발자 모드
          </div>
        )}

        {IS_DEV_MODE ? (
          <button
            onClick={handleDevLogin}
            disabled={loading}
            style={{
              width: '100%',
              padding: '13px 0',
              background: loading ? 'var(--elevated)' : 'var(--accent)',
              color: loading ? 'var(--text)' : 'white',
              border: 'none',
              borderRadius: 10,
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              transition: 'all 0.15s',
            }}
          >
            {loading && <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />}
            {loading ? '로그인 중...' : 'Dev Login으로 시작'}
          </button>
        ) : (
          <button
            onClick={handleSsoLogin}
            disabled={loading}
            style={{
              width: '100%',
              padding: '13px 0',
              background: loading ? 'var(--elevated)' : 'var(--accent)',
              color: loading ? 'var(--text)' : 'white',
              border: 'none',
              borderRadius: 10,
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              transition: 'all 0.15s',
            }}
          >
            {loading && <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />}
            {loading ? 'SSO 연결 중...' : 'SSO로 로그인'}
          </button>
        )}

        {error && (
          <div style={{
            color: 'var(--error)',
            fontSize: 12,
            marginTop: 16,
            padding: '8px 12px',
            background: 'var(--error-dim)',
            borderRadius: 6,
            border: '1px solid rgba(239,68,68,0.2)',
          }}>
            {error}
          </div>
        )}

        <p style={{ color: 'var(--text)', fontSize: 11, marginTop: 28, opacity: 0.35 }}>
          {IS_DEV_MODE ? 'VITE_DEV_MODE=true · 인증 우회 모드' : 'SAML 2.0 Single Sign-On'}
        </p>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
