import React, { useState, useEffect, useCallback, useRef } from 'react';
import './App.css';
import { healthCheck } from './api';
import SubmitPage from './SubmitPage';
import ResultPage from './ResultPage';
import DashboardPage from './DashboardPage';

function App() {
  const [page, setPage] = useState('submit');       // 'submit' | 'result' | 'dashboard'
  const [activeJobId, setActiveJobId] = useState(null);
  const [health, setHealth] = useState(null);        // null | 'ok' | 'err'
  const [toasts, setToasts] = useState([]);
  const toastIdRef = useRef(0);

  // ─── Health check on mount & every 15s ───
  const checkHealth = useCallback(async () => {
    try {
      await healthCheck();
      setHealth('ok');
    } catch {
      setHealth('err');
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const iv = setInterval(checkHealth, 15000);
    return () => clearInterval(iv);
  }, [checkHealth]);

  // ─── Navigation ───
  function navigate(pageName, jobId) {
    setPage(pageName);
    if (jobId) setActiveJobId(jobId);
  }

  // ─── Toast system ───
  function addToast(message, type = 'info') {
    const id = ++toastIdRef.current;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }

  // ─── Render page ───
  function renderPage() {
    switch (page) {
      case 'submit':
        return <SubmitPage onNavigate={navigate} addToast={addToast} />;
      case 'result':
        return <ResultPage jobId={activeJobId} onNavigate={navigate} addToast={addToast} />;
      case 'dashboard':
        return <DashboardPage onNavigate={navigate} addToast={addToast} />;
      default:
        return <SubmitPage onNavigate={navigate} addToast={addToast} />;
    }
  }

  return (
    <div className="app-container">
      {/* Nav Bar */}
      <nav className="nav-bar" id="main-nav">
        <div className="nav-logo" onClick={() => navigate('submit')}>
          <span className="nav-logo-text">
            FEM<span className="accent">SCALE</span>
          </span>
        </div>

        <div className="nav-links">
          <span className="nav-divider"></span>
          <button
            id="nav-submit"
            className={`nav-link ${page === 'submit' ? 'active' : ''}`}
            onClick={() => navigate('submit')}
          >
            Submit
          </button>
          <button
            id="nav-dashboard"
            className={`nav-link ${page === 'dashboard' ? 'active' : ''}`}
            onClick={() => navigate('dashboard')}
          >
            Dashboard
          </button>
        </div>

        <div className="nav-health">
          <span className={`health-dot ${health === 'ok' ? 'ok' : health === 'err' ? 'err' : ''}`}></span>
          <span>{health === 'ok' ? 'ONLINE' : health === 'err' ? 'OFFLINE' : 'CHECKING'}</span>
        </div>
      </nav>

      {/* Page Content */}
      <main className="page-content" id="page-content">
        {renderPage()}
      </main>

      {/* Footer */}
      <footer className="site-footer">
        <div className="footer-left">
          <span className="footer-brand">FEMSCALE</span>
          <span className="footer-copy">2024 FemScale. Encrypted Terminal Access.</span>
        </div>
        <div className="footer-links">
          <button className="footer-link" onClick={() => navigate('dashboard')}>Documentation</button>
          <button className="footer-link">Privacy</button>
          <button className="footer-link">System Status</button>
        </div>
      </footer>

      {/* Toast Container */}
      {toasts.length > 0 && (
        <div className="toast-container">
          {toasts.map((t) => (
            <div key={t.id} className={`toast toast-${t.type}`}>
              {t.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;