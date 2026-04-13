import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getSamlLoginUrl, devLogin } from '../services/api';

const IS_DEV_MODE = import.meta.env.VITE_DEV_MODE === 'true';

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Dev mode: auto-login on mount
  useEffect(() => {
    if (IS_DEV_MODE) {
      handleDevLogin();
    }
  }, []);

  const handleDevLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await devLogin();
      localStorage.setItem('access_token', token);
      navigate('/');
    } catch {
      setError('Dev login failed. Is DEV_MODE=true set in backend .env?');
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
      setError('Failed to initiate SSO login. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#0f172a',
    }}>
      <div style={{
        background: '#1e293b',
        borderRadius: 16,
        padding: 48,
        width: 400,
        textAlign: 'center',
        border: '1px solid #334155',
      }}>
        <h1 style={{ color: '#f1f5f9', fontSize: 28, fontWeight: 700, margin: '0 0 8px' }}>
          Test Executor
        </h1>
        <p style={{ color: '#64748b', fontSize: 14, margin: '0 0 32px' }}>
          Device Management & Test Execution Platform
        </p>

        {IS_DEV_MODE ? (
          <>
            <div style={{
              background: '#422006', border: '1px solid #92400e',
              borderRadius: 8, padding: '8px 12px', marginBottom: 24,
              color: '#fbbf24', fontSize: 13,
            }}>
              개발자 모드 활성화됨
            </div>
            <button
              onClick={handleDevLogin}
              disabled={loading}
              style={{
                width: '100%', padding: '14px 0',
                background: loading ? '#334155' : '#16a34a',
                color: loading ? '#64748b' : '#ffffff',
                border: 'none', borderRadius: 8,
                fontSize: 16, fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? '로그인 중...' : 'Dev Login (인증 없이 진입)'}
            </button>
          </>
        ) : (
          <button
            onClick={handleSsoLogin}
            disabled={loading}
            style={{
              width: '100%', padding: '14px 0',
              background: loading ? '#334155' : '#2563eb',
              color: loading ? '#64748b' : '#ffffff',
              border: 'none', borderRadius: 8,
              fontSize: 16, fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Redirecting to SSO...' : 'Sign in with SSO'}
          </button>
        )}

        {error && (
          <div style={{ color: '#ef4444', fontSize: 13, marginTop: 16 }}>{error}</div>
        )}

        <p style={{ color: '#475569', fontSize: 12, marginTop: 24 }}>
          {IS_DEV_MODE ? 'VITE_DEV_MODE=true' : 'SAML 2.0 Single Sign-On'}
        </p>
      </div>
    </div>
  );
}
