import { BrowserRouter, Routes, Route, Navigate, NavLink, useParams, useNavigate } from 'react-router-dom';
import { Smartphone, Monitor, ListOrdered, History, LogOut, Activity } from 'lucide-react';
import LoginPage from './pages/LoginPage';
import SamlCallbackPage from './pages/SamlCallbackPage';
import DeviceListPage from './components/DeviceList/DeviceListPage';
import StreamPage from './components/DeviceStream/StreamPage';
import QueueStatusPage from './components/QueueStatus/QueueStatusPage';
import ExecutionHistoryPage from './components/ExecutionHistory/ExecutionHistoryPage';
import ExecutionDetail from './components/ExecutionHistory/ExecutionDetail';
import './App.css';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token');
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

const NAV_ITEMS = [
  { to: '/', end: true, icon: <Smartphone size={16} />, label: '단말 관리' },
  { to: '/stream', icon: <Monitor size={16} />, label: '화면 스트리밍' },
  { to: '/queue', icon: <ListOrdered size={16} />, label: '대기열' },
  { to: '/history', icon: <History size={16} />, label: '실행 이력' },
];

function Sidebar() {
  const handleLogout = () => {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
  };

  return (
    <aside className="app-sidebar">
      {/* Brand */}
      <div className="nav-brand">
        <div className="brand-logo">TE</div>
        <div>
          <div className="brand-name">Test Executor</div>
          <div className="brand-sub">Device Platform</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="nav-links">
        <div className="nav-section">메뉴</div>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Bottom */}
      <div className="nav-bottom">
        <div style={{
          padding: '8px 12px',
          marginBottom: 8,
          borderRadius: 6,
          background: 'rgba(34,197,94,0.08)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <Activity size={13} style={{ color: '#22c55e', flexShrink: 0 }} />
          <span style={{ fontSize: 11, color: '#22c55e', fontWeight: 500 }}>시스템 정상</span>
        </div>
        <button className="nav-logout" onClick={handleLogout}>
          <LogOut size={16} />
          <span>로그아웃</span>
        </button>
      </div>
    </aside>
  );
}

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="app-main">{children}</main>
    </div>
  );
}

function ExecutionDetailRoute() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  if (!id) return null;
  return <ExecutionDetail executionId={id} onBack={() => navigate('/history')} />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<SamlCallbackPage />} />
        <Route path="/" element={<ProtectedRoute><Layout><DeviceListPage /></Layout></ProtectedRoute>} />
        <Route path="/stream" element={<ProtectedRoute><Layout><StreamPage /></Layout></ProtectedRoute>} />
        <Route path="/stream/:deviceId" element={<ProtectedRoute><Layout><StreamPage /></Layout></ProtectedRoute>} />
        <Route path="/queue" element={<ProtectedRoute><Layout><QueueStatusPage /></Layout></ProtectedRoute>} />
        <Route path="/history" element={<ProtectedRoute><Layout><ExecutionHistoryPage /></Layout></ProtectedRoute>} />
        <Route path="/history/:id" element={<ProtectedRoute><Layout><ExecutionDetailRoute /></Layout></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
