import { BrowserRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import SamlCallbackPage from './pages/SamlCallbackPage';
import { DeviceListPage } from './components/DeviceList/DeviceListPage';
import { StreamPage } from './components/DeviceStream/StreamPage';
import { QueueStatusPage } from './components/QueueStatus/QueueStatusPage';
import { ExecutionHistoryPage } from './components/ExecutionHistory/ExecutionHistoryPage';
import { ExecutionDetail } from './components/ExecutionHistory/ExecutionDetail';
import './App.css';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token');
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function Layout({ children }: { children: React.ReactNode }) {
  const handleLogout = () => {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
  };

  return (
    <div className="app-layout">
      <nav className="app-nav">
        <div className="nav-brand">Test Executor</div>
        <div className="nav-links">
          <NavLink to="/" end>단말 관리</NavLink>
          <NavLink to="/stream">화면 스트리밍</NavLink>
          <NavLink to="/queue">대기열</NavLink>
          <NavLink to="/history">실행 이력</NavLink>
        </div>
        <button className="nav-logout" onClick={handleLogout}>로그아웃</button>
      </nav>
      <main className="app-main">{children}</main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<SamlCallbackPage />} />
        <Route path="/" element={<ProtectedRoute><Layout><DeviceListPage /></Layout></ProtectedRoute>} />
        <Route path="/stream" element={<ProtectedRoute><Layout><StreamPage /></Layout></ProtectedRoute>} />
        <Route path="/queue" element={<ProtectedRoute><Layout><QueueStatusPage /></Layout></ProtectedRoute>} />
        <Route path="/history" element={<ProtectedRoute><Layout><ExecutionHistoryPage /></Layout></ProtectedRoute>} />
        <Route path="/history/:id" element={<ProtectedRoute><Layout><ExecutionDetail /></Layout></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
