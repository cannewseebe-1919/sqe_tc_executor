import { useState } from 'react';
import { getSamlLoginUrl } from '../services/api';

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
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

        <button
          onClick={handleLogin}
          disabled={loading}
          style={{
            width: '100%',
            padding: '14px 0',
            background: loading ? '#334155' : '#2563eb',
            color: loading ? '#64748b' : '#ffffff',
            border: 'none',
            borderRadius: 8,
            fontSize: 16,
            fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? 'Redirecting to SSO...' : 'Sign in with SSO'}
        </button>

        {error && (
          <div style={{ color: '#ef4444', fontSize: 13, marginTop: 16 }}>{error}</div>
        )}

        <p style={{ color: '#475569', fontSize: 12, marginTop: 24 }}>
          SAML 2.0 Single Sign-On
        </p>
      </div>
    </div>
  );
}
