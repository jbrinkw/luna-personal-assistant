import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { SystemProvider } from './context/SystemContext';
import { ConfigProvider } from './context/ConfigContext';
import { ServicesProvider } from './context/ServicesContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/layout/Layout';
import { ToastContainer } from './components/common/Toast';
import ErrorBoundary from './components/common/ErrorBoundary';
import Dashboard from './pages/Dashboard';
import ExtensionManager from './pages/ExtensionManager';
import ExtensionDetail from './pages/ExtensionDetail';
import UpdateManager from './pages/QueueManager';
import ExtensionStore from './pages/ExtensionStore';
import KeyManager from './pages/KeyManager';
import ExtensionFrame from './pages/ExtensionFrame';
import Infrastructure from './pages/Infrastructure';

function AuthGate({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: 'var(--bg-primary)'
      }}>
        <div>
          <h2>🌙 Luna Hub</h2>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Auto-redirect to GitHub OAuth
    window.location.href = '/auth/login';
    return null;
  }

  return children;
}

export default function App() {
  const [toasts, setToasts] = useState([]);

  const showToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id));
    }, 5000);
  };

  const closeToast = (id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <AuthGate>
            <SystemProvider>
              <ConfigProvider>
                <ServicesProvider>
                  <Routes>
                    <Route path="/ext/:name" element={<ExtensionFrame />} />
                    <Route path="/*" element={
                      <Layout>
                        <Routes>
                          <Route path="/" element={<Dashboard />} />
                          <Route path="/extensions" element={<ExtensionManager />} />
                          <Route path="/extensions/:name" element={<ExtensionDetail />} />
                          <Route path="/queue" element={<UpdateManager />} />
                          <Route path="/store" element={<ExtensionStore />} />
                          <Route path="/secrets" element={<KeyManager />} />
                          <Route path="/infrastructure" element={<Infrastructure />} />
                        </Routes>
                      </Layout>
                    } />
                  </Routes>
                  <ToastContainer toasts={toasts} onClose={closeToast} />
                </ServicesProvider>
              </ConfigProvider>
            </SystemProvider>
          </AuthGate>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
